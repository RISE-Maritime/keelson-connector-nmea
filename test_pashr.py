#!/usr/bin/env python3

"""
Simple test script to verify PASHR parsing functionality
"""

import pynmea2
from datetime import datetime
import pytz

def test_pashr_parsing():
    """Test PASHR message parsing"""
    
    # Example PASHR message
    test_message = "$PASHR,104534.00,45.2,T,-2.5,3.8,0.5,0.1,0.1,0.2,1,0*33"
    
    print("Testing PASHR parsing...")
    print(f"Input message: {test_message}")
    
    try:
        # Parse the message
        parsed = pynmea2.parse(test_message)
        
        print(f"Parsed successfully: {type(parsed)}")
        print(f"Timestamp: {parsed.timestamp}")
        print(f"True heading: {parsed.true_heading}")
        print(f"Is true heading: {parsed.is_true_heading}")
        print(f"Roll: {parsed.roll}")
        print(f"Pitch: {parsed.pitch}")
        print(f"Heave: {parsed.heave}")
        print(f"Roll accuracy: {parsed.roll_accuracy}")
        print(f"Pitch accuracy: {parsed.pitch_accuracy}")
        print(f"Heading accuracy: {parsed.heading_accuracy}")
        print(f"Aiding status: {parsed.aiding_status}")
        print(f"IMU status: {parsed.imu_status}")
        
        # Test timestamp conversion
        if parsed.timestamp is not None:
            nmea_msg_timestamp_dt = datetime.combine(datetime.today(), parsed.timestamp, tzinfo=pytz.utc)
            print(f"Combined timestamp: {nmea_msg_timestamp_dt}")
        
        # Test heading type detection
        heading_type = "true" if parsed.is_true_heading == "T" else "magnetic"
        print(f"Heading type: {heading_type}")
        
        print("✓ PASHR parsing test passed!")
        return True
        
    except Exception as e:
        print(f"✗ PASHR parsing test failed: {e}")
        return False

if __name__ == "__main__":
    test_pashr_parsing()
