#!/usr/bin/env python3
"""
ANavS Position Decoder

This script decodes position data from ANavS positioning systems supporting two input formats:
1. ANavS binary protocol (via TCP stream on port 6001)
2. CAN bus messages in candump format

Usage:
    # For binary protocol from ANavS device:
    socat TCP:192.168.1.124:6001 STDOUT | ./can-anavs-msg.py
    
    # For CAN bus messages:
    candump can0 | ./can-anavs-msg.py

Output:
    JSON objects with position data when lat/lon/height are available:
    {
        "ts_unix": 1725702128.23,
        "ingress_ns": 1725702128230000000,
        "lat": 57.123456,
        "lon": 11.987654,
        "height_m": 12.34,
        "res_code": 1234,
        "week": 2282,
        "tow": 123456.789
    }
"""

import sys
import time
import logging
import warnings
import re
import struct
import json

# ANavS Binary Protocol Constants
SYNC_CHAR_1 = 0xB5
SYNC_CHAR_2 = 0x62
CLASS_ID = 0x02
MESSAGE_ID = 0xE0

# Mapping of ANavS CAN variable IDs to (name, type)
# Based on ANavS CAN output spec (subset for position)
ID_MAP = {
    1: ("resCode", "uint16"),
    2: ("week", "uint16"),
    3: ("tow", "double"),
    4: ("weekInit", "uint16"),
    5: ("towInit", "double"),
    7: ("lat", "double"),
    8: ("lon", "double"),
    9: ("height", "double"),
}

def fletcher_checksum(data):
    """Calculate Fletcher-16 checksum with modulo 256 as per ANavS spec."""
    ck_a = 0
    ck_b = 0
    for byte in data:
        ck_a = (ck_a + byte) % 256
        ck_b = (ck_b + ck_a) % 256
    return ck_a, ck_b

def parse_anavs_binary(data_buffer):
    """Parse ANavS binary protocol messages from a data buffer.
    
    Returns: (consumed_bytes, messages_list)
    Where messages_list contains decoded position data dictionaries.
    """
    messages = []
    consumed = 0
    
    while len(data_buffer) >= 8:  # Minimum message size
        # Look for sync pattern
        sync_pos = -1
        for i in range(len(data_buffer) - 1):
            if data_buffer[i] == SYNC_CHAR_1 and data_buffer[i + 1] == SYNC_CHAR_2:
                sync_pos = i
                break
        
        if sync_pos == -1:
            # No sync found, consume all but last byte
            consumed = max(0, len(data_buffer) - 1)
            break
            
        # Skip any bytes before sync
        if sync_pos > 0:
            consumed += sync_pos
            data_buffer = data_buffer[sync_pos:]
            logging.debug(f"Skipped {sync_pos} bytes to find sync")
            continue
            
        # Check if we have enough bytes for header
        if len(data_buffer) < 6:
            break
            
        # Parse header: sync1(1) + sync2(1) + class(1) + id(1) + length(2)
        try:
            sync1, sync2, msg_class, msg_id, length = struct.unpack('<BBBBH', data_buffer[:6])
        except struct.error as e:
            logging.warning(f"Header unpack error: {e}, buffer len: {len(data_buffer)}")
            consumed += 2
            data_buffer = data_buffer[2:]
            continue
        
        # Validate header
        if sync1 != SYNC_CHAR_1 or sync2 != SYNC_CHAR_2 or msg_class != CLASS_ID or msg_id != MESSAGE_ID:
            # Invalid header, skip this sync and continue
            logging.debug(f"Invalid header: sync={sync1:02x}{sync2:02x}, class={msg_class:02x}, id={msg_id:02x}")
            consumed += 2
            data_buffer = data_buffer[2:]
            continue
            
        # Check if we have complete message
        total_msg_len = 6 + length + 2  # header + payload + checksum
        if len(data_buffer) < total_msg_len:
            logging.debug(f"Incomplete message: need {total_msg_len}, have {len(data_buffer)}")
            break
            
        # Extract payload and checksum
        payload = data_buffer[6:6+length]
        checksum = data_buffer[6+length:6+length+2]
        
        # Verify checksum
        checksum_data = data_buffer[2:6+length]  # class + id + length + payload
        expected_ck_a, expected_ck_b = fletcher_checksum(checksum_data)
        received_ck_a, received_ck_b = struct.unpack('<BB', checksum)
        
        if expected_ck_a != received_ck_a or expected_ck_b != received_ck_b:
            logging.warning(f"Checksum mismatch: expected {expected_ck_a:02x}{expected_ck_b:02x}, got {received_ck_a:02x}{received_ck_b:02x}")
            consumed += 2
            data_buffer = data_buffer[2:]
            continue
            
        # Parse payload
        try:
            pos_data = parse_anavs_payload(payload)
            if pos_data:
                messages.append(pos_data)
                logging.debug(f"Successfully parsed ANavS message, payload length: {length}")
        except Exception as e:
            logging.warning(f"Failed to parse payload: {e}")
            
        # Consume this message
        consumed += total_msg_len
        data_buffer = data_buffer[total_msg_len:]
        
    return consumed, messages

def parse_anavs_payload(payload):
    """Parse ANavS binary payload to extract position data."""
    if len(payload) < 79:  # Minimum payload size for position data
        return None
        
    try:
        # Parse according to ANavS binary format specification
        offset = 0
        
        # id (uint8)
        msg_id = struct.unpack('<B', payload[offset:offset+1])[0]
        offset += 1
        
        # resCode (uint16)
        res_code = struct.unpack('<H', payload[offset:offset+2])[0]
        offset += 2
        
        # week (uint16)
        week = struct.unpack('<H', payload[offset:offset+2])[0]
        offset += 2
        
        # tow (double)
        tow = struct.unpack('<d', payload[offset:offset+8])[0]
        offset += 8
        
        # weekInit (uint16)
        week_init = struct.unpack('<H', payload[offset:offset+2])[0]
        offset += 2
        
        # towInit (double)
        tow_init = struct.unpack('<d', payload[offset:offset+8])[0]
        offset += 8
        
        # reserved (int16)
        offset += 2
        
        # lat (double)
        lat = struct.unpack('<d', payload[offset:offset+8])[0]
        offset += 8
        
        # lon (double)
        lon = struct.unpack('<d', payload[offset:offset+8])[0]
        offset += 8
        
        # height (double)
        height = struct.unpack('<d', payload[offset:offset+8])[0]
        offset += 8
        
        # ECEF-X (double)
        ecef_x = struct.unpack('<d', payload[offset:offset+8])[0]
        offset += 8
        
        # ECEF-Y (double)
        ecef_y = struct.unpack('<d', payload[offset:offset+8])[0]
        offset += 8
        
        # ECEF-Z (double)
        ecef_z = struct.unpack('<d', payload[offset:offset+8])[0]
        offset += 8
        
        return {
            'msg_id': msg_id,
            'res_code': res_code,
            'week': week,
            'tow': tow,
            'lat': lat,
            'lon': lon,
            'height': height,
            'ecef_x': ecef_x,
            'ecef_y': ecef_y,
            'ecef_z': ecef_z,
            'timestamp': time.time()
        }
        
    except struct.error as e:
        logging.warning(f"Struct unpacking error: {e}")
        return None

_DOUBLE = lambda b: struct.unpack('<d', b)[0]
_U16 = lambda b: struct.unpack('<H', b[:2])[0]
_U8 = lambda b: b[0]

_DOUBLE = lambda b: struct.unpack('<d', b)[0]
_U16 = lambda b: struct.unpack('<H', b[:2])[0]
_U8 = lambda b: b[0]

TYPE_UNPACK = {
    'double': _DOUBLE,
    'uint16': _U16,
    'uint8': _U8,
}

# Regex patterns for common candump style lines
_CANDUMP_PATTERNS = [
    # candump: "can0  007   [8]  01 02 03 04 05 06 07 08"
    re.compile(r"^(?P<if>\w+)\s+(?P<id>[0-9A-Fa-f]{3,8})\s+\[(?P<dlc>\d)\]\s+(?P<data>(?:[0-9A-Fa-f]{2}\s*){0,16})$"),
    # compact: "123#0102030405060708"
    re.compile(r"^(?P<id>[0-9A-Fa-f]{3,8})#(?P<data>[0-9A-Fa-f]{0,16})$"),
    # candump with parens timestamp: "(000.000000) can0 123#0102..."
    re.compile(r"^\([^)]*\)\s+\w+\s+(?P<id>[0-9A-Fa-f]{3,8})#(?P<data>[0-9A-Fa-f]{0,16})$"),
]

def parse_can_line(line: str):
    """Parse a CAN textual line into (id_int, data_bytes) or return None.

    Supports several common candump / compact formats.
    """
    line = line.strip()
    if not line:
        return None
    for pat in _CANDUMP_PATTERNS:
        m = pat.match(line)
        if m:
            try:
                can_id = int(m.group('id'), 16)
                data_hex = m.group('data').replace(' ', '')
                # Pad if odd length (shouldn't happen)
                if len(data_hex) % 2:
                    data_hex = data_hex[:-1]
                data = bytes.fromhex(data_hex)
                return can_id, data
            except Exception:  # noqa
                return None
    return None

class PositionAggregator:
    """Aggregates latitude, longitude, height from incoming CAN frames or binary messages.

    Emits a JSON line when all three are available and at least one updated.
    """
    def __init__(self):
        self.values = {"lat": None, "lon": None, "height": None}
        self._last_emit = 0.0

    def update(self, name: str, value, ingress_ns: int):
        if name not in self.values:
            return None
        changed = (self.values[name] != value)
        self.values[name] = value
        if changed and all(v is not None for v in self.values.values()):
            # Emit if at least 100ms since last emission or value changed
            now = time.time()
            if (now - self._last_emit) >= 0.1:
                self._last_emit = now
                out = {
                    "ts_unix": now,
                    "ingress_ns": ingress_ns,
                    "lat": self.values["lat"],
                    "lon": self.values["lon"],
                    "height_m": self.values["height"],
                }
                return out
        return None
    
    def update_from_binary(self, pos_data):
        """Update position from ANavS binary message and emit if valid."""
        if not pos_data:
            return None
            
        now = time.time()
        ingress_ns = int(now * 1e9)
        
        # Check if any position data changed
        changed = (
            self.values["lat"] != pos_data["lat"] or
            self.values["lon"] != pos_data["lon"] or
            self.values["height"] != pos_data["height"]
        )
        
        # Update values
        self.values["lat"] = pos_data["lat"]
        self.values["lon"] = pos_data["lon"] 
        self.values["height"] = pos_data["height"]
        
        if changed and all(v is not None for v in self.values.values()):
            # Emit if at least 100ms since last emission or value changed
            if (now - self._last_emit) >= 0.1:
                self._last_emit = now
                out = {
                    "ts_unix": now,
                    "ingress_ns": ingress_ns,
                    "lat": self.values["lat"],
                    "lon": self.values["lon"],
                    "height_m": self.values["height"],
                    "res_code": pos_data.get("res_code"),
                    "week": pos_data.get("week"),
                    "tow": pos_data.get("tow"),
                    "ecef_x": pos_data.get("ecef_x"),
                    "ecef_y": pos_data.get("ecef_y"),
                    "ecef_z": pos_data.get("ecef_z"),
                }
                return out
        return None

pos_agg = PositionAggregator()

if __name__ == "__main__":

    # Setup logger
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s :%(lineno)d %(message)s", level=10
    )
    logging.captureWarnings(True)
    warnings.filterwarnings("once")

    # Buffer for binary data
    binary_buffer = bytearray()

    # Process input stream
    while True:
        try:
            # Read data in chunks for binary protocol
            chunk = sys.stdin.buffer.read(4096)
            if not chunk:
                time.sleep(0.001)
                continue
                
            ingress_timestamp = time.time_ns()
            
            # Add to binary buffer
            binary_buffer.extend(chunk)
            
            # Try to parse ANavS binary messages first
            try:
                consumed, messages = parse_anavs_binary(binary_buffer)
                if consumed > 0:
                    binary_buffer = binary_buffer[consumed:]
                    
                for pos_data in messages:
                    emit = pos_agg.update_from_binary(pos_data)
                    if emit:
                        print(json.dumps(emit), flush=True)
                        logging.debug(f"Decoded binary position: lat={pos_data['lat']:.6f}, lon={pos_data['lon']:.6f}, height={pos_data['height']:.2f}")
            except Exception as e:
                logging.warning(f"Binary parsing error: {e}")
                # Clear some buffer to prevent repeated errors
                if len(binary_buffer) > 1000:
                    binary_buffer = binary_buffer[100:]
            
            # If no binary messages were parsed, try CAN line parsing
            if not messages and chunk:
                try:
                    # Convert chunk to text lines and process each
                    text_data = chunk.decode('ascii', errors='ignore')
                    lines = text_data.split('\n')
                    
                    for line in lines:
                        if not line.strip():
                            continue
                            
                        parsed = parse_can_line(line)
                        if parsed:
                            can_id, data_bytes = parsed
                            if can_id in ID_MAP:
                                name, typ = ID_MAP[can_id]
                                unpack = TYPE_UNPACK.get(typ)
                                if unpack:
                                    try:
                                        value = unpack(data_bytes)
                                        emit = pos_agg.update(name, value, ingress_timestamp)
                                        logging.debug(f"Decoded CAN {name} (ID {can_id})={value}")
                                        if emit:
                                            print(json.dumps(emit), flush=True)
                                    except Exception as e:
                                        logging.warning(f"Failed to unpack CAN {name} id={can_id}: {e}")
                        else:
                            logging.debug(f"Unparsed line: {line.strip()}")
                            
                except UnicodeDecodeError:
                    # Data is likely binary, already handled above
                    pass
                except Exception as e:
                    logging.warning(f"Error processing text data: {e}")
            
            # Prevent buffer from growing too large
            if len(binary_buffer) > 65536:
                # Keep only the last portion
                binary_buffer = binary_buffer[-32768:]
                logging.warning("Binary buffer overflow, truncating")
                
        except KeyboardInterrupt:
            logging.info("Interrupted by user")
            break
        except struct.error as e:
            logging.warning(f"Struct error: {e}")
            time.sleep(0.1)
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            time.sleep(0.1)


        