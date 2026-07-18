import asyncio
import random
import time
import uuid
import struct
import socket
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI()
lobbies = {}

# Set to 2 for your buddy test, override with LOBBY_SIZE=8 later
TARGET_LOBBY_SIZE = int(os.getenv("LOBBY_SIZE", 2))

# PHASE 1: EVENT-DRIVEN UDP ICE RELAY (The Shotgun Approach)
class ICERelayProtocol(asyncio.DatagramProtocol):
    def __init__(self):
        self.rooms = {}

    def connection_made(self, transport):
        self.transport = transport
        print("[RELAY] Linux Socket Boundary Bound. Shotgun routing online.")

    def datagram_received(self, data, addr):
        if len(data) < 8:
            return

        session_token = struct.unpack('<Q', data[:8])[0]

        if session_token not in self.rooms:
            self.rooms[session_token] = []

        room_clients = self.rooms[session_token]

        if addr not in room_clients:
            room_clients.append(addr)
            # Expanded to 32 to absorb aggressive Symmetric NAT port scrambling
            if len(room_clients) > 32:
                room_clients.pop(0)

        for client in room_clients:
            if client != addr:
                self.transport.sendto(data, client)


@app.on_event("startup")
async def startup_event():
    loop = asyncio.get_running_loop()

    # Create a raw socket to manually bypass Python's default tiny buffer limits
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # [CRITICAL SERVER PATCH]: Give the Python Relay 4MB kernel queues!
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024 * 4)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024 * 1024 * 4)

    sock.setblocking(False)
    sock.bind(("0.0.0.0", 49152))

    # Pass the supercharged socket into the asyncio loop
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: ICERelayProtocol(),
        sock=sock
    )

    app.state.udp_relay_transport = transport
    print(f"[SYSTEM] Unified HTTP Matchmaker & High-Capacity UDP Relay initialized. Target Lobby Size: {TARGET_LOBBY_SIZE}")


# Base endpoint for joining
class PlayerEndpoint(BaseModel):
    public_ip: str
    public_port: int
    local_ip: str
    local_port: int

# Extended endpoint for hosting
class HostEndpoint(PlayerEndpoint):
    target_size: int = 2  # Default to 1v1 if unspecified

@app.post("/host")
async def host_game(endpoint: HostEndpoint):
    lobby_id = str(uuid.uuid4()).upper()[:4]
    session_token = random.getrandbits(63)

    lobbies[lobby_id] = {
        "session_token": session_token,
        "status": "holding_cell",
        "start_time": 0.0,
        "target_size": endpoint.target_size, # Host dictates the size
        "players": [{
            "ip": endpoint.public_ip,
            "port": endpoint.public_port,
            "local_ip": endpoint.local_ip,
            "local_port": endpoint.local_port
        }]
    }
    return {"lobby_id": lobby_id, "status": "holding_cell", "session_token": session_token}

@app.post("/join/{lobby_id}")
async def join_game(lobby_id: str, endpoint: PlayerEndpoint):
    if lobby_id not in lobbies:
        raise HTTPException(status_code=404, detail="Lobby not found")

    lobby = lobbies[lobby_id]

    if lobby["status"] == "locked":
        raise HTTPException(status_code=403, detail="Lobby is already locked and starting")

    if len(lobby["players"]) >= lobby["target_size"]:
        raise HTTPException(status_code=403, detail="Lobby is full")

    lobby["players"].append({
        "ip": endpoint.public_ip,
        "port": endpoint.public_port,
        "local_ip": endpoint.local_ip,
        "local_port": endpoint.local_port
    })

    # Lock when we hit the Host's target size
    if len(lobby["players"]) == lobby["target_size"]:
        lobby["status"] = "locked"
        lobby["start_time"] = time.time() + 5.0
        print(f"[LOBBY] Lobby {lobby_id} Reached Consensus ({lobby['target_size']}/{lobby['target_size']}). Ignition sequence initiated.")

    return {
        "session_token": lobby["session_token"],
        "players": lobby["players"]
    }


@app.get("/status/{lobby_id}")
async def check_status(lobby_id: str):
    if lobby_id not in lobbies:
        raise HTTPException(status_code=404, detail="Lobby not found")

    lobby = lobbies[lobby_id]

    return {
        "status": lobby["status"],
        "player_count": len(lobby["players"]),
        "players": lobby["players"],
        "start_time": lobby["start_time"],
        "server_time": time.time() # Critical for cross-domain clock synchronization
    }


@app.post("/force_start/{lobby_id}")
async def force_start(lobby_id: str):
    if lobby_id not in lobbies:
        raise HTTPException(status_code=404, detail="Lobby not found")

    lobby = lobbies[lobby_id]
    if lobby["status"] != "locked":
        lobby["status"] = "locked"
        lobby["start_time"] = time.time() + 5.0
        print(f"[DEBUG] Lobby {lobby_id} force-started with {len(lobby['players'])} players.")
    return {"status": "locked", "start_time": lobby["start_time"]}
