#!/usr/bin/env python3
"""
Inject AIS NMEA 2000 messages via Actisense gateway using n2k-cli

This creates JSON-formatted NMEA2000 messages and pipes them to n2k-cli write mode
to transmit to the NMEA 2000 bus via the Actisense NGX-1-USB gateway.
"""

import json
import struct
from datetime import datetime

# Test vessel data
MMSI = 211512000  # Test MMSI (Germany)
LATITUDE = 54.89   # degrees N
LONGITUDE = 26.0   # degrees E
SOG = 12.3        # knots
COG = 72.0        # degrees
HEADING = 75      # degrees

def create_ais_class_a_position_report():
    """
    Create PGN 129038 - AIS Class A Position Report
    
    Field structure:
    - Message ID (2 bits) = 1 (position report)
    - Repeat indicator (2 bits) = 0
    - User ID (MMSI) (4 bytes)
    - Longitude (4 bytes, 1e-7 degrees)
    - Latitude (4 bytes, 1e-7 degrees)
    - Position accuracy (1 bit)
    - RAIM flag (1 bit)
    - Time stamp (6 bits)
    - COG (2 bytes, 1e-4 radians)
    - SOG (2 bytes, 0.01 m/s)
    - Communication state (19 bits)
    - AIS transceiver information (5 bits)
    - Heading (2 bytes, 1e-4 radians)
    - Rate of turn (2 bytes)
    - Nav status (4 bits)
    - Reserved (1 byte)
    - Regional reserved (1 byte)
    - Spare (1 bit)
    """
    import math
    
    data = bytearray(27)
    
    # Byte 0: Message ID (1) + Repeat indicator (0) = 0x01
    data[0] = 0x01
    
    # Bytes 1-4: MMSI (little-endian)
    struct.pack_into('<I', data, 1, MMSI)
    
    # Bytes 5-8: Longitude (1e-7 degrees, little-endian)
    lon_raw = int(LONGITUDE * 1e7)
    struct.pack_into('<i', data, 5, lon_raw)
    
    # Bytes 9-12: Latitude (1e-7 degrees, little-endian)
    lat_raw = int(LATITUDE * 1e7)
    struct.pack_into('<i', data, 9, lat_raw)
    
    # Byte 13: Position accuracy (1 bit) + RAIM (1 bit) + Timestamp (6 bits)
    timestamp_seconds = datetime.now().second
    data[13] = (0x01 << 0) | (0x00 << 1) | ((timestamp_seconds & 0x3F) << 2)
    
    # Bytes 14-15: COG (1e-4 radians)
    cog_rad = COG * math.pi / 180.0
    cog_raw = int(cog_rad * 1e4)
    struct.pack_into('<H', data, 14, cog_raw)
    
    # Bytes 16-17: SOG (0.01 m/s)
    sog_ms = SOG * 0.514444  # knots to m/s
    sog_raw = int(sog_ms * 100)
    struct.pack_into('<H', data, 16, sog_raw)
    
    # Bytes 18-20: Communication state (19 bits) + Transceiver (5 bits)
    # Using simple values for testing
    data[18] = 0x00
    data[19] = 0x00
    data[20] = 0x00
    
    # Bytes 21-22: Heading (1e-4 radians)
    hdg_rad = HEADING * math.pi / 180.0
    hdg_raw = int(hdg_rad * 1e4)
    struct.pack_into('<H', data, 21, hdg_raw)
    
    # Bytes 23-24: Rate of turn (0x7FFF = not available)
    struct.pack_into('<h', data, 23, 0x7FFF)
    
    # Byte 25: Nav status (0 = under way using engine)
    data[25] = 0x00
    
    # Byte 26: Reserved
    data[26] = 0xFF
    
    return bytes(data)


def create_nmea2000_json_message(pgn, priority, src, dst, data):
    """Create JSON message compatible with n2k-cli write mode"""
    
    msg = {
        "timestamp": datetime.now().isoformat(),
        "prio": priority,
        "src": src,
        "dst": dst,
        "pgn": pgn,
        "description": "AIS Class A Position Report",
        "fields": {
            # Decoded fields (optional, raw data takes precedence)
            "Message ID": 1,
            "MMSI": str(MMSI),
            "Longitude": LONGITUDE,
            "Latitude": LATITUDE,
            "COG": COG,
            "SOG": SOG,
            "Heading": HEADING,
        },
        # Raw data in hex format
        "data": data.hex()
    }
    return msg


def main():
    print("=" * 60, file=__import__('sys').stderr)
    print("AIS Injection via Actisense NGX-1-USB", file=__import__('sys').stderr)
    print("=" * 60, file=__import__('sys').stderr)
    print(f"MMSI: {MMSI}", file=__import__('sys').stderr)
    print(f"Position: {LATITUDE}°N, {LONGITUDE}°E", file=__import__('sys').stderr)
    print(f"Speed: {SOG} kn, Course: {COG}°, Heading: {HEADING}°", file=__import__('sys').stderr)
    print("=" * 60, file=__import__('sys').stderr)
    
    # Create AIS data
    ais_data = create_ais_class_a_position_report()
    
    # Create JSON message
    msg = create_nmea2000_json_message(
        pgn=129038,
        priority=4,
        src=50,  # Our source address
        dst=255,  # Broadcast
        data=ais_data
    )
    
    print(f"Data ({len(ais_data)} bytes): {ais_data.hex()}", file=__import__('sys').stderr)
    print("", file=__import__('sys').stderr)
    print("JSON message to stdout:", file=__import__('sys').stderr)
    print("-" * 40, file=__import__('sys').stderr)
    
    # Output JSON to stdout for piping to n2k-cli
    json_str = json.dumps(msg)
    print(json_str)  # This goes to stdout
    
    print("-" * 40, file=__import__('sys').stderr)
    print("", file=__import__('sys').stderr)
    print("To send via Actisense, run:", file=__import__('sys').stderr)
    print("  python3 inject_ais_actisense.py | python3 bin/n2k-cli write \\", file=__import__('sys').stderr)
    print("    --gateway-type usb --protocol actisense --port /dev/ttyUSB0", file=__import__('sys').stderr)


if __name__ == "__main__":
    main()
