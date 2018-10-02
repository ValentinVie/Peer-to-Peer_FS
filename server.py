#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct  1 18:16:23 2018

@author: vav4
"""

import socket
from threading import Thread
import sys
import pickle
 
TCP_IP = '127.0.0.1' # Listening IP
TCP_PORT = 5005 # Listening Port
BUFFER_SIZE = 1024  # The receive buffer, contains the first message from the client.


class MainServer:
    def __init__(self, IP = TCP_IP, TCPPort = TCP_PORT, bufferSize = BUFFER_SIZE):
        self.IP = IP
        self.TCPPort = TCPPort
        self.bufferSize = bufferSize #Receive buffer size.
        self.threads = [] #list of handleClient threads.
        self.filesAvailable = { 'filename1HASH': {'client1' : ['piece 1', 'peice 2'], 
                                                  'client2': ['piece 3']
                                                 },
                                'HASH file 2':{ 'client2' : ['piece1', 'piece2', 'piece3']
                                              }
                              }
        
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
        self.serverSocket.listen(5)# queue up to 5 requests
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
                except:
                    print("[S] Thread handleClient() did not start.")

        except KeyboardInterrupt:
            for t in self.threads:
                t.join(3) # Wait 3s for the thread to finish.
                t.exit() # Exit the thread.
            self.serverSocket.close()
            print("\n[S] Server stopped on user interrupt.")
        

    def handleClient(self, clientSocket, addr):
        #Print out what the client sends
        request = clientSocket.recv(self.bufferSize).decode()
        print("[S] Received request from the client %s:%d : \"%s\"."%(addr[0], addr[1], request))
        
        #Request handler
        if request == "GET_FILE_LIST":
            self.sendFileList(clientSocket)
        else:
            print("[S] Unknown request, dropping.")
        
        #Sends back a packet
        clientSocket.send("ACK".encode())
        clientSocket.close()
        print("[S] Completed request from the client %s:%d : \"%s\"."%(addr[0], addr[1], request))
    
    def sendFileList(self, clientSocket): #sends the list of files availlables with the sources.
        try:
            # Sends the self.filesAvailable
            data = pickle.dumps(self.filesAvailable)
            clientSocket.send(data)

            # Check the ACK
            ack = clientSocket.recv(self.bufferSize).decode() #just for an ack...
            assert(ack == "ACK")
        except:
            print("[S] sendFileList failed with socket ", clientSocket)
        
        
            

if __name__ == "__main__":
    S = MainServer()
    S.startServer()