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
from threading import Thread
from os import listdir
from os.path import isfile, join, getsize
import hashlib
import random
random.seed()

TARGET_IP = '127.0.0.1' # Target IP of the main server
TARGET_PORT = 5005 # Target Port of the main server
ENDPOINT_PORT = random.randint(49152, 65535) #The Internet Assigned Numbers Authority (IANA) suggests the range 49152 to 65535 (215+214 to 216−1) for dynamic or private ports.
ENDPOINT_IP = '127.0.0.1' 
BUFFER_SIZE = 1024 # The receive buffer
MAX_NB_PEERS = 5


class Client:
    def __init__(self, shareFolder, targetIP = TARGET_IP, targetPort = TARGET_PORT, bufferSize = BUFFER_SIZE, endPointIP = ENDPOINT_IP, endPointPort = ENDPOINT_PORT):
        self.filesAvailable = [] #list of files available [('filename1', hash(...), fileSize, nbChunks), ('filename2', hash(...), fileSize, nbChunks)...]
        self.targetIP = TARGET_IP #Main server
        self.targetPort = TARGET_PORT #Main server
        self.endPointIP = endPointIP #End-point IP
        self.endPointPort = endPointPort #End-point port
        
        self.threads = {} #Dict of all server threads running
        
        self.bufferSize = BUFFER_SIZE
        self.shareFolder = shareFolder # The name of the folder the client will share the file from.
        
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
                
                self.fileLocationRequest(self.filesAvailable[choice])
                
        
        
        print("[C2MS] Disconnected from server.")
        self.clientSocket.close()
        
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
        
        # Look for the response
        ack = self.clientSocket.recv(self.bufferSize).decode()
        assert(ack == "ACK")
    
    def fileRegisterRequest(self):
        #Tells the server what files the peer wants to share with the network. 
        #Takes in the IP address (uint32) and port (uint16) for the end- point to accept peer connections for download; 
        #the number of files to register (uint16); 
        #and for every file, a file name (string) and its length (uint32), and a hash of each chunk
        
        sha224 = hashlib.sha224() #My hash function
        
        registrationObject = {} #The object to send to the server
        filenameShared = [f for f in listdir(self.shareFolder) if isfile(join(self.shareFolder, f))]
        registrationObject['nbOfFiles'] = len(filenameShared)
        registrationObject['endPointIP'] = self.endPointIP
        registrationObject['endPointPort'] = self.endPointPort
        registrationObject['filesMetadata'] = [] #[('file1', globalhash of file1, size, chunkNb), ....]
        
        for filename in filenameShared:
            pathToF = self.shareFolder+'/'+filename
            size = getsize(pathToF) #in bytes
            #Compute the hash of the entire file with sha224 (better than MD5 or SHA1)
            #And the hash of each chunk with len self.bufferSize
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
        self.clientSocket.send("END_DATA".encode())
            
        
        # Look for the response
        ack = self.clientSocket.recv(self.bufferSize).decode()
        assert(ack == "ACK")
        
        print("[C2MS] Send register request.")
        
    def fileLocationRequest(self, fileID):
        print(fileID)
        
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
        print("[S2P] Client server side started.")
        
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
            for t in self.threads.values():
                t.join(1) #let the thread 1sec to finish

            self.serverSocket.close()
            print("\n[S2P] Client server stopped on user interrupt.")
    
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
            else:
                print("[S2P] Unknown request, dropping.")
        
        #Close the client handler.
        peerSocket.close()
        del self.threads[addr]
        print("[S2P] Client disconnected %s:%d."%(addr[0], addr[1]))
    
    def handleGetChunk(peerSocket, addr):
        #Ask which chunk the peer wants and send it + the hash
        pass
    
    def handleLeaveRequest(self, clientSocket, addr):# The client wishes to disconnect from the P2P network.
                
        #Signal to the client he can leave now.
        clientSocket.send("ACK".encode())
        print("[S2P] Completed request LEAVE from the client %s:%d."%(addr[0], addr[1]))
    
    #-------------------------- PEER TO SERVER SIDE -----------------------------
    #----------------------------------------------------------------------------
    
        
        
if __name__ == "__main__":
    shareFolder = sys.argv[1]
    
    C = Client(shareFolder)
    C.startServerSide()
    C.startClientSide()