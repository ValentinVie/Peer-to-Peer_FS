#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct  1 18:16:23 2018

@author: vav4
"""

import socket
from threading import Thread
 
TCP_IP = '127.0.0.1' # Listening IP
TCP_PORT = 5005 # Listening Port
BUFFER_SIZE = 1024  # The receive buffer, contains the first message from the client.




class MainServer:
    def __init__(self, IP = TCP_IP, TCPPort = TCP_PORT, bufferSize = BUFFER_SIZE):
        self.IP = IP
        self.TCPPort = TCPPort
        self.bufferSize = bufferSize #Receive buffer size.
        self.threads = [] #list of handleClient threads.
        
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
                    clientHandler = Thread(target=self.handleClient, args=(clientSocket,))
                    clientHandler.start()
                except:
                    print("[S] Thread did not start.")
        except KeyboardInterrupt:
            for t in self.threads:
                t.join(3) # Wait 3s for the thread to finish.
                t.exit() # Exit the thread.
            self.serverSocket.close()
            print("\n[S] Server stopped.")
        

    def handleClient(self, clientSocket):
        #Print out what the client sends
        request = clientSocket.recv(self.bufferSize)
        print("[S] Received from the client %s."%request.decode())
        
        #Sends back a packet
        clientSocket.send("ACK".encode())
        clientSocket.close()
        
            

if __name__ == "__main__":
    S = MainServer()
    S.startServer()