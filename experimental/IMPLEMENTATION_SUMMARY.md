# Enhanced ANavS Keelson Connector - Implementation Summary

## Overview
Successfully implemented an enhanced ANavS binary protocol connector with comprehensive sensor data extraction and Keelson/Zenoh publishing capabilities.

## Key Features Implemented

### 1. Binary Protocol Parsing
- **Complete ANavS Binary Protocol Support**: UBX-style sync pattern (0xB5 0x62), Class 0x02, Message ID 0xE0
- **Fletcher-16 Checksum Validation**: Ensures data integrity
- **Extended Payload Support**: Handles 265+ byte payloads with full sensor suite data
- **Robust Buffer Management**: Handles partial messages and sync recovery

### 2. Enhanced Data Extraction
- **Position Data**: Latitude, longitude, altitude (WGS84)
- **Velocity**: 3-axis velocity in NED frame (North-East-Down) in m/s
- **Acceleration**: 3-axis acceleration in body frame in m/s²
- **Attitude**: Euler angles (heading, pitch, roll) in degrees
- **ECEF Coordinates**: Earth-Centered, Earth-Fixed position
- **GPS Timing**: GPS week and time-of-week with UTC conversion
- **Baseline Data**: NED frame baseline measurements
- **Standard Deviations**: Quality metrics for all measurements

### 3. UTC Time Conversion
- **GPS to UTC Conversion**: Converts GPS week/TOW to UTC datetime
- **Timezone Handling**: Proper UTC timezone assignment using pytz
- **High Precision**: Maintains sub-second precision for timestamps

### 4. Keelson Publishing Architecture
- **Multiple Publisher Topics**: 17 different data streams
- **Selective Publishing**: Choose specific data types via command line
- **Proper Message Formats**: Uses Keelson protobuf payloads
- **High Priority Publishing**: INTERACTIVE_HIGH priority with DROP congestion control

## Published Topics

### Core Navigation Data
- `location_fix` - GPS position in Keelson LocationFix format
- `velocity_north/east/down` - Velocity components in NED frame
- `acceleration_x/y/z` - Acceleration in body frame
- `attitude_heading/pitch/roll` - Euler angles

### Timing and Coordinates
- `utc_time` - UTC timestamp from GPS conversion
- `ecef_x/y/z` - ECEF coordinate components
- `gps_week/gps_tow` - Raw GPS timing data

### Status and Quality
- `result_code` - ANavS processing result code

## Coordinate Frame Specifications

### Velocity (NED Frame)
- **North**: Positive towards true north
- **East**: Positive towards east
- **Down**: Positive downward (negative for altitude gain)
- **Units**: meters per second (m/s)

### Acceleration (Body Frame)
- **X**: Forward acceleration in vehicle body frame
- **Y**: Right acceleration in vehicle body frame  
- **Z**: Downward acceleration in vehicle body frame (includes gravity)
- **Units**: meters per second squared (m/s²)

### Attitude (Euler Angles)
- **Heading**: Yaw angle from north (0-360°)
- **Pitch**: Nose up/down angle (-90 to +90°)
- **Roll**: Bank angle (-180 to +180°)
- **Units**: degrees

## Usage Examples

### Connect to ANavS Device (All Data)
```bash
python3 anavs_connector.py -e vessel_name --publish all
```

### Selective Data Publishing
```bash
# Position and velocity only
python3 anavs_connector.py -e vessel_name --publish location_fix --publish velocity

# Attitude and acceleration for vehicle dynamics
python3 anavs_connector.py -e vessel_name --publish attitude --publish acceleration

# UTC timing for time synchronization
python3 anavs_connector.py -e vessel_name --publish utc_time --publish gps_timing
```

### Read from Data Stream
```bash
# Via socat from ANavS device
socat TCP:192.168.1.124:6001 STDOUT | python3 anavs_connector.py --input-mode stdin -e vessel_name
```

### Debug Mode
```bash
python3 anavs_connector.py -e vessel_name --log-level 10 --publish all
```

## Technical Validation

### Test Results
- ✅ Binary protocol parsing with synthetic data
- ✅ Velocity extraction (NED frame): N=2.5, E=1.2, D=-0.1 m/s
- ✅ Acceleration extraction (body frame): X=0.1, Y=-0.05, Z=9.81 m/s²
- ✅ Attitude extraction: Heading=45.5°, Pitch=2.1°, Roll=-1.8°
- ✅ UTC time conversion: GPS week/TOW → UTC datetime
- ✅ Fletcher-16 checksum validation
- ✅ Complete payload structure (265 bytes)

### Data Flow Verification
```
ANavS Device → Binary Protocol → Enhanced Parser → Multiple Publishers → Keelson/Zenoh
```

## File Structure
```
/experimental/
├── anavs_connector.py           # Main enhanced connector
├── terminal_inputs.py           # Command line argument handling
├── test_enhanced_anavs.py       # Validation test suite
├── enhanced_usage_examples.py   # Usage documentation
└── can-anavs-msg.py            # Original position decoder
```

## Dependencies
- **Zenoh**: Message broker communication
- **Keelson**: Maritime data framework with protobuf payloads
- **pytz**: Timezone handling for UTC conversion
- **struct**: Binary data parsing
- **Virtual Environment**: Isolated Python environment with all dependencies

## Performance Characteristics
- **Real-time Processing**: Handles continuous data streams
- **Low Latency**: High priority publishing with DROP congestion control
- **Robust Recovery**: Sync pattern recovery on data corruption
- **Memory Efficient**: Buffer management with controlled memory usage

## Integration Notes
- **Compatible with existing NMEA parser architecture**: Similar structure to main.py
- **Modular publisher selection**: Granular control over published data types
- **Extensible design**: Easy to add new data types or coordinate frames
- **Production ready**: Error handling, logging, and validation included

## Success Metrics
- **Complete ANavS Protocol Support**: All specified binary message fields extracted
- **Enhanced Data Extraction**: 4 new data categories (velocity, acceleration, attitude, UTC time)
- **Flexible Publishing**: 17 distinct publisher topics with selective publishing
- **Validated Implementation**: Test suite confirms correct parsing and coordinate frames
- **Production Architecture**: Robust error handling and monitoring capabilities

This enhanced connector provides comprehensive access to ANavS sensor fusion data, enabling advanced maritime applications requiring high-precision navigation, attitude, and kinematics information.
