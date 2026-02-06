#!/usr/bin/env python3
"""
Inject NMEA 2000 AIS messages to Yacht Devices gateway via UDP

This sends AIS Class A Position Report (PGN 129038) to the YDEN gateway
on UDP port 1458 (TO NMEA 2000).
"""

import socket
import struct
import time
from datetime import datetime

# Yacht Devices endpoint (direct network connection)
YDEN_IP = "192.168.1.22"  # YDEN on local network
TCP_PORT_TO_N2K = 1458  # Write TO NMEA 2000 bus
TCP_PORT_FROM_N2K = 1457  # Read FROM NMEA 2000 bus (broadcast)

# AIS vessel data
MMSI = 211512000
LATITUDE = 54.89  # degrees North
LONGITUDE = 26.0  # degrees East
SOG = 12.3  # knots
COG = 72.0  # degrees
HEADING = 75  # degrees
VESSEL_NAME = "TESTSHIP"


def encode_yacht_devices_message(pgn, priority, src, dst, data):
    """
    Encode a message in Yacht Devices RAW protocol format for TRANSMIT.
    
    Format for TX: 0x93 0x15 <pgn_low> <pgn_mid> <pgn_high> <src> <dst> <len> <data...> <crc>
    
    Note: 0x15 is the transmit command (0x10 is receive)
    """
    message = bytearray()
    
    # Start byte
    message.append(0x93)
    
    # Command: 0x15 = Transmit to N2K bus
    message.append(0x15)
    
    # PGN (3 bytes, little-endian)
    message.append(pgn & 0xFF)
    message.append((pgn >> 8) & 0xFF)
    message.append((pgn >> 16) & 0xFF)
    
    # Source address
    message.append(src)
    
    # Destination address (255 = broadcast)
    message.append(dst)
    
    # Data length
    message.append(len(data))
    
    # Data
    message.extend(data)
    
    # CRC (XOR of all bytes after start byte)
    crc = 0
    for b in message[1:]:
        crc ^= b
    message.append(crc)
    
    return bytes(message)


def create_ais_position_report(mmsi, lat, lon, sog, cog, heading):
    """
    Create PGN 129038 - AIS Class A Position Report
    
    Based on NMEA 2000 PGN 129038 specification.
    """
    data = bytearray()
    
    # Byte 0: Message ID (6 bits) + Repeat Indicator (2 bits)
    # Message Type 1 = Position Report Class A
    msg_id = 1
    repeat = 0
    data.append((repeat << 6) | msg_id)
    
    # Bytes 1-4: User ID (MMSI) - 32 bits, little-endian
    data.extend(struct.pack('<I', mmsi))
    
    # Bytes 5-8: Longitude - 32 bits signed, 1e-7 degrees, little-endian
    lon_int = int(lon * 1e7)
    data.extend(struct.pack('<i', lon_int))
    
    # Bytes 9-12: Latitude - 32 bits signed, 1e-7 degrees, little-endian
    lat_int = int(lat * 1e7)
    data.extend(struct.pack('<i', lat_int))
    
    # Byte 13: Position Accuracy (1 bit) + RAIM (1 bit) + Time Stamp (6 bits)
    accuracy = 1  # High
    raim = 0
    timestamp = datetime.now().second
    data.append((accuracy & 0x01) | ((raim & 0x01) << 1) | ((timestamp & 0x3F) << 2))
    
    # Bytes 14-15: COG - 16 bits unsigned, 1e-4 radians, little-endian
    cog_rad = cog * 0.0174533  # degrees to radians
    cog_int = int(cog_rad * 10000) & 0xFFFF
    data.extend(struct.pack('<H', cog_int))
    
    # Bytes 16-17: SOG - 16 bits unsigned, 0.01 knots, little-endian
    sog_int = int(sog * 100) & 0xFFFF
    data.extend(struct.pack('<H', sog_int))
    
    # Bytes 18-19: Communication State (19 bits) + AIS Transceiver Info (5 bits)
    # Simplified: just use default values
    data.extend([0x00, 0x00])
    
    # Bytes 20-21: True Heading - 16 bits unsigned, 1e-4 radians, little-endian
    heading_rad = heading * 0.0174533
    heading_int = int(heading_rad * 10000) & 0xFFFF
    data.extend(struct.pack('<H', heading_int))
    
    # Bytes 22-23: Rate of Turn - 16 bits signed, 1e-3 rad/s (0x7FFF = not available)
    data.extend([0xFF, 0x7F])
    
    # Byte 24: Nav Status (4 bits) + Reserved (4 bits)
    # 0 = Under way using engine
    nav_status = 0
    data.append(nav_status & 0x0F)
    
    # Byte 25: Reserved
    data.append(0xFF)
    
    # Byte 26: SID (Sequence ID)
    data.append(0xFF)
    
    return bytes(data)


def send_ais_message():
    """Send AIS position report via UDP to Yacht Devices gateway using text format"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    print(f"Injecting AIS message to YDEN at {YDEN_IP}:{TCP_PORT_TO_N2K} (UDP)")
    print(f"Vessel MMSI: {MMSI}")
    print(f"Position: {LATITUDE}°N, {LONGITUDE}°E")
    print(f"Speed: {SOG} knots, Course: {COG}°, Heading: {HEADING}°")
    print()
    
    # Create AIS position report (PGN 129038)
    ais_data = create_ais_position_report(MMSI, LATITUDE, LONGITUDE, SOG, COG, HEADING)
    
    # Convert to hex string for YDEN text format
    data_hex = ' '.join(f'{b:02X}' for b in ais_data)
    
    # YDEN text format: "T PGN dst data"
    # T = Transmit, PGN in hex, dst = 255 (broadcast), data as hex bytes
    pgn_hex = f'{129038:08X}'  # 0001F80E
    
    # Format 1: Simple "T PGN data" format
    msg_text1 = f"T {pgn_hex} FF {data_hex}\r\n"
    
    # Format 2: With timestamp like the received format
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    msg_text2 = f"{timestamp} T {pgn_hex} 32 FF {data_hex}\r\n"
    
    # Format 3: Shorter PGN format (6 hex digits)
    pgn_short = f'{129038:06X}'  # 01F80E
    msg_text3 = f"T {pgn_short} FF {data_hex}\r\n"
    
    print(f"PGN 129038 data ({len(ais_data)} bytes): {ais_data.hex()}")
    print()
    
    # Try all formats
    for i, msg in enumerate([msg_text1, msg_text2, msg_text3], 1):
        print(f"Format {i}: {msg.strip()}")
        sock.sendto(msg.encode('ascii'), (YDEN_IP, TCP_PORT_TO_N2K))
        time.sleep(0.2)
    
    print()
    print("✓ AIS messages sent in multiple text formats!")
    print()
    print("Monitor YDEN output: nc 192.168.1.22 1456 | grep VDM")
    
    sock.close()


if __name__ == "__main__":
    send_ais_message()
