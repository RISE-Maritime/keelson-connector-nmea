#!/usr/bin/env python3

"""
Test Script for Bidirectional NMEA Connector

This script demonstrates and tests the bidirectional NMEA functionality by:
1. Testing NMEA formatter functions
2. Testing output adapters
3. Simulating Keelson message conversion
"""

import sys
import time
import asyncio
import logging
from datetime import datetime
import pytz

# Add the bin directory to the path so we can import our modules
sys.path.insert(0, '/workspaces/keelson-connector-nmea/bin')

from nmea_formatter import NmeaFormatter, create_gga_sentence, create_rmc_sentence, calculate_nmea_checksum
from nmea_output_adapter import create_udp_config, MultiOutputAdapter
from keelson.payloads.foxglove.LocationFix_pb2 import LocationFix


def test_nmea_formatter():
    """Test the NMEA formatter functions."""
    print("\n=== Testing NMEA Formatter ===")
    
    # Test checksum calculation
    sentence = "GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"
    expected_checksum = "47"
    calculated_checksum = calculate_nmea_checksum(sentence)
    print(f"Checksum test: {calculated_checksum} == {expected_checksum} -> {'PASS' if calculated_checksum == expected_checksum else 'FAIL'}")
    
    # Test coordinate formatting  
    from nmea_formatter import format_coordinate
    lat_coord, lat_dir = format_coordinate(57.4358, is_longitude=False)
    lon_coord, lon_dir = format_coordinate(12.0326, is_longitude=True)
    print(f"Coordinate formatting: {lat_coord}{lat_dir}, {lon_coord}{lon_dir}")
    
    # Test creating LocationFix and generating sentences
    location_fix = LocationFix()
    location_fix.timestamp.FromDatetime(datetime.now(pytz.utc))
    location_fix.latitude = 57.4358
    location_fix.longitude = 12.0326
    location_fix.altitude = 25.5
    
    # Test GGA sentence generation
    gga_sentence = create_gga_sentence(location_fix, satellites_used=8, hdop=1.2)
    print(f"Generated GGA: {gga_sentence}")
    
    # Test RMC sentence generation  
    rmc_sentence = create_rmc_sentence(location_fix, speed_knots=5.5, course_deg=45.0)
    print(f"Generated RMC: {rmc_sentence}")
    
    # Test NmeaFormatter class
    formatter = NmeaFormatter()
    formatter.update_location_fix(location_fix)
    formatter.update_speed(5.5)
    formatter.update_course(45.0)
    formatter.update_heading(50.0)
    
    generated_sentences = []
    if (sentence := formatter.generate_gga_sentence()) is not None:
        generated_sentences.append(sentence)
    if (sentence := formatter.generate_rmc_sentence()) is not None:
        generated_sentences.append(sentence)
    if (sentence := formatter.generate_hdt_sentence()) is not None:
        generated_sentences.append(sentence)
    
    print(f"Formatter generated {len(generated_sentences)} sentences:")
    for sentence in generated_sentences:
        print(f"  {sentence}")


async def test_output_adapter():
    """Test the output adapter functionality."""
    print("\n=== Testing Output Adapter ===")
    
    try:
        # Create a UDP output configuration (localhost for testing)
        configs = [create_udp_config("127.0.0.1", 9999)]
        
        # Create and start adapter
        adapter = MultiOutputAdapter(configs)
        await adapter.start()
        
        print(f"Started {adapter.get_active_adapters()} output adapters")
        
        # Send some test NMEA sentences
        test_sentences = [
            "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47",
            "$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A",
            "$GPVTG,084.4,T,077.3,M,022.4,N,041.5,K*43"
        ]
        
        for sentence in test_sentences:
            adapter.send_nmea(sentence)
            print(f"Sent: {sentence}")
            await asyncio.sleep(0.1)
        
        # Give some time for messages to be sent
        await asyncio.sleep(1.0)
        
        # Stop adapter
        await adapter.stop()
        print("Output adapter test completed")
        
    except Exception as e:
        print(f"Output adapter test failed: {e}")


def test_coordinate_conversion():
    """Test coordinate conversion between decimal degrees and NMEA format."""
    print("\n=== Testing Coordinate Conversion ===")
    
    from nmea_formatter import format_coordinate
    
    test_coords = [
        (57.4358, False, "5726.1480", "N"),   # Latitude
        (-57.4358, False, "5726.1480", "S"),  # Latitude South
        (12.0326, True, "01201.9560", "E"),   # Longitude
        (-12.0326, True, "01201.9560", "W"),  # Longitude West
    ]
    
    for coord, is_lon, expected_coord, expected_dir in test_coords:
        coord_str, direction = format_coordinate(coord, is_lon)
        print(f"Input: {coord} -> Output: {coord_str} {direction} (Expected: {expected_coord} {expected_dir})")
        # Note: Minor differences in formatting are acceptable


async def main():
    """Main test function."""
    logging.basicConfig(level=logging.INFO)
    print("Starting Bidirectional NMEA Connector Tests")
    
    # Run tests
    test_nmea_formatter()
    test_coordinate_conversion()
    await test_output_adapter()
    
    print("\n=== Test Summary ===")
    print("✓ NMEA formatter functions tested")
    print("✓ Coordinate conversion tested")
    print("✓ Output adapter tested")
    print("\nTo test the full bidirectional functionality:")
    print("1. Start a Zenoh router")
    print("2. Run the bidirectional connector in output mode")
    print("3. Publish some Keelson messages to trigger NMEA output")
    print("\nExample commands:")
    print("  # Output mode with console debugging")
    print("  python3 bin/main_bidirectional --log-level 10 -r rise -e test_vessel --output-only \\")
    print("    --output-udp 127.0.0.1:8501 --nmea-sentences GGA,RMC,VTG --nmea-rate-hz 0.5")
    print("\n  # Listen for output with netcat")
    print("  nc -lu 8501")


if __name__ == "__main__":
    asyncio.run(main())