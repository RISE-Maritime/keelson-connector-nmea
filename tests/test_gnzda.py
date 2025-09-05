#!/usr/bin/env python3

"""
Simple test script to verify GNZDA parsing functionality
"""

import pynmea2
from datetime import datetime
import pytz

def test_gnzda_parsing():
    """Test GNZDA message parsing"""
    
    # Example GNZDA message
    test_message = "$GNZDA,104534.00,05,09,2025,00,00*76"
    
    print("Testing GNZDA parsing...")
    print(f"Input message: {test_message}")
    
    try:
        # Parse the message
        parsed = pynmea2.parse(test_message)
        
        print(f"Parsed successfully: {type(parsed)}")
        print(f"Timestamp: {parsed.timestamp}")
        print(f"Day: {parsed.day}")
        print(f"Month: {parsed.month}")
        print(f"Year: {parsed.year}")
        print(f"Local zone: {parsed.local_zone}")
        print(f"Local zone minutes: {parsed.local_zone_minutes}")
        
        # Test full datetime construction
        if all([parsed.day, parsed.month, parsed.year, parsed.timestamp]):
            full_datetime = datetime.combine(
                datetime(int(parsed.year), int(parsed.month), int(parsed.day)),
                parsed.timestamp,
                tzinfo=pytz.utc
            )
            print(f"Combined datetime: {full_datetime}")
            print(f"ISO format: {full_datetime.isoformat()}")
            
            # Test time formatting
            time_str = parsed.timestamp.strftime("%H:%M:%S.%f")[:-3]
            print(f"Time string: {time_str}")
            
            # Test date formatting
            date_str = f"{parsed.year}-{parsed.month:02d}-{parsed.day:02d}"
            print(f"Date string: {date_str}")
        
        print("✓ GNZDA parsing test passed!")
        return True
        
    except Exception as e:
        print(f"✗ GNZDA parsing test failed: {e}")
        return False

if __name__ == "__main__":
    test_gnzda_parsing()
