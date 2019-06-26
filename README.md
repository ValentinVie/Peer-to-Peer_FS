# Peer-to-Peer File System - Networking class project

## Introduction
In this project, I design and implement a simple peer-to-peer (P2P) file sharing system using TCP/IP. The goal is to gain experience on implementing a centralized P2P network.

See `instructions.pdf` for complete information about the project.

## Protocol
Here are the key component of our P2P protocol:

| Peer Request | Server Reply |
|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Register Request:** Tells the server what files the peer wants to share with the network. Takes in the IP address and port for the end- point to accept peer connections for download; the number of files to register; and for every file, a file name (string) and its length. | **Register Reply:** For each file, it advises if the file registration was a success (Boolean). |
| **File List Request:** Asks the server for the list of files. | **File List Reply:** Includes the number of files in the list; and for each file, a file name (string) and a file length. |
| **File Locations Request:** Asks the server for the IP endpoints of the peers containing the requested file (string). | **File Locations Reply:** Includes number of endpoints; then for each endpoint, chunks of the file it has, an IP address and port. |
| **Chunk Register Request:** Tells the server when a peer receives a new chunk of the file and becomes a source (of that chunk) for other peers. | **Chunk Register Reply:** Advises if the chunk registration was a success (Boolean). |
| **Leave Request:** Tells the server remove this peer and all its files (chunks) from the network. | **Leave Reply:** Ad- vises if the peer was removed successfully (Boolean). |

To learn more about the protocol, check `lab1_report.pdf`

## P2P Requirements
• **Multiple Connections:** The peers and servers are able to support multiple connections simultaneously. We cannot delay any message arbitrarily because of lack of parallelism. We use multithreading to handle the connection between each party.

• **Parallel Downloading:** The system is able to download a file from multiple peers and assemble the file. Before downloading, the client get the number of chunks from a server and the sources and downloads the file in parts from multiple peers simultaneously. To ensure integrity of downloaded file, a hash function is used.

• **Chunk management:** Upon finishing the download of a chunk, a peer registers that chunk with the server to become a source (of that chunk) for other peers. When a peer downloads chunks from another peer, it downloads the “rarest first”.

## Demo

In this demonstration we have 3 peers (clients) and one tracker (server). Each client has a sharing folder `./1` for client #1, `./2` for client #2... We first get the metadata of the files that are being shared by asking the tracker. Then we contact again the tracker to get the chunks each peer has about a spacific file and the download start.

Here peers #3 and #2 download `climbing.jpg`from peer #1 (simultaneously). Then peer #1 downloads `bear.jpg` from peer #2.

<p align="center">
	<img src="./demo.gif" />
</p>

## Usage

1. `server.py` : The server (tracker) base code, serving the peer.
Gives all the files availlable, the peers availlable and also return which pieces are the rarest.

2. `client.py`: The peer code. Sends and receives data from other peers.
