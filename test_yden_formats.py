#!/usr/bin/env python3
"""
Test script to verify YDEN RAW protocol format and transmission.
Tries multiple message formats to see what works.
"""

import socket
import struct
import time

YDEN_IP = "192.168.1.22"
UDP_PORT = 1458

def send_raw(data, description):
    """Send raw bytes to YDEN and print hex"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print(f"\n{description}")
    print(f"  Hex: {data.hex()}")
    print(f"  Len: {len(data)} bytes")
    sock.sendto(data, (YDEN_IP, UDP_PORT))
    sock.close()
    time.sleep(0.5)

# Test MMSI and position
MMSI = 211512000
LAT = int(54.89 * 1e7)  # 54.89°N
LON = int(26.0 * 1e7)   # 26°E
SOG = int(12.3 * 100)   # 12.3 knots
COG = int(72.0 * 0.0174533 * 10000)  # 72° in 1e-4 rad
HDG = int(75.0 * 0.0174533 * 10000)  # 75° in 1e-4 rad

print("=" * 60)
print("Testing YDEN NMEA 2000 RAW transmission formats")
print("=" * 60)

# === Format 1: Standard Yacht Devices RAW ===
# Based on YD RAW protocol: https://www.yachtd.com/downloads/ydwg02.pdf
# TX format may be: 0x93 0x15 <PGN 3 bytes LE> <src> <dst> <len> <data> <crc>

pgn = 129038
data = bytearray()
data.append(0x01)  # Message type 1
data.extend(struct.pack('<I', MMSI))
data.extend(struct.pack('<i', LON))
data.extend(struct.pack('<i', LAT))
data.append(0x00)  # Accuracy/RAIM/Timestamp
data.extend(struct.pack('<H', COG))
data.extend(struct.pack('<H', SOG))
data.extend([0x00, 0x00])  # Comm state
data.extend(struct.pack('<H', HDG))
data.extend([0xFF, 0x7F])  # ROT
data.append(0x00)  # Nav status

msg1 = bytearray([0x93, 0x15])
msg1.extend(struct.pack('<I', pgn)[:3])
msg1.append(50)   # src
msg1.append(255)  # dst
msg1.append(len(data))
msg1.extend(data)
crc = 0
for b in msg1[1:]:
    crc ^= b
msg1.append(crc)
send_raw(bytes(msg1), "Format 1: YD RAW TX (0x93 0x15)")

# === Format 2: Try with priority byte ===
msg2 = bytearray([0x93, 0x15, 0x04])  # Add priority
msg2.extend(struct.pack('<I', pgn)[:3])
msg2.append(50)   # src
msg2.append(255)  # dst
msg2.append(len(data))
msg2.extend(data)
crc = 0
for b in msg2[1:]:
    crc ^= b
msg2.append(crc)
send_raw(bytes(msg2), "Format 2: YD RAW TX with priority")

# === Format 3: Actisense-like NGT-1 format ===
# NGT-1 uses: <DLE><STX><cmd><len><data><crc><DLE><ETX>
DLE = 0x10
STX = 0x02
ETX = 0x03

actisense_data = bytearray()
actisense_data.append(0x04)  # Priority
actisense_data.extend(struct.pack('<I', pgn)[:3])
actisense_data.append(255)  # dst
actisense_data.append(50)   # src
actisense_data.append(len(data))
actisense_data.extend(data)

msg3 = bytearray([DLE, STX, 0x93])  # 0x93 = N2K message command
msg3.append(len(actisense_data))
msg3.extend(actisense_data)
crc = sum(msg3[2:]) & 0xFF
msg3.append(crc)
msg3.extend([DLE, ETX])
send_raw(bytes(msg3), "Format 3: Actisense-style framing")

# === Format 4: Simple PGN broadcast ===
# Some gateways just want: <pgn><data>
msg4 = bytearray()
msg4.extend(struct.pack('<I', pgn))
msg4.extend(data)
send_raw(bytes(msg4), "Format 4: Simple PGN + data")

print("\n" + "=" * 60)
print("Sent 4 different formats. Check YDEN TCP 1456 for AIS output.")
print("Run: nc 192.168.1.22 1456 | grep -i 'VDM\\|AIS\\|129038'")
print("=" * 60)
