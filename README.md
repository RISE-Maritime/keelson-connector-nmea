# Keelson NMEA Connector

Bidirectional connectors between NMEA0183/NMEA2000 maritime protocols and the Keelson/Zenoh data distribution framework.

## Overview

This repository provides command-line utilities for converting between NMEA maritime data formats (both NMEA0183 and NMEA2000) and the Keelson protocol on a Zenoh messaging bus:

### NMEA0183 Connectors
- **`nmea01832keelson`** - Reads NMEA0183 sentences from STDIN and publishes structured data to Keelson/Zenoh
- **`keelson2nmea0183`** - Subscribes to Keelson/Zenoh subjects and outputs NMEA0183 sentences to STDOUT

### NMEA2000 (N2K) Connectors
- **`n2k-cli`** - Bidirectional bridge between NMEA2000 CAN gateways and JSON streams
- **`n2k2keelson`** - Reads NMEA2000 JSON from STDIN and publishes structured data to Keelson/Zenoh
- **`keelson2n2k`** - Subscribes to Keelson/Zenoh subjects and outputs NMEA2000 JSON to STDOUT

These tools enable integration between legacy NMEA-based systems (GPS receivers, chart plotters, autopilots, CAN networks) and modern Zenoh-based maritime platforms.

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

## Supported NMEA2000 PGNs

The NMEA2000 connectors support the following Parameter Group Numbers (PGNs):

| PGN | Name | Keelson Subjects |
|-----|------|------------------|
| **129025** | Position, Rapid Update | `location_fix` |
| **129026** | COG & SOG, Rapid Update | `course_over_ground_deg`, `speed_over_ground_knots` |
| **129029** | GNSS Position Data | `location_fix`, `location_fix_satellites_used`, `location_fix_hdop`, `location_fix_undulation_m` |
| **127250** | Vessel Heading | `heading_true_north_deg` or `heading_magnetic_deg` |
| **127257** | Attitude | `yaw_deg`, `pitch_deg`, `roll_deg` |
| **130306** | Wind Data | `apparent_wind_speed_mps`, `apparent_wind_angle_deg` (or true variants) |
| **127245** | Rudder | `rudder_angle_deg` |
| **130311** | Environmental Parameters | `water_temperature_celsius`, `air_pressure_pa` |

### NMEA2000 Architecture

The NMEA2000 connectors use a **three-component architecture** with JSON as the interchange format:

```
CAN Gateway ←→ n2k-cli (JSON bridge) ←→ n2k2keelson/keelson2n2k ←→ Keelson/Zenoh
```

**Why this design?**
- **Hardware abstraction**: n2k-cli handles all CAN gateway communication (TCP, USB, various protocols)
- **Composability**: Follows Unix philosophy - can pipe data through any tool
- **Testability**: Easy to test with mock JSON data
- **Reusability**: Components can be used independently or with other systems
- **Consistency**: Same STDIN/STDOUT pattern as NMEA0183 connectors

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
- `nmea2000` - NMEA2000 PGN encoding/decoding library
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

### NMEA2000 CAN Gateway Bridge (`n2k-cli`)

Bidirectional bridge between NMEA2000 CAN gateways and JSON streams. This tool provides the hardware abstraction layer for NMEA2000 communication.

#### Supported Gateways

- **TCP**: EBYTE (ECAN-E01/W01), Actisense (W2K-1), Yacht Devices (YDWG-02)
- **USB**: Waveshare USB-CAN-A

#### Read Mode (CAN → JSON)

```bash
# Read from EBYTE gateway
n2k-cli read \
  --gateway-type tcp \
  --host 192.168.0.46 \
  --port 8881 \
  --protocol ebyte

# Read from Actisense gateway
n2k-cli read \
  --gateway-type tcp \
  --host 192.168.1.100 \
  --port 10110 \
  --protocol actisense

# Read from USB gateway
n2k-cli read \
  --gateway-type usb \
  --port /dev/ttyUSB0 \
  --protocol waveshare

# Filter specific PGNs
n2k-cli read \
  --gateway-type tcp \
  --host 192.168.0.46 \
  --port 8881 \
  --protocol ebyte \
  --include-pgns 129025,129026,127250
```

#### Write Mode (JSON → CAN)

```bash
# Write JSON messages to CAN gateway
cat nmea2000_messages.json | n2k-cli write \
  --gateway-type tcp \
  --host 192.168.0.46 \
  --port 8881 \
  --protocol ebyte
```

### NMEA2000 → Keelson (`n2k2keelson`)

Reads NMEA2000 messages in JSON format from standard input and publishes to Keelson/Zenoh.

#### Basic Usage

```bash
# Read from CAN gateway and publish to Keelson
n2k-cli read --gateway-type tcp --host 192.168.0.46 --port 8881 --protocol ebyte \
  | n2k2keelson -r "vessel/test_boat" -e "sensors" -s "n2k/primary"
```

#### Command-Line Options

```
Required Arguments:
  -r, --realm REALM              Keelson realm (e.g., "vessel/sv_colibri")
  -e, --entity-id ENTITY_ID      Entity identifier (e.g., "sensors")
  -s, --source-id SOURCE_ID      Source identifier (e.g., "n2k/primary")

Optional Arguments:
  --log-level LEVEL              Log level: 10=DEBUG, 20=INFO, 30=WARNING, 40=ERROR (default: 20)
  --mode {peer,client}           Zenoh session mode (default: peer)
  --connect ENDPOINT             Zenoh router endpoint (can be used multiple times)
  --publish-raw                  Also publish raw JSON messages to 'raw' subject
```

#### Examples

**Connect to specific Zenoh router:**
```bash
n2k-cli read --gateway-type tcp --host 192.168.0.46 --port 8881 --protocol ebyte \
  | n2k2keelson \
      -r "vessel/sv_colibri" \
      -e "sensors" \
      -s "n2k/primary" \
      --mode client \
      --connect "tcp/192.168.1.100:7447"
```

**Debug with tee:**
```bash
n2k-cli read --gateway-type tcp --host 192.168.0.46 --port 8881 --protocol ebyte \
  | tee /tmp/n2k-debug.json \
  | n2k2keelson -r "vessel/sv_colibri" -e "sensors" -s "n2k/primary"

# In another terminal:
tail -f /tmp/n2k-debug.json | jq .
```

**Publish raw JSON for debugging:**
```bash
n2k-cli read --gateway-type tcp --host 192.168.0.46 --port 8881 --protocol ebyte \
  | n2k2keelson \
      -r "vessel/sv_colibri" \
      -e "sensors" \
      -s "n2k/primary" \
      --publish-raw
```

### Keelson → NMEA2000 (`keelson2n2k`)

Subscribes to Keelson/Zenoh subjects and outputs NMEA2000 messages in JSON format to standard output.

#### Basic Usage

```bash
# Subscribe to Keelson and output JSON to CAN gateway
keelson2n2k -r "vessel/sv_colibri" -e "sensors" \
  | n2k-cli write --gateway-type tcp --host 192.168.0.46 --port 8881 --protocol ebyte
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
  --source-address ADDRESS       NMEA2000 source address (0-253, default: 1)
  --priority PRIORITY            Message priority (0-7, lower is higher, default: 2)
  --source_id_SUBJECT PATTERN    Source pattern for specific subject (default: "**")
```

#### Examples

**Change NMEA2000 source address:**
```bash
keelson2n2k \
  -r "vessel/sv_colibri" \
  -e "autopilot" \
  --source-address 10 \
  | n2k-cli write --gateway-type tcp --host 192.168.0.46 --port 8881 --protocol ebyte
```

**Filter by specific sources:**
```bash
keelson2n2k \
  -r "vessel/sv_colibri" \
  -e "sensors" \
  --source_id_location_fix "gps/**" \
  --source_id_heading_true_north_deg "compass/primary" \
  | n2k-cli write --gateway-type tcp --host 192.168.0.46 --port 8881 --protocol ebyte
```

**Bidirectional setup (separate terminals):**
```bash
# Terminal 1: N2K → Keelson
n2k-cli read --gateway-type tcp --host 192.168.0.46 --port 8881 --protocol ebyte \
  | n2k2keelson -r "vessel/sv_colibri" -e "sensors" -s "n2k/primary"

# Terminal 2: Keelson → N2K
keelson2n2k -r "vessel/sv_colibri" -e "autopilot" \
  | n2k-cli write --gateway-type tcp --host 192.168.0.46 --port 8881 --protocol ebyte
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
│   ├── nmea01832keelson       # NMEA0183 → Keelson script
│   ├── keelson2nmea0183       # Keelson → NMEA0183 script
│   ├── n2k-cli                # NMEA2000 CAN gateway bridge
│   ├── n2k2keelson            # NMEA2000 → Keelson script
│   ├── keelson2n2k            # Keelson → NMEA2000 script
│   └── utils.py               # Shared helper functions
├── tests/
│   ├── test_nmea2keelson.py   # NMEA0183 tests
│   ├── test_keelson2nmea.py   # NMEA0183 tests
│   ├── test_n2k_cli.py        # NMEA2000 CLI tests
│   └── test_n2k2keelson.py    # NMEA2000 connector tests
├── requirements.txt           # Python dependencies
├── requirements_dev.txt       # Development dependencies
└── README.md                  # This file
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
