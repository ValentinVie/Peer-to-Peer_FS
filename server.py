#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct  1 18:16:23 2018

@author: vav4, Valentin VIE
PennState University, CSE 514
"""

import socket
from threading import Thread
import sys
import pickle
import time

#--------------------------- PROTOCOL OPTIONS
TCP_IP = '127.0.0.1' # Listening IP
TCP_PORT = 5005 # Listening Port
BUFFER_SIZE = 1024  # The receive buffer, contains the first message from the client.
MAX_NB_CLIENT = 5




class MainServer:
    def __init__(self, IP = TCP_IP, TCPPort = TCP_PORT, bufferSize = BUFFER_SIZE):
        self.IP = IP
        self.TCPPort = TCPPort
        self.bufferSize = bufferSize #Receive buffer size.
        self.threads = {} #dict of all threads running
        self.filesAvailable = {}
        #self.filesAvailable = { ('filename1', hash(filename1), filesize, chunkNb): {(IP, PORT) : set([1, 2, 3]) chuncks availables, 
        #                                          ('127.0.0.1', 1253): set([3])
        #                                         },
        #                        ('filename2', hash('filename2'), 231, 7):{ ('127.0.0.1', 4353) : set([1, 2, 3, 4, 5, 6, 7])
        #                                      }
        #                      }
        
        # Create a TCP/IP socket
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #re-use the socket if in a TIME_WAIT state.
        #https://stackoverflow.com/questions/27360218/how-to-close-socket-connection-on-ctrl-c-in-a-python-programme
        self.serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Bind the socket to the port
        try:
            self.serverSocket.bind((TCP_IP, TCP_PORT))
        except:
            print("[S] Binding socket failed.")
            print("[S] Aborting.")
            sys.exit()
        
        # Listen for incoming connections
        self.serverSocket.listen(MAX_NB_CLIENT)# Queue up to MAX_NB_CLIENT requests
        print("[S] Server created, not listening yet.")
        
    def startServer(self):
        print("[S] Server socket now listening.")
        try:
            while True:
                clientSocket, addr = self.serverSocket.accept()
                print("[S] Accepted connection from: %s:%d."%(addr[0], addr[1]))

                try:
                    clientHandler = Thread(target=self.handleClient, args=(clientSocket, addr))
                    clientHandler.start()
                    self.threads[addr] = clientHandler
                except:
                    print("[S] Thread handleClient() did not start.")

        except KeyboardInterrupt:
            for t in self.threads.values():
                t.join(1) #let the thread 1sec to finish

            self.serverSocket.close()
            print("\n[S] Server stopped on user interrupt.")
        

    def handleClient(self, clientSocket, addr):
        request = None
        while request != 'LEAVE':
            #Print out what the client sends
            request = clientSocket.recv(self.bufferSize).decode()
            print("[S] Received request from the client %s:%d : \"%s\"."%(addr[0], addr[1], request))

            #Request handler
            if request == "GET_FILE_LIST":
                self.handleFileListRequest(clientSocket, addr)
            elif request == "FILE_REGISTER":
                self.handleFileRegisterRequest(clientSocket, addr)
            elif request == "FILE_LOCATION":
                self.handleFileLocationRequest(clientSocket, addr)
            elif request == "CHUNK_REGISTER":
                self.handleChunkRegisterRequest(clientSocket, addr)
            elif request == 'LEAVE':
                self.handleLeaveRequest(clientSocket, addr) #self.removeClientFromFilesAvailable(addr) included in it.
                break
            elif len(request) == 0:
                break
            else:
                print("[S] Unknown request, dropping.", request)
        
        #Close the client handler.
        clientSocket.close()
        del self.threads[addr]
        print("[S] Client disconnected %s:%d."%(addr[0], addr[1]))
        
    
    def handleFileListRequest(self, clientSocket, addr): #sends the list of files availlables with the sources.
        # Sends the self.filesAvailable
        data = pickle.dumps(list(self.filesAvailable.keys()))
        for n in range(len(data) // self.bufferSize + 1):
            clientSocket.send(data[n * self.bufferSize: (n + 1) * self.bufferSize])
        clientSocket.send("END_DATA".encode())

        # Check the ACK
        ack = clientSocket.recv(self.bufferSize).decode() #just for an ack...
        assert(ack == "ACK")
        print("[S] Completed request GET_FILE_LIST from the client %s:%d."%(addr[0], addr[1]))
    
    def handleLeaveRequest(self, clientSocket, addr):# The client wishes to disconnect from the P2P network.
        #Receive the server side info about the client
        serverSideAddr = pickle.loads(clientSocket.recv(self.bufferSize))
        
        #remove the client from the file system...
        self.removeClientFromFilesAvailable(serverSideAddr)
        
        #Signal to the client he can leave now.
        clientSocket.send("ACK".encode())
        print("[S] Completed request LEAVE from the client %s:%d."%(addr[0], addr[1]))
    
    def removeClientFromFilesAvailable(self, addr):
        for fileID, sources in self.filesAvailable.copy().items():
            if self.filesAvailable[fileID].get(addr, None) == None:
                continue
            else:
                if len(self.filesAvailable[fileID]) == 1:
                    del self.filesAvailable[fileID] #There was only 1 source.
                else:
                    del self.filesAvailable[fileID][addr] #We remove only the source that left
    
    def handleFileRegisterRequest(self, clientSocket, addr):
        #Tells the client to send the file register data.
        clientSocket.send("SEND".encode())
        
        #Wait for the client to send the file it wants to register
        data = []
        while True:
            packet = clientSocket.recv(self.bufferSize)
            if packet == "END_DATA".encode():
                break
            elif packet[-8:] == "END_DATA".encode(): #8 = len("END_DATA")
                n = len(packet)
                data.append(packet[0:n-8])
                break
            data.append(packet)
        registrationObject = pickle.loads(b"".join(data))
        
        #Send and ACK
        
        clientSocket.send("ACK".encode())
        
        
        #Process the data
        self.filesAvailable
        endPointIP = registrationObject['endPointIP']
        endPointPort = registrationObject['endPointPort']
        assert(registrationObject['nbOfFiles'] == len(registrationObject['filesMetadata'])) #check we get all the infos about every objects
        for meta in registrationObject['filesMetadata']:
            if self.filesAvailable.get(meta, None) == None: #the entry doesn't exist already
                self.filesAvailable[meta] = { (endPointIP, endPointPort): set([k for k in range(meta[3])])} #create a list with all the chunck numbers
            else:
                self.filesAvailable[meta][(endPointIP, endPointPort)] = set([k for k in range(meta[3])])
                
        
        print("[S] Completed request FILE_REGISTER from the client %s:%d."%(addr[0], addr[1]))
    
    def handleFileLocationRequest(self, clientSocket, addr):
        #Tells the client to send the fileID.
        clientSocket.send("SEND".encode())
        
        #Receive fileID
        data = clientSocket.recv(self.bufferSize)
        fileID = pickle.loads(data)

        
        #Return the sources for the fileID
        data = pickle.dumps(self.filesAvailable[fileID])
        for n in range(len(data) // self.bufferSize + 1):
            clientSocket.send(data[n * self.bufferSize: (n + 1) * self.bufferSize])
        clientSocket.send("END_DATA".encode())

        print("[S] Completed request FILE_LOCATION from the client %s:%d."%(addr[0], addr[1]))
        
    def handleChunkRegisterRequest(self, clientSocket, addr):
        #Tells the client to send
        clientSocket.send("SEND".encode())
        
        #Receive the chunkID, the fileID and the endPointIP and endPointPort
        rawData = []
        while True:
            packet = clientSocket.recv(self.bufferSize)
            if packet == "END_DATA".encode():
                break
            elif packet[-8:] == "END_DATA".encode(): #8 = len("END_DATA")
                n = len(packet)
                rawData.append(packet[0:n-8])
                break
            rawData.append(packet)
            
        data = pickle.loads(b"".join(rawData))
        chunksToBeRegistered, fileID, endPointIP, endPointPort = data[0], data[1], data[2], data[3]
        
        #Send an ACK
        clientSocket.send("ACK".encode())
        
        #Add the chunk to the list of sources.
        if self.filesAvailable.get(fileID, None) == None:
            self.filesAvailable[fileID] = {(endPointIP, endPointPort): set([chunkID])}
        else:
            if self.filesAvailable[fileID].get((endPointIP, endPointPort), None) == None:
                self.filesAvailable[fileID][(endPointIP, endPointPort)] = chunksToBeRegistered
            else:
                self.filesAvailable[fileID][(endPointIP, endPointPort)].update(chunksToBeRegistered) #Union
            
        

if __name__ == "__main__":
    S = MainServer()
    S.startServer()