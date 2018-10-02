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

TARGET_IP = '127.0.0.1' # Target IP
TARGET_PORT = 5005 # Target Port
BUFFER_SIZE = 1024 # The receive buffer

class Client:
    def __init__(self, targetIP = TARGET_IP, targerPort = TARGET_PORT, bufferSize = BUFFER_SIZE):
        self.filesAvailable = {}
        self.targetIP = TARGET_IP
        self.targerPort = TARGET_PORT
        self.bufferSize = BUFFER_SIZE
        
        # Create a TCP/IP socket
        self.clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Connect the socket to the port where the server is listening
        try:
            self.clientSocket.connect((self.targetIP, self.targerPort))
            print("[C] Client connected to the server : %s:%d."% (self.targetIP, self.targerPort))
        except ConnectionRefusedError:
            print("[C] Server refused the connexion.")
            print("[C] Aborting.")
            self.clientSocket.close()
            sys.exit()
        
        #self.startServerSide()
        #self.sendRegisterRequest()
        #self.startClientSide()
    
    def sendRegisterRequest(self):
        print("[C] Send register request.")
        pass
        
    def startServerSide(self):
        print("[C] Server side started.")
        pass
    
    
    def startClientSide(self):
        print("[C] Welcome, please choose the file you wish to download.")
        self.sendFileListRequest()
        
        print(self.filesAvailable)

        #wait for instruction

#        # Send data
#        self.clientSocket.send("Message from client".encode())
#
#        # Look for the response
#        data = self.clientSocket.recv(self.bufferSize)
#        print("[C] Received data: %s."% data.decode())

        self.clientSocket.close()
        
    def sendFileListRequest(self):
        # Sends request
        self.clientSocket.send("GET_FILE_LIST".encode())
        
        # Look for the response
        data = self.clientSocket.recv(self.bufferSize)
        self.filesAvailable = pickle.loads(data)
        
        # Sends the ACK
        self.clientSocket.send("ACK".encode())

if __name__ == "__main__":
    C = Client()
    C.startClientSide()