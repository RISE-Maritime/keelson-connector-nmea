#!/usr/bin/env python3
"""
Test script for enhanced ANavS connector with velocity, acceleration, attitude, and UTC time
"""

import struct
import io
import sys
import os

# Add the parent directory to sys.path to import our module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from anavs_connector import parse_anavs_binary, fletcher_checksum

def create_test_anavs_message():
    """Create a synthetic ANavS binary message for testing"""
    
    # ANavS Extended Message structure:
    # Header: sync (2 bytes) + class (1) + id (1) + length (2)
    # Payload: Basic data (79 bytes) + Extended data (velocity, acceleration, attitude, etc.)
    # Checksum: Fletcher-16 (2 bytes)
    
    # Header
    sync = b'\xB5\x62'  # UBX sync pattern
    msg_class = 0x02    # ANavS class
    msg_id = 0xE0       # Extended position message
    
    # Payload length (will be calculated)
    
    # Basic payload (79 bytes) - GPS timing and position
    week = 2345                    # GPS week
    tow = 123456.789               # Time of week (double)
    res_code = 0                   # Result code
    lat = 57.6981000               # Latitude in degrees (raw value)
    lon = 11.9746000               # Longitude in degrees (raw value)  
    height = 25.5                  # Height in meters
    ecef_x = 3370658.123           # ECEF X (meters)
    ecef_y = 711877.456            # ECEF Y (meters)
    ecef_z = 5349786.789           # ECEF Z (meters)
    hor_acc = 0.05                 # Horizontal accuracy (float)
    ver_acc = 0.08                 # Vertical accuracy (float)
    sat_used = 12                  # Satellites used
    
    # Extended payload data
    # Velocity in NED frame (3 * double)
    vel_north = 2.5   # m/s
    vel_east = 1.2    # m/s
    vel_down = -0.1   # m/s
    
    # Acceleration in body frame (3 * double)  
    acc_x = 0.1       # m/s²
    acc_y = -0.05     # m/s²
    acc_z = 9.81      # m/s²
    
    # Attitude - Euler angles (3 * double)
    heading = 45.5    # degrees
    pitch = 2.1       # degrees
    roll = -1.8       # degrees
    
    # Baseline data (3 * double)
    baseline_x = 1.234
    baseline_y = 2.345
    baseline_z = 3.456
    
    # Standard deviations (9 * float)
    std_pos_x = 0.01
    std_pos_y = 0.01
    std_pos_z = 0.02
    std_vel_x = 0.005
    std_vel_y = 0.005
    std_vel_z = 0.01
    std_att_x = 0.1
    std_att_y = 0.1
    std_att_z = 0.1
    
    # Pack basic payload according to ANavS binary format
    payload = struct.pack('<BH',     # id(1) + resCode(2) 
        msg_id, res_code
    )
    payload += struct.pack('<H',     # week(2)
        week
    )
    payload += struct.pack('<d',     # tow(8)
        tow
    )
    payload += struct.pack('<H',     # weekInit(2)
        week
    )
    payload += struct.pack('<d',     # towInit(8)
        tow
    )
    payload += struct.pack('<h',     # reserved(2)
        0
    )
    payload += struct.pack('<ddd',   # lat(8) + lon(8) + height(8)
        lat, lon, height
    )
    payload += struct.pack('<ddd',   # ECEF X(8) + Y(8) + Z(8)
        ecef_x, ecef_y, ecef_z
    )
    
    # Baseline data (3 * double)
    payload += struct.pack('<ddd',
        baseline_x, baseline_y, baseline_z
    )
    
    # Baseline standard deviations (3 * double)
    payload += struct.pack('<ddd',
        0.01, 0.01, 0.02
    )
    
    # Velocity in NED frame (3 * double)
    payload += struct.pack('<ddd',
        vel_north, vel_east, vel_down
    )
    
    # Velocity standard deviations (3 * double)
    payload += struct.pack('<ddd',
        std_vel_x, std_vel_y, std_vel_z
    )
    
    # Acceleration in body frame (3 * double)  
    payload += struct.pack('<ddd',
        acc_x, acc_y, acc_z
    )
    
    # Acceleration standard deviations (3 * double)
    payload += struct.pack('<ddd',
        0.005, 0.005, 0.01
    )
    
    # Attitude - Euler angles (3 * double)
    payload += struct.pack('<ddd',
        heading, pitch, roll
    )
    
    # Attitude standard deviations (3 * double)
    payload += struct.pack('<ddd',
        std_att_x, std_att_y, std_att_z
    )
    
    # Calculate payload length
    payload_length = len(payload)
    
    # Create complete message without checksum
    message_without_checksum = sync + struct.pack('<BBH', msg_class, msg_id, payload_length) + payload
    
    # Calculate Fletcher-16 checksum (skip sync bytes)
    checksum_data = message_without_checksum[2:]  # Skip sync bytes for checksum
    ck_a, ck_b = fletcher_checksum(checksum_data)
    checksum = (ck_b << 8) | ck_a
    
    # Complete message
    complete_message = message_without_checksum + struct.pack('<H', checksum)
    
    print(f"Created test message:")
    print(f"  Payload length: {payload_length} bytes")
    print(f"  Total message length: {len(complete_message)} bytes")
    print(f"  Checksum: 0x{checksum:04X}")
    
    return complete_message, {
        'week': week,
        'tow': tow,
        'lat': lat,  # Already in degrees
        'lon': lon,  # Already in degrees
        'height': height,
        'vel_north': vel_north,
        'vel_east': vel_east,
        'vel_down': vel_down,
        'acc_x': acc_x,
        'acc_y': acc_y,
        'acc_z': acc_z,
        'heading': heading,
        'pitch': pitch,
        'roll': roll
    }

def test_enhanced_parsing():
    """Test the enhanced ANavS parsing functionality"""
    
    print("=== Enhanced ANavS Connector Test ===")
    
    # Create test message
    test_message, expected = create_test_anavs_message()
    
    # Parse the message
    try:
        consumed, parsed_messages = parse_anavs_binary(test_message)
        
        if not parsed_messages:
            print("ERROR: No messages parsed!")
            return False
            
        parsed = parsed_messages[0]
        
        print(f"\n=== Parsing Results ===")
        print(f"GPS Week: {parsed['week']} (expected: {expected['week']})")
        print(f"GPS TOW: {parsed['tow']:.3f} (expected: {expected['tow']:.3f})")
        print(f"Latitude: {parsed['lat']:.6f}° (expected: {expected['lat']:.6f}°)")
        print(f"Longitude: {parsed['lon']:.6f}° (expected: {expected['lon']:.6f}°)")
        print(f"Height: {parsed['height']:.2f}m (expected: {expected['height']:.2f}m)")
        
        print(f"\n=== Velocity (NED Frame) ===")
        print(f"North: {parsed['velocity_ned'][0]:.3f} m/s (expected: {expected['vel_north']:.3f})")
        print(f"East:  {parsed['velocity_ned'][1]:.3f} m/s (expected: {expected['vel_east']:.3f})")
        print(f"Down:  {parsed['velocity_ned'][2]:.3f} m/s (expected: {expected['vel_down']:.3f})")
        
        print(f"\n=== Acceleration (Body Frame) ===")
        print(f"X: {parsed['acceleration_body'][0]:.3f} m/s² (expected: {expected['acc_x']:.3f})")
        print(f"Y: {parsed['acceleration_body'][1]:.3f} m/s² (expected: {expected['acc_y']:.3f})")
        print(f"Z: {parsed['acceleration_body'][2]:.3f} m/s² (expected: {expected['acc_z']:.3f})")
        
        print(f"\n=== Attitude (Euler Angles) ===")
        print(f"Heading: {parsed['attitude'][0]:.2f}° (expected: {expected['heading']:.2f}°)")
        print(f"Pitch:   {parsed['attitude'][1]:.2f}° (expected: {expected['pitch']:.2f}°)")
        print(f"Roll:    {parsed['attitude'][2]:.2f}° (expected: {expected['roll']:.2f}°)")
        
        print(f"\n=== UTC Timestamp ===")
        utc_time = parsed['utc_timestamp']
        print(f"UTC Time: {utc_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} UTC")
        
        # Validate key values
        tolerance = 1e-6
        success = True
        
        if abs(parsed['lat'] - expected['lat']) > tolerance:
            print(f"ERROR: Latitude mismatch!")
            success = False
            
        if abs(parsed['lon'] - expected['lon']) > tolerance:
            print(f"ERROR: Longitude mismatch!")
            success = False
            
        if abs(parsed['velocity_ned'][0] - expected['vel_north']) > tolerance:
            print(f"ERROR: Velocity North mismatch!")
            success = False
            
        if abs(parsed['acceleration_body'][0] - expected['acc_x']) > tolerance:
            print(f"ERROR: Acceleration X mismatch!")
            success = False
            
        if abs(parsed['attitude'][0] - expected['heading']) > tolerance:
            print(f"ERROR: Heading mismatch!")
            success = False
        
        if success:
            print(f"\n✅ All validations passed!")
            return True
        else:
            print(f"\n❌ Some validations failed!")
            return False
            
    except Exception as e:
        print(f"ERROR: Failed to parse message: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_enhanced_parsing()
    exit(0 if success else 1)
