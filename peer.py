#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct  1 18:19:08 2018

@author: vav4
"""

import socket
import time
import sys
import pickle
from threading import Thread, Lock
from os import listdir
from os.path import isfile, join, getsize, exists
from os import mkdir
import shutil
import hashlib
import random
from collections import Counter
random.seed()

TARGET_IP = '127.0.0.1' # Target IP of the main server
TARGET_PORT = 5005 # Target Port of the main server
ENDPOINT_PORT = random.randint(49152, 65535) #The Internet Assigned Numbers Authority (IANA) suggests the range 49152 to 65535 (215+214 to 216−1) for dynamic or private ports.
ENDPOINT_IP = '127.0.0.1' 
BUFFER_SIZE = 1024 # The receive buffer
MAX_NB_PEERS = 5
SEND_DELAY = 0.01
TMP_DIRECTORY = 'tmp' #The name of the temporary directory.
MAX_QUEUED_REQUEST = 50


def progressBar(progress, total):
    #Displays or updates a console progress bar.
    #Source: https://stackoverflow.com/questions/3160699/python-progress-bar
    barLength, status = 20, ""
    progress = float(progress) / float(total)
    if progress >= 1.:
        progress, status = 1, "\r\n"
    block = int(round(barLength * progress))
    text = "\r[{}] {:.0f}% {}".format(
        "#" * block + "-" * (barLength - block), round(progress * 100, 0),
        status)
    sys.stdout.write(text)
    sys.stdout.flush()

class Client:
    def __init__(self, shareFolder, targetIP = TARGET_IP, targetPort = TARGET_PORT, bufferSize = BUFFER_SIZE, endPointIP = ENDPOINT_IP, endPointPort = ENDPOINT_PORT):
        
        #------------------ CLIENT TO MAIN-SERVER SIDE
        self.filesAvailable = [] #list of files available [('filename1', hash(...), fileSize, nbChunks), ('filename2', hash(...), fileSize, nbChunks)...]
        self.targetIP = TARGET_IP #Main server
        self.targetPort = TARGET_PORT #Main server
        self.shareFolder = shareFolder # The name of the folder the client will share the file from.
        
        #------------------------ SERVER TO PEER SIDE
        self.endPointIP = endPointIP #End-point IP
        self.endPointPort = endPointPort #End-point port
        self.threads = {} #Dict of all server threads running
        
        #-------------------------- PEER TO SERVER SIDE
        self.downloadingFileSource = None #Which peer has what ?
        self.downloadingFileID = None #File metadata (filename, hash, size in B, chunkNb)
        self.downloadingFileSourceUpdateTime = None #Timestamp of the last time the FileSources has been updated (ask the Main server)
        self.chunksDownloaded = set([]) #The chunks downloaded so far
        self.chunksDownloading = set([]) #The chunks downloading
        self.chunksDownloaded_ingLock = Lock() #Lock on the last 2 objects
        
        self.chunksSaveLock = Lock()
        
        self.downloadingThreads = {} #The threads for the downloading process
        self.peerConnected = {} #Dict of peers' (IP, Port) where the client is connected to. {(IP, Port): socket, (IP2, Port2): socket2}
        
        #-------------------------- GENERAL
        self.bufferSize = BUFFER_SIZE
        
        self.startServerSideThread = Thread(target=self.startServerSide, args=())
        self.startClientSideThread = Thread(target=self.startClientSide, args=())
        self.startServerSideThread.start()
        self.startClientSideThread.start()
    

    #------------------ CLIENT TO MAIN-SERVER SIDE [C2MS] -----------------------
    #----------------------------------------------------------------------------
    
    def startClientSide(self):
        # Create a TCP/IP socket
        self.clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Connect the socket to the port where the server is listening
        try:
            self.clientSocket.connect((self.targetIP, self.targetPort))
            print("[C2MS] Client connected to the server : %s:%d."% (self.targetIP, self.targetPort))
        except ConnectionRefusedError:
            print("[C2MS] Server refused the connexion.")
            print("[C2MS] Aborting.")
            self.clientSocket.close()
            sys.exit()
        #Socket created and connected.
        
        self.fileRegisterRequest()
        
        print("[C2MS] Welcome, here are the files available.")
        
        while True:
            #Show the files available
            self.fileListRequest()
            self.printFileList()

            # Ask for the user's choice.
            choice = input("[C2MS] Please choose the file number you wish to download [Q] for leaving [R] for reloading: ")
                
            # Respond to the user's choice.
            if choice == 'Q':
                print("[C2MS] Disconnecting from the server and shutting down server side...")
                #shut down server side
                self.leaveRequest()
                break
            if choice == 'R':
                print("[C2MS] Reloading...")
                continue
            else:
                try:
                    choice = int(choice)
                    assert(len(self.filesAvailable) > choice)
                except:
                    print("[C2MS] Invalid input, try again.")
                    continue
                
                returnCode = self.fileLocationRequest(self.filesAvailable[choice])
                if returnCode == 0:
                    self.startDownload()
                
        
        
        print("[C2MS] Disconnected from server.")
        self.clientSocket.close()
        self.stopServerSide() #closing the serverSide too.
        
    def fileListRequest(self):
        # Sends request
        self.clientSocket.send("GET_FILE_LIST".encode())
        
        # Look for the response
        data = []
        while True:
            packet = self.clientSocket.recv(self.bufferSize)
            if packet == "END_DATA".encode():
                break
            data.append(packet)
        self.filesAvailable = pickle.loads(b"".join(data))
        
        # Sends the ACK
        time.sleep(SEND_DELAY)
        self.clientSocket.send("ACK".encode())
    
    def printFileList(self):
        count = 0
        print('\n{0:5} | {1:20} | {2:10}'.format('[x]', 'Filename', 'File size (B)'))
        for item in self.filesAvailable:
            print('{0:5} | {1:20} | {2:10}'.format('['+str(count)+']' , item[0], item[2]))
            count += 1
    
    def leaveRequest(self):
        # Sends request
        self.clientSocket.send("LEAVE".encode())
        
        #Send the server Side IP and Port, the MS will delete the client from the file system
        time.sleep(SEND_DELAY)
        self.clientSocket.send(pickle.dumps((self.endPointIP, self.endPointPort)))
        
        # Look for the response
        ack = self.clientSocket.recv(self.bufferSize).decode()
        assert(ack == "ACK")
    
    def fileRegisterRequest(self):
        #Tells the server what files the peer wants to share with the network. 
        #Takes in the IP address (uint32) and port (uint16) for the end- point to accept peer connections for download; 
        #the number of files to register (uint16); 
        #and for every file, a file name (string) and its length (uint32), and a hash of each chunk
        
        
        registrationObject = {} #The object to send to the server
        filenameShared = [f for f in listdir(self.shareFolder) if isfile(join(self.shareFolder, f))]
        registrationObject['nbOfFiles'] = len(filenameShared)
        registrationObject['endPointIP'] = self.endPointIP
        registrationObject['endPointPort'] = self.endPointPort
        registrationObject['filesMetadata'] = [] #[('file1', globalhash of file1, size, chunkNb), ....]
        
        for filename in filenameShared:
            sha224 = hashlib.sha224() #My hash function
            pathToF = self.shareFolder+'/'+filename
            size = getsize(pathToF) #in bytes
            #Compute the hash of the entire file with sha224 (better than MD5 or SHA1)
            chunkNb = 0
            with open(pathToF, 'rb') as f:
                while True:
                    data = f.read(self.bufferSize) #Read self.bufferSize bytes by self.bufferSize bytes
                    if not data:
                        break
                    chunkNb += 1
                    sha224.update(data)
            registrationObject['filesMetadata'].append((filename, sha224.hexdigest(), size, chunkNb))
                        
        
        # Sends request
        self.clientSocket.send("FILE_REGISTER".encode())
        
        # Look for the response
        reply = self.clientSocket.recv(self.bufferSize).decode()
        assert(reply == "SEND")
        
        #Send the data for the registration
        data = pickle.dumps(registrationObject)
        for n in range(len(data) // self.bufferSize + 1):
            self.clientSocket.send(data[n * self.bufferSize: (n + 1) * self.bufferSize])
            time.sleep(SEND_DELAY)
        self.clientSocket.send("END_DATA".encode())
            
        
        # Look for the response
        ack = self.clientSocket.recv(self.bufferSize).decode()
        assert(ack == "ACK")
        
        print("[C2MS] Sent register request.")
        
    def fileLocationRequest(self, fileID):
        #fileID = ('filename', globalhash of file, size in bytes, chunkNb)
        #Check if the client already have the file:
        fileAlreadyDownloaded = None
        try:
            sha224 = hashlib.sha224() #My hash function
            pathToF = self.shareFolder+'/'+fileID[0]
            size = getsize(pathToF) #in bytes
            #Compute the hash of the entire file with sha224 (better than MD5 or SHA1)
            chunkNb = 0
            with open(pathToF, 'rb') as f:
                while True:
                    data = f.read(self.bufferSize) #Read self.bufferSize bytes by self.bufferSize bytes
                    if not data:
                        break
                    chunkNb += 1
                    sha224.update(data)
            if (fileID[0], sha224.hexdigest(), size, chunkNb) == fileID:
                fileAlreadyDownloaded = True
            else:
                fileAlreadyDownloaded = False
        except:
            fileAlreadyDownloaded = False
                
        if not fileAlreadyDownloaded: #We send the request
            #fileID = ('filename', hash(...), fileSize, nbChunks)
            self.clientSocket.send("FILE_LOCATION".encode())

            #Send fileID
            time.sleep(SEND_DELAY)
            self.clientSocket.send(pickle.dumps(fileID))
            
            #Receive the sources
            data = []
            while True:
                packet = self.clientSocket.recv(self.bufferSize)
                if packet == "END_DATA".encode():
                    break
                data.append(packet)

            #Decode the sources and take a timestamp
            #If the timestamp is too old, we will send the same request again.
            self.downloadingFileSource = pickle.loads(b"".join(data)) #the seeders data {('127.0.0.1', 63248): set([chunkNn]), ('127.0.0.1', 63249):...}
            self.downloadingFileID = fileID
            self.downloadingFileSourceUpdateTime = time.time() #time in sec
            
            #Sends an ACK
            time.sleep(SEND_DELAY)
            self.clientSocket.send("ACK".encode())
            return 0
        
        else:
            print("[C2MS] You already have this file.")
            return -1
                
    #------------------------ SERVER TO PEER SIDE [S2P] -------------------------
    #----------------------------------------------------------------------------
    
    def startServerSide(self):
        # Create a TCP/IP socket
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #re-use the socket if in a TIME_WAIT state.
        #https://stackoverflow.com/questions/27360218/how-to-close-socket-connection-on-ctrl-c-in-a-python-programme
        self.serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Bind the socket to the port
        try:
            self.serverSocket.bind((self.endPointIP, self.endPointPort))
        except:
            print("[S2P] Binding socket failed.")
            print("[S2P] Aborting.")
            sys.exit()
        print("[S2P] Client server side started on %s:%d."%(self.endPointIP, self.endPointPort))
        
        # Listen for incoming connections
        self.serverSocket.listen(MAX_NB_PEERS)# Queue up to MAX_NB_PEERS requests
        
        print("[S2P] Client server socket now listening and seeding in the background.")
        try:
            while True:
                peerSocket, addr = self.serverSocket.accept()
                print("[S2P] Accepted connection from: %s:%d."%(addr[0], addr[1]))

                try:
                    peerSocket = Thread(target=self.handleClient, args=(peerSocket, addr))
                    peerSocket.start()
                    self.threads[addr] = peerSocket
                except:
                    print("[S2P] Thread handleClient() did not start.")

        except KeyboardInterrupt:
            self.stopServerSide()
            print("\n[S2P] Client server stopped on user interrupt.")
        
        except ConnectionAbortedError:
            print("\n[S2P] Client server stopped (brutally).")
    
    def stopServerSide(self):
        for t in self.threads.values():
            t.join(1) #let the thread 1sec to finish

        self.serverSocket.close()

    def handleClient(self, peerSocket, addr):
        request = None
        while request != 'LEAVE':
            #Print out what the client sends
            request = peerSocket.recv(self.bufferSize).decode()
            print("[S2P] Received request from the peer %s:%d : \"%s\"."%(addr[0], addr[1], request))

            #Request handler
            if request == "GET_CHUNK":
                self.handleGetChunk(peerSocket, addr)
            elif request == 'LEAVE':
                self.handleLeaveRequest(clientSocket, addr)
                break
            elif len(request) == 0:
                break
            else:
                print("[S2P] Unknown request, dropping.")
        
        #Close the client handler.
        peerSocket.close()
        del self.threads[addr]
        print("[S2P] Client disconnected %s:%d."%(addr[0], addr[1]))
    
    def handleGetChunk(self, peerSocket, addr):
        #Ask which chunk the peer wants and send it + the hash
        
        #Receive the file ID:
        fileID = pickle.loads(peerSocket.recv(self.bufferSize))
        
        #Receive the chunk ID:
        chunkID = pickle.loads(peerSocket.recv(self.bufferSize))
        
        #Find the chunk of data requested:
        chunkData = ''
        try:
            pathToF = self.shareFolder+'/'+fileID[0]
            chunkNb = 0
            with open(pathToF, 'rb') as f:
                while True:
                    chunkData = f.read(self.bufferSize) #Read self.bufferSize bytes by self.bufferSize bytes
                    if not chunkData or chunkNb == chunkID:
                        break
                    chunkNb += 1
        except:
            print("[S2P] Counldn't find the chunk requested.")
        
        #Send the chunk requested
        time.sleep(SEND_DELAY)
        peerSocket.send(chunkData)
        
        #Send the hash
        time.sleep(SEND_DELAY)
        peerSocket.send(hashlib.sha224(chunkData).hexdigest().encode())
        
        print("[S2P] Completed request GET_CHUNK from the client %s:%d."%(addr[0], addr[1]))
            
    def handleLeaveRequest(self, clientSocket, addr):# The client wishes to disconnect from the P2P network.
                
        #Signal to the client he can leave now.
        time.sleep(SEND_DELAY)
        clientSocket.send("ACK".encode())
        print("[S2P] Completed request LEAVE from the client %s:%d."%(addr[0], addr[1]))
    
    #-------------------------- PEER TO SERVER SIDE -----------------------------
    #----------------------------------------------------------------------------
    
    def startDownload(self):
        
        testWhile = len(self.chunksDownloaded) != self.downloadingFileID[3]
        while testWhile:#downloadingFileID = ('filename', globalhash of file, size in bytes, chunkNb)
            # Uses self.downloadingFileSource to check which chunk is the rarest.
            rarestChunkObject = self.findRarestChunk()
            if rarestChunkObject == -1:
                self.chunksDownloaded_ingLock.acquire()
                testWhile = len(self.chunksDownloaded) != self.downloadingFileID[3]
                self.chunksDownloaded_ingLock.release()
                continue
            chunkID, peerIP, peerPort = rarestChunkObject[0], rarestChunkObject[1], rarestChunkObject[2]
            
            peerSocketLock = self.peerConnected.get((peerIP, peerPort), None)
            peerSocket = None
            peerLock = None
            if peerSocketLock == None: # We create a new socket.
                # Create a TCP/IP socket
                peerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                
                
                # Connect the socket to the port where the server is listening
                try:
                    peerSocket.connect((peerIP, peerPort))
                    #print("[P2S] Client connected to the server : %s:%d."% (self.targetIP, self.targetPort))
                except ConnectionRefusedError:
                    print("[P2S] Server refused the connexion.")
                    print("[P2S] Aborting.")
                    peerSocket.close()
                    del self.peerConnected[(peerIP, peerPort)]
                    sys.exit()
                #Socket created and connected.
                
                #Create a new lock, specific for the socket, this will avoid downloading 
                #2 chunks at the same time from the same peer
                peerLock = Lock()
                
                #Add it for bookkeeping
                self.peerConnected[(peerIP, peerPort)] = (peerSocket, peerLock)
                
            else:
                peerSocket, peerLock = peerSocketLock[0], peerSocketLock[1]
            
            #Block if too many threads are active at the same time...
            self.maxNumberRequestHandler()
            
            #Update fileLocationRequest if it's been too long since last time we asked the server
            #This allow the client to discover new peers
            
            try:
                chunkRequestThread = Thread(target=self.chunkRequest, args=(chunkID, peerSocket, peerLock))
                chunkRequestThread.start()
                self.downloadingThreads[(chunkID, peerIP, peerPort)] = chunkRequestThread
            except:
                print("[P2S] Thread handleClient() did not start.")
                
            self.chunksDownloaded_ingLock.acquire()
            testWhile = len(self.chunksDownloaded) != self.downloadingFileID[3]
            progressBar(len(self.chunksDownloaded), self.downloadingFileID[3])
            self.chunksDownloaded_ingLock.release()
        #End while loop, the file is downloaded
        
        
        #Wait for the threads to finish.
        for chunkRequestThread in self.downloadingThreads.values():
            chunkRequestThread.join()
        
        #Closing all the sockets opened
        for peerSocket, lock in self.peerConnected.values():
            #TODO Send LEAVE REQUEST
            peerSocket.close()
            
        self.saveFile()
        
        self.downloadingFileSource = None # The seeders data {('127.0.0.1', 63248): set([chunkNb]), ('127.0.0.1', 63249):...}
        self.downloadingFileID = None 
        self.downloadingFileSourceUpdateTime = None #TODO
        self.chunksDownloaded = set([])
        self.chunksDownloading = set([])
        self.downloadingThreads = {} #{(chunkID, peerIP, peerPort): Thread }
        self.peerConnected = {} #{(peerIP, peerPort): (socket, lock)...}
        
    def findRarestChunk(self): #Using the Counter package
        pendingChunks = []
        
        self.chunksDownloaded_ingLock.acquire()
        for s in self.downloadingFileSource.values():
            pendingChunks += list(s.difference(self.chunksDownloaded).difference(self.chunksDownloading))
        self.chunksDownloaded_ingLock.release()
        
        try:
            chunkID = Counter(pendingChunks).most_common()[-1][0]

            for peer, s in self.downloadingFileSource.items():
                if chunkID in s:
                    return (chunkID, peer[0], peer[1])
        except:
            return -1
    
    def maxNumberRequestHandler(self):
        #Block if too many threads are active at the same time...
        nbActiveThread = 0
        for threadID, chunkRequestThread in self.downloadingThreads.copy().items():
            if chunkRequestThread.isAlive():
                nbActiveThread += 1
            else:
                del self.downloadingThreads[threadID]

        while nbActiveThread > MAX_QUEUED_REQUEST:
            print("[P2S] Waiting for queued requests to finish...")
            time.sleep(2) #Wait for threads to finish.
            nbActiveThread = 0
            for threadID, chunkRequestThread in self.downloadingThreads.copy().items():
                if chunkRequestThread.isAlive():
                    nbActiveThread += 1
                else:
                    del self.downloadingThreads[threadID]
    
    def chunkRequest(self, chunkID, peerSocket, peerLock):
        self.chunksDownloaded_ingLock.acquire()
        self.chunksDownloading.add(chunkID)
        self.chunksDownloaded_ingLock.release()
        
        #Lock the peerSocket
        peerLock.acquire()
        peerSocket.send("GET_CHUNK".encode())
        
        #Send the file ID
        time.sleep(SEND_DELAY)
        peerSocket.send(pickle.dumps(self.downloadingFileID))
        
        #Send the chunk ID
        time.sleep(SEND_DELAY)
        peerSocket.send(pickle.dumps(chunkID))
        
        #Receive the chunk
        data = peerSocket.recv(self.bufferSize)
        
        #Receive the hash(chunk)
        hashReceived = peerSocket.recv(self.bufferSize).decode()
        
        peerLock.release()
        #Unlock the peerSocket
        
        hashedData = hashlib.sha224(data).hexdigest()
        
        if hashedData == hashReceived:
            #Save it to the temp directory to avoid using too much memory
            self.chunksSaveLock.acquire()
            if not exists(self.shareFolder+'/'+TMP_DIRECTORY):
                mkdir(self.shareFolder+'/'+TMP_DIRECTORY)

            f = open(self.shareFolder+'/'+TMP_DIRECTORY+'/'+str(chunkID)+'.chunk', 'wb')
            f.write(data)
            f.close()
            self.chunksSaveLock.release()

            self.chunksDownloaded_ingLock.acquire()
            self.chunksDownloaded.add(chunkID)
            self.chunksDownloading.remove(chunkID)
            self.chunksDownloaded_ingLock.release()
            #print("[P2S] Chunk request successful.", chunkID)
        else:
            self.chunksDownloaded_ingLock.acquire()
            self.chunksDownloading.remove(chunkID)
            self.chunksDownloaded_ingLock.release()
            print("[P2S] Chunk request failed, invalid hash.", chunkID)
    
    def saveFile(self):
        #Assemble the file
        with open(self.shareFolder+'/'+self.downloadingFileID[0], 'wb') as tempFile:
            for i in range(self.downloadingFileID[3]):
                 with open(self.shareFolder + '/'+TMP_DIRECTORY+'/'+str(i)+'.chunk', 'rb') as chunkFile:
                    shutil.copyfileobj(chunkFile, tempFile)
        
        #Remove the TMP_DIRECTORY directory
        shutil.rmtree(self.shareFolder+'/'+TMP_DIRECTORY)
        print("[P2S] File downloaded.")
        
        
if __name__ == "__main__":
    shareFolder = sys.argv[1]
    
    C = Client(shareFolder)