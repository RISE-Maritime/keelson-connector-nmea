# Keelson NMEA0183 Connector

Bidirectional connectors between NMEA0183 sentences and the Keelson/Zenoh maritime data protocol.

## Overview

This repository provides two command-line utilities for converting between NMEA0183 maritime data format and the Keelson protocol on a Zenoh messaging bus:

- **`nmea01832keelson`** - Reads NMEA0183 sentences from STDIN and publishes structured data to Keelson/Zenoh
- **`keelson2nmea0183`** - Subscribes to Keelson/Zenoh subjects and outputs NMEA0183 sentences to STDOUT

These tools enable integration between legacy NMEA0183-based systems (GPS receivers, chart plotters, autopilots) and modern Zenoh-based maritime platforms.

## Supported NMEA0183 Sentence Types

Both connectors support the following 8 essential NMEA sentence types:

| Type | Description | Keelson Subjects |
|------|-------------|------------------|
| **GGA** | Global Positioning System Fix Data | `location_fix`, `location_fix_satellites_used`, `location_fix_hdop`, `location_fix_undulation_m` |
| **RMC** | Recommended Minimum Specific GNSS Data | `location_fix`, `speed_over_ground_knots`, `course_over_ground_deg` |
| **HDT** | Heading True | `heading_true_north_deg` |
| **VTG** | Track Made Good and Ground Speed | `course_over_ground_deg`, `speed_over_ground_knots` |
| **ZDA** | Date and Time | `timestamp` |
| **GLL** | Geographic Position Latitude/Longitude | `location_fix` |
| **ROT** | Rate of Turn | `yaw_rate_degps` |
| **GSA** | GNSS DOP and Active Satellites | `location_fix_hdop`, `location_fix_vdop`, `location_fix_pdop` |

## Installation

### Prerequisites

- Python 3.8 or later
- Access to a Zenoh router (optional for peer-to-peer mode)

### Install Dependencies

```bash
pip install -r requirements.txt
```

The key dependencies are:
- `eclipse-zenoh` - Zenoh messaging library
- `keelson` - Keelson protocol implementation
- `pynmea2` - NMEA0183 parsing and generation
- `skarv` - In-memory data vault for state management

## Usage

### NMEA → Keelson (`nmea01832keelson`)

Reads NMEA0183 sentences from standard input and publishes to Keelson/Zenoh.

#### Basic Usage

```bash
# Read from GPS device
cat /dev/ttyUSB0 | nmea01832keelson -r "vessel/sv_colibri" -e "sensors" -s "gps/primary"

# Read from file
nmea01832keelson -r "vessel/sv_colibri" -e "sensors" -s "gps/primary" < nmea_log.txt

# Pipe from another program
gpsd_client | nmea01832keelson -r "vessel/sv_colibri" -e "sensors" -s "gps/primary"
```

#### Command-Line Options

```
Required Arguments:
  -r, --realm REALM              Keelson realm (e.g., "vessel/sv_colibri")
  -e, --entity-id ENTITY_ID      Entity identifier (e.g., "sensors")
  -s, --source-id SOURCE_ID      Source identifier (e.g., "gps/primary")

Optional Arguments:
  --log-level LEVEL              Log level: 10=DEBUG, 20=INFO, 30=WARNING, 40=ERROR (default: 20)
  --mode {peer,client}           Zenoh session mode (default: peer)
  --connect ENDPOINT             Zenoh router endpoint (can be used multiple times)
  --publish-raw                  Also publish raw NMEA to 'raw' subject
```

#### Examples

**Connect to a Zenoh router:**
```bash
cat /dev/ttyUSB0 | nmea01832keelson \
  -r "vessel/sv_colibri" \
  -e "sensors" \
  -s "gps/primary" \
  --mode client \
  --connect "tcp/192.168.1.100:7447"
```

**Enable debug logging:**
```bash
cat /dev/ttyUSB0 | nmea01832keelson \
  -r "vessel/sv_colibri" \
  -e "sensors" \
  -s "gps/primary" \
  --log-level 10
```

**Also publish raw NMEA sentences:**
```bash
cat /dev/ttyUSB0 | nmea01832keelson \
  -r "vessel/sv_colibri" \
  -e "sensors" \
  -s "gps/primary" \
  --publish-raw
```

### Keelson → NMEA (`keelson2nmea0183`)

Subscribes to Keelson/Zenoh subjects and outputs NMEA0183 sentences to standard output.

#### Basic Usage

```bash
# Output to terminal
keelson2nmea0183 -r "vessel/sv_colibri" -e "sensors"

# Output to serial device
keelson2nmea0183 -r "vessel/sv_colibri" -e "sensors" > /dev/ttyUSB1

# Output to file
keelson2nmea0183 -r "vessel/sv_colibri" -e "sensors" > nmea_output.log

# Pipe to another program
keelson2nmea0183 -r "vessel/sv_colibri" -e "sensors" | opencpn_input
```

#### Command-Line Options

```
Required Arguments:
  -r, --realm REALM              Keelson realm (e.g., "vessel/sv_colibri")
  -e, --entity-id ENTITY_ID      Entity identifier (e.g., "sensors")

Optional Arguments:
  --log-level LEVEL              Log level: 10=DEBUG, 20=INFO, 30=WARNING, 40=ERROR (default: 20)
  --mode {peer,client}           Zenoh session mode (default: peer)
  --connect ENDPOINT             Zenoh router endpoint (can be used multiple times)
  --talker-id ID                 NMEA talker ID (default: "GP")
  --source_id_SUBJECT PATTERN    Source pattern for specific subject (default: "**")
```

#### Examples

**Change NMEA talker ID:**
```bash
keelson2nmea0183 \
  -r "vessel/sv_colibri" \
  -e "sensors" \
  --talker-id "GN"
```

**Connect to specific Zenoh router:**
```bash
keelson2nmea0183 \
  -r "vessel/sv_colibri" \
  -e "sensors" \
  --mode client \
  --connect "tcp/192.168.1.100:7447"
```

**Filter by specific GPS source:**
```bash
keelson2nmea0183 \
  -r "vessel/sv_colibri" \
  -e "sensors" \
  --source_id_location_fix "gps/primary" \
  --source_id_speed_over_ground_knots "gps/primary"
```

**Subscribe to multiple sources using wildcards:**
```bash
keelson2nmea0183 \
  -r "vessel/sv_colibri" \
  -e "sensors" \
  --source_id_location_fix "gps/**"
```

## Keelson Subject Mapping

### NMEA → Keelson Mappings

#### GGA (Position Fix)
```
NMEA Field                → Keelson Subject (Type)
---------------------------------------------------
Latitude, Longitude       → location_fix (LocationFix)
Altitude                  → location_fix.altitude (LocationFix)
Number of satellites      → location_fix_satellites_used (TimestampedInt)
HDOP                      → location_fix_hdop (TimestampedFloat)
Geoid separation          → location_fix_undulation_m (TimestampedFloat)
```

#### RMC (Recommended Minimum)
```
NMEA Field                → Keelson Subject (Type)
---------------------------------------------------
Latitude, Longitude       → location_fix (LocationFix)
Speed over ground         → speed_over_ground_knots (TimestampedFloat)
True course               → course_over_ground_deg (TimestampedFloat)
```

#### HDT (Heading True)
```
NMEA Field                → Keelson Subject (Type)
---------------------------------------------------
True heading              → heading_true_north_deg (TimestampedFloat)
```

#### VTG (Track Made Good)
```
NMEA Field                → Keelson Subject (Type)
---------------------------------------------------
True track                → course_over_ground_deg (TimestampedFloat)
Speed in knots            → speed_over_ground_knots (TimestampedFloat)
```

#### ZDA (Time and Date)
```
NMEA Field                → Keelson Subject (Type)
---------------------------------------------------
UTC date/time             → timestamp (TimestampedTimestamp)
```

#### GLL (Geographic Position)
```
NMEA Field                → Keelson Subject (Type)
---------------------------------------------------
Latitude, Longitude       → location_fix (LocationFix)
```

#### ROT (Rate of Turn)
```
NMEA Field                → Keelson Subject (Type)
---------------------------------------------------
Rate of turn (deg/min)    → yaw_rate_degps (TimestampedFloat, converted to deg/sec)
```

#### GSA (DOP and Active Satellites)
```
NMEA Field                → Keelson Subject (Type)
---------------------------------------------------
HDOP                      → location_fix_hdop (TimestampedFloat)
VDOP                      → location_fix_vdop (TimestampedFloat)
PDOP                      → location_fix_pdop (TimestampedFloat)
```

### Unit Conversions

The connectors automatically handle unit conversions:

- **ROT**: NMEA uses degrees/minute, Keelson uses degrees/second
  - NMEA → Keelson: divide by 60
  - Keelson → NMEA: multiply by 60

- **VTG**: Converts knots to km/h for NMEA output
  - 1 knot = 1.852 km/h

## Architecture

### nmea01832keelson Architecture

```
STDIN → Parse (pynmea2) → Handler Functions → Keelson Envelope → Zenoh Publish
```

- **Functional design** with handler registry pattern
- **Lazy publisher caching** to minimize Zenoh overhead
- **Timestamped messages** using NMEA timestamps when available
- **Defensive parsing** with graceful error handling

### keelson2nmea0183 Architecture

```
Zenoh Subscribe → skarv Vault → Event Triggers → Generate NMEA (pynmea2) → STDOUT
```

- **Event-driven generation** using `@skarv.subscribe()` decorators
- **State aggregation** with skarv in-memory vault
- **Automatic checksum** calculation via pynmea2
- **Wildcard subscriptions** for flexible source matching

## Development

### Project Structure

```
keelson-connector-nmea/
├── bin/
│   ├── nmea01832keelson       # NMEA → Keelson script
│   ├── keelson2nmea0183        # Keelson → NMEA script
│   └── utils.py                # Shared helper functions
├── legacy/                     # Previous implementation (deprecated)
├── requirements.txt            # Python dependencies
├── requirements_dev.txt        # Development dependencies
└── README.md                   # This file
```

### Key Design Patterns

Following the [keelson-connector-ais](https://github.com/RISE-Maritime/keelson-connector-ais) reference architecture:

1. **Functional over OOP** - Simple functions with handler registries
2. **Lazy resource creation** - Publishers created on first use
3. **Skarv for state** - In-memory vault for data aggregation
4. **Decorator-based subscriptions** - Clean event-driven patterns
5. **STDOUT discipline** - Always flush after write

### Adding New NMEA Sentence Types

To add support for additional NMEA sentence types:

#### In nmea01832keelson:

1. Create a handler function in [bin/nmea01832keelson](bin/nmea01832keelson):
   ```python
   def handle_xxx(msg, session, args):
       """Handle XXX - Description."""
       # Extract fields from msg
       # Publish to appropriate Keelson subjects
   ```

2. Register the handler:
   ```python
   MESSAGE_HANDLERS = {
       # ... existing handlers
       "XXX": handle_xxx,
   }
   ```

#### In keelson2nmea0183:

1. Add required subjects to `SUBJECTS` list in [bin/keelson2nmea0183](bin/keelson2nmea0183)

2. Create a subscriber function:
   ```python
   @skarv.subscribe("your_subject")
   def on_your_subject(sample: skarv.Sample):
       """Generate XXX sentence when subject is updated."""
       # Parse sample
       # Aggregate data from skarv
       # Generate NMEA sentence using pynmea2
       # Output with output_nmea()
   ```

## Testing

### Manual Testing

**Round-trip test:**
```bash
# Terminal 1: Generate NMEA from Keelson
keelson2nmea0183 -r "test/vessel" -e "sensors" > /tmp/nmea_output

# Terminal 2: Publish test data to Keelson
# (use keelson tools or write test script)

# Terminal 3: Feed NMEA back to Keelson
cat /tmp/nmea_output | nmea01832keelson -r "test/roundtrip" -e "sensors" -s "test"

# Verify data integrity
```

**Test with sample NMEA file:**
```bash
cat << 'EOF' > test.nmea
$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47
$GPGSA,A,3,04,05,,09,12,,,24,,,,,2.5,1.3,2.1*39
$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A
EOF

nmea01832keelson -r "test/vessel" -e "sensors" -s "gps" < test.nmea
```

## References

- **Keelson Protocol**: [https://rise-maritime.github.io/keelson/](https://rise-maritime.github.io/keelson/)
  - [Protocol Specification](https://rise-maritime.github.io/keelson/protocol-specification/)
  - [Subjects and Types](https://rise-maritime.github.io/keelson/subjects-and-types/)
- **NMEA0183 Standard**: Maritime navigation data communication protocol
- **Zenoh**: [https://zenoh.io/](https://zenoh.io/) - Zero Overhead Network Protocol
- **pynmea2**: [https://github.com/Knio/pynmea2](https://github.com/Knio/pynmea2)

## License

[Include your license information here]

## Contributing

Contributions are welcome! Please follow the existing code style and patterns established in the reference implementation.

## Support

For issues and questions:
- Open an issue on GitHub
- Refer to the Keelson documentation
- Check the keelson-connector-ais reference implementation
