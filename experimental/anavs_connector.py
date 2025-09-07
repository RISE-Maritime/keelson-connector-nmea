#!/usr/bin/env python3
"""
ANavS Keelson Connector

This connector reads ANavS binary protocol data and publishes it via Keelson/Zenoh.
It can connect directly to an ANavS device via TCP or read from stdin.

Usage:
    # Connect to ANavS device directly:
    python3 anavs_connector.py -e vessel_name
    
    # Read from stdin (e.g., from socat):
    socat TCP:192.168.1.124:6001 STDOUT | python3 anavs_connector.py --input-mode stdin -e vessel_name
"""

import zenoh
import logging
import warnings
import json
import time
import keelson
import sys
import socket
import struct
from datetime import datetime, timedelta
import pytz
from terminal_inputs import terminal_inputs
from keelson.payloads.Primitives_pb2 import TimestampedBytes, TimestampedInt, TimestampedFloat, TimestampedString, TimestampedTimestamp
from keelson.payloads.foxglove.LocationFix_pb2 import LocationFix

# ANavS Binary Protocol Constants
SYNC_CHAR_1 = 0xB5
SYNC_CHAR_2 = 0x62
CLASS_ID = 0x02
MESSAGE_ID = 0xE0

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
    """Parse ANavS binary payload to extract position, velocity, acceleration, and attitude data."""
    if len(payload) < 170:  # Minimum payload size for extended data
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
        
        # b - Baseline in NED frame (3*double)
        baseline_n = struct.unpack('<d', payload[offset:offset+8])[0]
        offset += 8
        baseline_e = struct.unpack('<d', payload[offset:offset+8])[0]
        offset += 8
        baseline_d = struct.unpack('<d', payload[offset:offset+8])[0]
        offset += 8
        
        # bStdDev - Standard deviation of baseline (3*double)
        baseline_std_n = struct.unpack('<d', payload[offset:offset+8])[0]
        offset += 8
        baseline_std_e = struct.unpack('<d', payload[offset:offset+8])[0]
        offset += 8
        baseline_std_d = struct.unpack('<d', payload[offset:offset+8])[0]
        offset += 8
        
        # vel - Velocity in NED frame (3*double)
        vel_n = struct.unpack('<d', payload[offset:offset+8])[0]
        offset += 8
        vel_e = struct.unpack('<d', payload[offset:offset+8])[0]
        offset += 8
        vel_d = struct.unpack('<d', payload[offset:offset+8])[0]
        offset += 8
        
        # velStdDev - Standard deviation of velocity (3*double)
        vel_std_n = struct.unpack('<d', payload[offset:offset+8])[0]
        offset += 8
        vel_std_e = struct.unpack('<d', payload[offset:offset+8])[0]
        offset += 8
        vel_std_d = struct.unpack('<d', payload[offset:offset+8])[0]
        offset += 8
        
        # acc - Acceleration in body frame (3*double)
        acc_x = struct.unpack('<d', payload[offset:offset+8])[0]
        offset += 8
        acc_y = struct.unpack('<d', payload[offset:offset+8])[0]
        offset += 8
        acc_z = struct.unpack('<d', payload[offset:offset+8])[0]
        offset += 8
        
        # accStdDev - Standard deviation of acceleration (3*double)
        acc_std_x = struct.unpack('<d', payload[offset:offset+8])[0]
        offset += 8
        acc_std_y = struct.unpack('<d', payload[offset:offset+8])[0]
        offset += 8
        acc_std_z = struct.unpack('<d', payload[offset:offset+8])[0]
        offset += 8
        
        # att - Attitude/Euler angles in degrees (heading, pitch, roll) (3*double)
        heading = struct.unpack('<d', payload[offset:offset+8])[0]
        offset += 8
        pitch = struct.unpack('<d', payload[offset:offset+8])[0]
        offset += 8
        roll = struct.unpack('<d', payload[offset:offset+8])[0]
        offset += 8
        
        # attStdDev - Standard deviation of attitude (3*double)
        att_std_heading = struct.unpack('<d', payload[offset:offset+8])[0]
        offset += 8
        att_std_pitch = struct.unpack('<d', payload[offset:offset+8])[0]
        offset += 8
        att_std_roll = struct.unpack('<d', payload[offset:offset+8])[0]
        offset += 8
        
        # Convert GPS time to UTC datetime
        # GPS epoch is January 6, 1980
        gps_epoch = datetime(1980, 1, 6, tzinfo=pytz.utc)
        gps_seconds = week * 7 * 24 * 3600 + tow
        message_timestamp = gps_epoch + timedelta(seconds=gps_seconds)
        utc_timestamp = message_timestamp  # GPS time is already in UTC (with leap seconds)
        
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
            'baseline': [baseline_n, baseline_e, baseline_d],
            'baseline_std': [baseline_std_n, baseline_std_e, baseline_std_d],
            'velocity_ned': [vel_n, vel_e, vel_d],
            'velocity_std': [vel_std_n, vel_std_e, vel_std_d],
            'acceleration_body': [acc_x, acc_y, acc_z],
            'acceleration_std': [acc_std_x, acc_std_y, acc_std_z],
            'attitude': [heading, pitch, roll],
            'attitude_std': [att_std_heading, att_std_pitch, att_std_roll],
            'timestamp': message_timestamp,
            'utc_timestamp': utc_timestamp
        }
        
    except struct.error as e:
        logging.warning(f"Struct unpacking error: {e}")
        return None
    except IndexError as e:
        logging.warning(f"Payload too short for extended parsing: {e}")
        return None

def create_tcp_connection(host, port):
    """Create TCP connection to ANavS device."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10.0)  # 10 second timeout
        sock.connect((host, port))
        sock.settimeout(1.0)   # 1 second timeout for reads
        logging.info(f"Connected to ANavS device at {host}:{port}")
        return sock
    except Exception as e:
        logging.error(f"Failed to connect to ANavS device: {e}")
        return None

def main():
    # Input arguments and configurations
    args = terminal_inputs()
    
    # Setup logger
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s :%(lineno)d %(message)s", 
        level=args.log_level
    )
    logging.captureWarnings(True)
    warnings.filterwarnings("once")

    ## Construct session
    logging.info("Opening Zenoh session...")
    zenoh.init_log_from_env_or("error")

    conf = zenoh.Config()
    if args.connect is not None:
        conf.insert_json5("connect/endpoints", json.dumps(args.connect))
    
    with zenoh.open(conf) as session:
        logging.info("Zenoh session opened.")

        #################################################
        # Setting up PUBLISHERS

        # RAW binary data publisher
        key_exp_pub_raw = keelson.construct_pubsub_key(
            base_path=args.realm,
            entity_id=args.entity_id,
            subject="raw",  
            source_id=args.source_id + "/binary",
        )
        pub_raw = session.declare_publisher(
            key_exp_pub_raw, congestion_control=zenoh.CongestionControl.DROP
        )
        logging.info(f"Created RAW publisher: {key_exp_pub_raw}")

        # # Location fix publisher
        # key_exp_pub_location_fix = keelson.construct_pubsub_key(
        #     base_path=args.realm,
        #     entity_id=args.entity_id,
        #     subject="location_fix", 
        #     source_id=args.source_id + "/binary",
        # )
        # logging.info(f"Created LocationFix publisher: {key_exp_pub_location_fix}")

        # # ECEF position publisher
        # key_exp_pub_ecef = keelson.construct_pubsub_key(
        #     base_path=args.realm,
        #     entity_id=args.entity_id,
        #     subject="ecef_position", 
        #     source_id=args.source_id + "/binary",
        # )
        # logging.info(f"Created ECEF publisher: {key_exp_pub_ecef}")

        # # Velocity NED publisher
        # key_exp_pub_velocity = keelson.construct_pubsub_key(
        #     base_path=args.realm,
        #     entity_id=args.entity_id,
        #     subject="velocity_ned", 
        #     source_id=args.source_id + "/binary",
        # )
        # logging.info(f"Created Velocity NED publisher: {key_exp_pub_velocity}")

        # # Acceleration body publisher
        # key_exp_pub_acceleration = keelson.construct_pubsub_key(
        #     base_path=args.realm,
        #     entity_id=args.entity_id,
        #     subject="acceleration_body", 
        #     source_id=args.source_id + "/binary",
        # )
        # logging.info(f"Created Acceleration Body publisher: {key_exp_pub_acceleration}")

        # # Attitude publisher
        # key_exp_pub_attitude = keelson.construct_pubsub_key(
        #     base_path=args.realm,
        #     entity_id=args.entity_id,
        #     subject="attitude", 
        #     source_id=args.source_id + "/binary",
        # )
        # logging.info(f"Created Attitude publisher: {key_exp_pub_attitude}")

        # # Result code publisher
        # key_exp_pub_result_code = keelson.construct_pubsub_key(
        #     base_path=args.realm,
        #     entity_id=args.entity_id,
        #     subject="result_code", 
        #     source_id=args.source_id + "/binary",
        # )
        # logging.info(f"Created Result Code publisher: {key_exp_pub_result_code}")

        # # GPS timing publisher
        # key_exp_pub_gps_timing = keelson.construct_pubsub_key(
        #     base_path=args.realm,
        #     entity_id=args.entity_id,
        #     subject="gps_timing", 
        #     source_id=args.source_id + "/binary",
        # )
        # logging.info(f"Created GPS Timing publisher: {key_exp_pub_gps_timing}")

        # # UTC timestamp publisher
        # key_exp_pub_utc_time = keelson.construct_pubsub_key(
        #     base_path=args.realm,
        #     entity_id=args.entity_id,
        #     subject="utc_time", 
        #     source_id=args.source_id + "/binary",
        # )
        # logging.info(f"Created UTC Time publisher: {key_exp_pub_utc_time}")

        #################################################
        # Setup input stream

        tcp_socket = None
        
        if args.input_mode == "tcp":
            tcp_socket = create_tcp_connection(args.anavs_host, args.anavs_port)
            if tcp_socket is None:
                logging.error("Failed to connect to ANavS device, exiting")
                sys.exit(1)
        else:
            logging.info("Reading from stdin")

        #################################################
        # Main processing loop

        binary_buffer = bytearray()
        
        try:
            while True:
                # Read data
                if args.input_mode == "tcp" and tcp_socket:
                    try:
                        chunk = tcp_socket.recv(4096)
                        if not chunk:
                            logging.warning("TCP connection closed by remote")
                            break
                    except socket.timeout:
                        continue
                    except Exception as e:
                        logging.error(f"TCP read error: {e}")
                        break
                else:
                    chunk = sys.stdin.buffer.read(4096)
                    if not chunk:
                        time.sleep(0.001)
                        continue
                
                ingress_timestamp = time.time_ns()
                
                # Add to binary buffer
                binary_buffer.extend(chunk)
                
                # Publish RAW message if requested
                if any(topic in args.publish for topic in ("raw", "all")):
                    payload = TimestampedBytes()
                    payload.timestamp.FromNanoseconds(ingress_timestamp)
                    payload.value = chunk
                    serialized_payload = payload.SerializeToString()
                    envelope = keelson.enclose(serialized_payload)
                    pub_raw.put(envelope)
                    logging.debug(f"Published RAW data on {key_exp_pub_raw}")
                
                # Try to parse ANavS binary messages
                try:
                    consumed, messages = parse_anavs_binary(binary_buffer)
                    if consumed > 0:
                        binary_buffer = binary_buffer[consumed:]
                        
                    for pos_data in messages:
                        logging.debug(f"Decoded position: lat={pos_data['lat']:.6f}, lon={pos_data['lon']:.6f}, height={pos_data['height']:.2f}")
                        logging.debug(f"Velocity NED: N={pos_data['velocity_ned'][0]:.3f}, E={pos_data['velocity_ned'][1]:.3f}, D={pos_data['velocity_ned'][2]:.3f} m/s")
                        logging.debug(f"Acceleration Body: X={pos_data['acceleration_body'][0]:.3f}, Y={pos_data['acceleration_body'][1]:.3f}, Z={pos_data['acceleration_body'][2]:.3f} m/s²")
                        logging.debug(f"Attitude: Heading={pos_data['attitude'][0]:.2f}°, Pitch={pos_data['attitude'][1]:.2f}°, Roll={pos_data['attitude'][2]:.2f}°")
                        logging.debug(f"UTC Time: {pos_data['utc_timestamp'].strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} UTC")
                        
                        message_timestamp = pos_data['timestamp']
                        utc_timestamp = pos_data['utc_timestamp']
                        
                        # Publish LocationFix
                        if any(topic in args.publish for topic in ("location_fix", "all")):
                            payload_location = LocationFix()
                            payload_location.timestamp.FromDatetime(message_timestamp)
                            payload_location.latitude = pos_data['lat']
                            payload_location.longitude = pos_data['lon']
                            payload_location.altitude = pos_data['height']
                            
                            serialized_payload = payload_location.SerializeToString()
                            envelope = keelson.enclose(serialized_payload)
                            key_exp_pub_location_fix = keelson.construct_pubsub_key(
                                base_path=args.realm,
                                entity_id=args.entity_id,
                                subject="location_fix", 
                                source_id=args.source_id + "/binary",
                            )
                            session.put(
                                key_expr=key_exp_pub_location_fix,
                                payload=envelope,
                                priority=zenoh.Priority.INTERACTIVE_HIGH,
                                congestion_control=zenoh.CongestionControl.DROP,
                            )
                            logging.debug(f"Published LocationFix on {key_exp_pub_location_fix}")

                        # Publish ECEF Position
                        if any(topic in args.publish for topic in ("ecef", "all")):
                            payload_ecef = TimestampedFloat()
                            payload_ecef.timestamp.FromDatetime(message_timestamp)
                            payload_ecef.value = pos_data['ecef_x']  # X component
                            
                            key_exp_pub_ecef_x = keelson.construct_pubsub_key(
                                base_path=args.realm,
                                entity_id=args.entity_id,
                                subject="ecef_x", 
                                source_id=args.source_id + "/binary",
                            )
                            serialized_payload = payload_ecef.SerializeToString()
                            envelope = keelson.enclose(serialized_payload)
                            session.put(
                                key_expr=key_exp_pub_ecef_x,
                                payload=envelope,
                                priority=zenoh.Priority.INTERACTIVE_HIGH,
                                congestion_control=zenoh.CongestionControl.DROP,
                            )
                            logging.debug(f"Published ECEF X on {key_exp_pub_ecef_x}")
                            
                            # Similar for Y and Z components
                            payload_ecef.value = pos_data['ecef_y']
                            key_exp_pub_ecef_y = keelson.construct_pubsub_key(
                                base_path=args.realm,
                                entity_id=args.entity_id,
                                subject="ecef_y", 
                                source_id=args.source_id + "/binary",
                            )
                            serialized_payload = payload_ecef.SerializeToString()
                            envelope = keelson.enclose(serialized_payload)
                            session.put(key_expr=key_exp_pub_ecef_y, payload=envelope,
                                        priority=zenoh.Priority.INTERACTIVE_HIGH,
                                        congestion_control=zenoh.CongestionControl.DROP)
                            
                            payload_ecef.value = pos_data['ecef_z']
                            key_exp_pub_ecef_z = keelson.construct_pubsub_key(
                                base_path=args.realm,
                                entity_id=args.entity_id,
                                subject="ecef_z", 
                                source_id=args.source_id + "/binary",
                            )
                            serialized_payload = payload_ecef.SerializeToString()
                            envelope = keelson.enclose(serialized_payload)
                            session.put(key_expr=key_exp_pub_ecef_z, payload=envelope,
                                        priority=zenoh.Priority.INTERACTIVE_HIGH,
                                        congestion_control=zenoh.CongestionControl.DROP)

                        # Publish Velocity NED
                        if any(topic in args.publish for topic in ("velocity", "all")):
                            for i, component in enumerate(['north', 'east', 'down']):
                                payload_vel = TimestampedFloat()
                                payload_vel.timestamp.FromDatetime(message_timestamp)
                                payload_vel.value = pos_data['velocity_ned'][i]
                                
                                key_exp_pub_vel = keelson.construct_pubsub_key(
                                    base_path=args.realm,
                                    entity_id=args.entity_id,
                                    subject=f"velocity_{component}", 
                                    source_id=args.source_id + "/binary",
                                )
                                serialized_payload = payload_vel.SerializeToString()
                                envelope = keelson.enclose(serialized_payload)
                                session.put(
                                    key_expr=key_exp_pub_vel,
                                    payload=envelope,
                                    priority=zenoh.Priority.INTERACTIVE_HIGH,
                                    congestion_control=zenoh.CongestionControl.DROP,
                                )
                                logging.debug(f"Published Velocity {component} on {key_exp_pub_vel}")

                        # Publish Acceleration Body Frame
                        if any(topic in args.publish for topic in ("acceleration", "all")):
                            for i, component in enumerate(['x', 'y', 'z']):
                                payload_acc = TimestampedFloat()
                                payload_acc.timestamp.FromDatetime(message_timestamp)
                                payload_acc.value = pos_data['acceleration_body'][i]
                                
                                key_exp_pub_acc = keelson.construct_pubsub_key(
                                    base_path=args.realm,
                                    entity_id=args.entity_id,
                                    subject=f"acceleration_{component}", 
                                    source_id=args.source_id + "/binary",
                                )
                                serialized_payload = payload_acc.SerializeToString()
                                envelope = keelson.enclose(serialized_payload)
                                session.put(
                                    key_expr=key_exp_pub_acc,
                                    payload=envelope,
                                    priority=zenoh.Priority.INTERACTIVE_HIGH,
                                    congestion_control=zenoh.CongestionControl.DROP,
                                )
                                logging.debug(f"Published Acceleration {component} on {key_exp_pub_acc}")

                        # Publish Attitude (Euler angles)
                        if any(topic in args.publish for topic in ("attitude", "all")):
                            attitude_components = ['heading', 'pitch', 'roll']
                            for i, component in enumerate(attitude_components):
                                payload_att = TimestampedFloat()
                                payload_att.timestamp.FromDatetime(message_timestamp)
                                payload_att.value = pos_data['attitude'][i]
                                
                                key_exp_pub_att = keelson.construct_pubsub_key(
                                    base_path=args.realm,
                                    entity_id=args.entity_id,
                                    subject=f"attitude_{component}", 
                                    source_id=args.source_id + "/binary",
                                )
                                serialized_payload = payload_att.SerializeToString()
                                envelope = keelson.enclose(serialized_payload)
                                session.put(
                                    key_expr=key_exp_pub_att,
                                    payload=envelope,
                                    priority=zenoh.Priority.INTERACTIVE_HIGH,
                                    congestion_control=zenoh.CongestionControl.DROP,
                                )
                                logging.debug(f"Published Attitude {component} on {key_exp_pub_att}")

                        # Publish UTC Timestamp
                        if any(topic in args.publish for topic in ("utc_time", "timing", "all")):
                            payload_utc = TimestampedTimestamp()
                            payload_utc.timestamp.FromDatetime(message_timestamp)
                            payload_utc.value.FromDatetime(utc_timestamp)
                            
                            key_exp_pub_utc = keelson.construct_pubsub_key(
                                base_path=args.realm,
                                entity_id=args.entity_id,
                                subject="utc_time", 
                                source_id=args.source_id + "/binary",
                            )
                            serialized_payload = payload_utc.SerializeToString()
                            envelope = keelson.enclose(serialized_payload)
                            session.put(
                                key_expr=key_exp_pub_utc,
                                payload=envelope,
                                priority=zenoh.Priority.INTERACTIVE_HIGH,
                                congestion_control=zenoh.CongestionControl.DROP,
                            )
                            logging.debug(f"Published UTC Time on {key_exp_pub_utc}")

                        # Publish Result Code
                        if any(topic in args.publish for topic in ("result_code", "status", "all")):
                            payload_result = TimestampedInt()
                            payload_result.timestamp.FromDatetime(message_timestamp)
                            payload_result.value = pos_data['res_code']
                            
                            key_exp_pub_result = keelson.construct_pubsub_key(
                                base_path=args.realm,
                                entity_id=args.entity_id,
                                subject="result_code", 
                                source_id=args.source_id + "/binary",
                            )
                            serialized_payload = payload_result.SerializeToString()
                            envelope = keelson.enclose(serialized_payload)
                            session.put(
                                key_expr=key_exp_pub_result,
                                payload=envelope,
                                priority=zenoh.Priority.INTERACTIVE_HIGH,
                                congestion_control=zenoh.CongestionControl.DROP,
                            )
                            logging.debug(f"Published Result Code on {key_exp_pub_result}")

                        # Publish GPS Timing
                        if any(topic in args.publish for topic in ("gps_timing", "timing", "all")):
                            payload_timing = TimestampedFloat()
                            payload_timing.timestamp.FromDatetime(message_timestamp)
                            payload_timing.value = pos_data['tow']
                            
                            key_exp_pub_timing = keelson.construct_pubsub_key(
                                base_path=args.realm,
                                entity_id=args.entity_id,
                                subject="gps_tow", 
                                source_id=args.source_id + "/binary",
                            )
                            serialized_payload = payload_timing.SerializeToString()
                            envelope = keelson.enclose(serialized_payload)
                            session.put(
                                key_expr=key_exp_pub_timing,
                                payload=envelope,
                                priority=zenoh.Priority.INTERACTIVE_HIGH,
                                congestion_control=zenoh.CongestionControl.DROP,
                            )
                            logging.debug(f"Published GPS TOW on {key_exp_pub_timing}")

                            # Also publish GPS week
                            payload_timing.value = pos_data['week']
                            key_exp_pub_week = keelson.construct_pubsub_key(
                                base_path=args.realm,
                                entity_id=args.entity_id,
                                subject="gps_week", 
                                source_id=args.source_id + "/binary",
                            )
                            serialized_payload = payload_timing.SerializeToString()
                            envelope = keelson.enclose(serialized_payload)
                            session.put(
                                key_expr=key_exp_pub_week,
                                payload=envelope,
                                priority=zenoh.Priority.INTERACTIVE_HIGH,
                                congestion_control=zenoh.CongestionControl.DROP,
                            )

                        
                  

     
     

         
                        
                except Exception as e:
                    logging.warning(f"Binary parsing error: {e}")
                    # Clear some buffer to prevent repeated errors
                    if len(binary_buffer) > 1000:
                        binary_buffer = binary_buffer[100:]
                
                # Prevent buffer from growing too large
                if len(binary_buffer) > 65536:
                    # Keep only the last portion
                    binary_buffer = binary_buffer[-32768:]
                    logging.warning("Binary buffer overflow, truncating")
                    
        except KeyboardInterrupt:
            logging.info("Interrupted by user")
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
        finally:
            if tcp_socket:
                tcp_socket.close()
                logging.info("TCP connection closed")

    logging.info("Zenoh session closed.")
    sys.exit(0)

if __name__ == "__main__":
    main()
