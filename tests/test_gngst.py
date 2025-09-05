#!/usr/bin/env python3

"""
Simple test script to verify GNGST parsing functionality
"""

import pynmea2
from datetime import datetime
import pytz

def test_gngst_parsing():
    """Test GNGST message parsing"""
    
    # Example GNGST message
    test_message = "$GNGST,104534.00,1.6,1.4,3.2,15.0,2.1,5.8,4.6*75"
    
    print("Testing GNGST parsing...")
    print(f"Input message: {test_message}")
    
    try:
        # Parse the message
        parsed = pynmea2.parse(test_message)
        
        print(f"Parsed successfully: {type(parsed)}")
        print(f"Timestamp: {parsed.timestamp}")
        print(f"RMS: {parsed.rms}")
        print(f"Semi-major axis std dev: {parsed.std_dev_major}")
        print(f"Semi-minor axis std dev: {parsed.std_dev_minor}")
        print(f"Orientation: {parsed.orientation}")
        print(f"Latitude std dev: {parsed.std_dev_latitude}")
        print(f"Longitude std dev: {parsed.std_dev_longitude}")
        print(f"Altitude std dev: {parsed.std_dev_altitude}")
        
        # Test timestamp conversion
        if parsed.timestamp is not None:
            nmea_msg_timestamp_dt = datetime.combine(datetime.today(), parsed.timestamp, tzinfo=pytz.utc)
            print(f"Combined timestamp: {nmea_msg_timestamp_dt}")
        
        print("✓ GNGST parsing test passed!")
        return True
        
    except Exception as e:
        print(f"✗ GNGST parsing test failed: {e}")
        return False

if __name__ == "__main__":
    test_gngst_parsing()
