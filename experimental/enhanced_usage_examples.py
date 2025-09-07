#!/usr/bin/env python3
"""
Enhanced ANavS Keelson Connector - Usage Examples

This script demonstrates various usage patterns for the enhanced ANavS connector
that now supports velocity, acceleration, attitude, and UTC time publishing.
"""

import os

print("=== Enhanced ANavS Keelson Connector Usage Examples ===\n")

print("1. Connect to ANavS device and publish ALL data types:")
print("   python3 anavs_connector.py -e vessel_name --publish all")
print("   (Publishes: location_fix, velocity, acceleration, attitude, UTC time, ECEF, timing, etc.)\n")

print("2. Publish only position and velocity data:")
print("   python3 anavs_connector.py -e vessel_name --publish location_fix --publish velocity\n")

print("3. Publish only attitude (heading/pitch/roll) and acceleration:")
print("   python3 anavs_connector.py -e vessel_name --publish attitude --publish acceleration\n")

print("4. Read from stdin (via socat) and publish velocity + timing:")
print("   socat TCP:192.168.1.124:6001 STDOUT | python3 anavs_connector.py --input-mode stdin -e vessel_name --publish velocity --publish gps_timing\n")

print("5. Debug mode with all velocity and attitude data:")
print("   python3 anavs_connector.py -e vessel_name --publish velocity --publish attitude --log-level 10\n")

print("6. Custom ANavS device IP and publish UTC time:")
print("   python3 anavs_connector.py -e vessel_name --anavs-host 192.168.2.100 --publish utc_time --publish location_fix\n")

print("=== Available Publisher Topics ===")
topics = [
    ("all", "All available data types"),
    ("location_fix", "GPS position (lat/lon/alt) in Keelson LocationFix format"),
    ("velocity", "Velocity in NED frame (velocity_north/east/down)"),
    ("acceleration", "Acceleration in body frame (acceleration_x/y/z)"),
    ("attitude", "Euler angles (attitude_heading/pitch/roll) in degrees"),
    ("utc_time", "UTC timestamp from GPS time conversion"),
    ("ecef_position", "ECEF coordinates (ecef_x/y/z)"),
    ("gps_timing", "GPS timing (gps_week, gps_tow)"),
    ("result_code", "ANavS result/status code"),
    ("status", "Alias for result_code")
]

for topic, description in topics:
    print(f"  {topic:15} - {description}")

print(f"\n=== Data Coordinate Frames ===")
print(f"  Velocity:     NED frame (North-East-Down) in m/s")
print(f"  Acceleration: Body frame (X-Y-Z) in m/s²")
print(f"  Attitude:     Euler angles (Heading-Pitch-Roll) in degrees")
print(f"  Position:     WGS84 (lat/lon in degrees, altitude in meters)")
print(f"  ECEF:         Earth-Centered, Earth-Fixed (X-Y-Z) in meters")

print(f"\n=== Keelson Publisher Topics ===")
print(f"The following Zenoh/Keelson topics will be published:")
print(f"  rise/<entity_id>/location_fix/<source_id>/binary")
print(f"  rise/<entity_id>/velocity_north/<source_id>/binary")
print(f"  rise/<entity_id>/velocity_east/<source_id>/binary")
print(f"  rise/<entity_id>/velocity_down/<source_id>/binary")
print(f"  rise/<entity_id>/acceleration_x/<source_id>/binary")
print(f"  rise/<entity_id>/acceleration_y/<source_id>/binary")
print(f"  rise/<entity_id>/acceleration_z/<source_id>/binary")
print(f"  rise/<entity_id>/attitude_heading/<source_id>/binary")
print(f"  rise/<entity_id>/attitude_pitch/<source_id>/binary")
print(f"  rise/<entity_id>/attitude_roll/<source_id>/binary")
print(f"  rise/<entity_id>/utc_time/<source_id>/binary")
print(f"  rise/<entity_id>/ecef_x/<source_id>/binary")
print(f"  rise/<entity_id>/ecef_y/<source_id>/binary")
print(f"  rise/<entity_id>/ecef_z/<source_id>/binary")
print(f"  rise/<entity_id>/gps_week/<source_id>/binary")
print(f"  rise/<entity_id>/gps_tow/<source_id>/binary")
print(f"  rise/<entity_id>/result_code/<source_id>/binary")

print(f"\n=== Sample Output (Debug Mode) ===")
print(f"DEBUG:Decoded position: lat=57.698100, lon=11.974600, height=25.50")
print(f"DEBUG:Velocity NED: N=2.500, E=1.200, D=-0.100 m/s")
print(f"DEBUG:Acceleration Body: X=0.100, Y=-0.050, Z=9.810 m/s²")
print(f"DEBUG:Attitude: Heading=45.50°, Pitch=2.10°, Roll=-1.80°")
print(f"DEBUG:UTC Time: 2024-12-16 10:17:36.789 UTC")
print(f"DEBUG:Published LocationFix on rise/vessel_name/location_fix/anavs/0/binary")
print(f"DEBUG:Published Velocity north on rise/vessel_name/velocity_north/anavs/0/binary")
print(f"DEBUG:Published Attitude heading on rise/vessel_name/attitude_heading/anavs/0/binary")
