#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Oct  1 18:19:08 2018

@author: vav4
"""

import socket
import time
import sys

TARGET_IP = '127.0.0.1' # Target IP
TARGET_PORT = 5005 # Target Port
BUFFER_SIZE = 1024 # The receive buffer


# Create a TCP/IP socket
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect the socket to the port where the server is listening
try:
    client.connect((TARGET_IP, TARGET_PORT))
    print("[C] Client connected to the server : %s:%d."% (TARGET_IP, TARGET_PORT))
except ConnectionRefusedError:
    print("[C] Server refused the connexion.")
    print("[C] Aborting.")
    client.close()
    sys.exit()
#wait for instruction

# Send data
client.send("Request client...".encode())

# Look for the response
data = client.recv(BUFFER_SIZE)
print("[C] Received data: %s."% data.decode())

client.close()

