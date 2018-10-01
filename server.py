#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct  1 18:16:23 2018

@author: vav4
"""

import socket
from threading import Thread
 
TCP_IP = '127.0.0.1'
TCP_PORT = 5005
BUFFER_SIZE = 20  # Normally 1024, but we want fast response



conn, addr = s.accept()
print('Connection address:', addr)

while 1:
    data = conn.recv(BUFFER_SIZE)
    if not data: 
        break
    print("received data:", data.decode())
    conn.send(data+'response'.encode())
    
conn.close()

class MainServer:
    def __init__(self, IP, TCPPort, bufferSize):
        self.IP = IP
        self.TCPPort = TCPPort
        self.bufferSize = bufferSize #Receive buffer size.
        
        # Create a TCP/IP socket
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Bind the socket to the port
        self.s.bind((TCP_IP, TCP_PORT))
        # Listen for incoming connections
        self.s.listen(1)# queue up to 1 requests
        print("Server socket now listening")
        
        
        while True:
            self.connection, self.address = self.s.accept()
            self.ip, self.port = self.address[0], self.address[1]
            
            try:
                Thread(target=client_thread, args=(connection, ip, port)).start()
            except:
                print("Thread did not start.")
        

def client_thread(connection, ip, port, max_buffer_size = 5120)

if __name__ == "__main__":
    print("Starting the main server...")
