# Keelson Connector NMEA

**Bidirectional** Keelson connector for NMEA devices supporting both input and output operations.

This project provides **bidirectional NMEA connectivity**:
1. **NMEA → Keelson**: Reads NMEA sentences from serial, UDP, or TCP streams and publishes them on a Zenoh network using the Keelson data model
2. **Keelson → NMEA**: Subscribes to Keelson messages and converts them back to NMEA format for output via UDP, TCP, Serial, or Multicast

The connector parses various GNSS message types and publishes structured location, navigation, and attitude data, while also being able to regenerate NMEA sentences from Keelson data.

## Supported NMEA messages
- GNGNS - Global Navigation Satellite System Fix Data
- GPGGA - Global Positioning System Fix Data
- GPGSA - GNSS DOP and Active Satellites
- GPVTG - Course over ground and ground speed
- GPRMC - Recommended Minimum Specific GNSS Data
- GPGSV - GPS Satellites in View
- ROT - Rate of Turn
- Raw NMEA sentences

## Code overview

### Core Scripts
#### `bin/main` (Original)
Legacy NMEA input-only connector. Reads NMEA sentences from `stdin`, parses them with `pynmea2` and publishes selected fields using `keelson` and `zenoh`. Each NMEA type has a dedicated handler that serializes data into the appropriate Keelson protobuf payload such as `LocationFix`, `TimestampedFloat` or `TimestampedInt`.

#### `bin/main_bidirectional` (New)
**Bidirectional NMEA connector** that supports both input and output operations:
- **Input mode**: Processes NMEA from stdin (like the original)
- **Output mode**: Subscribes to Keelson messages and outputs NMEA via multiple transports
- **Bidirectional mode**: Handles both input and output simultaneously

### Supporting Modules
#### `bin/terminal_inputs.py`
Defines command line arguments including:
- Original arguments for NMEA input processing 
- New arguments for NMEA output configuration (UDP, TCP, Serial, Multicast, SOCAT)
- Output sentence types and generation rates

#### `bin/nmea_formatter.py`
Converts Keelson/Zenoh messages back to NMEA format. Supports generating:
- GGA (Global Positioning System Fix Data)
- RMC (Recommended Minimum Course)  
- VTG (Track Made Good and Ground Speed)
- ROT (Rate of Turn)
- HDT (Heading True)
- PASHR (Proprietary pitch/roll/heading)
- ZDA (Date and Time)

#### `bin/nmea_output_adapter.py`
Handles NMEA sentence output via various transport methods:
- UDP unicast/broadcast
- TCP client connections
- Serial ports
- UDP multicast
- SOCAT processes for complex configurations

#### `bin/keelson_to_nmea.py`
Zenoh subscriber that listens for Keelson messages and converts them to NMEA sentences using the formatter and output adapters.

### Docker setup
The `Dockerfile` builds a container containing the connector. `docker-compose.nmea.yml` provides examples for running the connector with SOCAT using either an UDP or USB source.

### Experimental notebooks
The `experimental` folder contains Jupyter notebooks and recorded JSON examples that demonstrate how to work with the produced data.

## Quick Start Examples

### Original NMEA Input (Legacy)
```bash
# UDP input
socat UDP4-RECV:8500,reuseaddr STDOUT | python3 bin/main --log-level 10 -r rise -e vessel1 -s gps/rutx --publish all

# USB/Serial input  
sudo socat /dev/ttyUSB1,raw,echo=0,b115200 - | python3 bin/main --log-level 10 -r rise -e vessel1 -s gps/sealog --publish all

# Multicast input
socat UDP4-RECV:60003,ip-add-membership=239.192.0.3:0.0.0.0,reuseaddr STDOUT | python3 bin/main --log-level 10 -r rise -e vessel1 -s ins/anavs --publish all
```

### Bidirectional NMEA Connector (New)

#### Input Only (Same as legacy)
```bash
# Process NMEA from UDP input
socat UDP4-RECV:8500,reuseaddr STDOUT | python3 bin/main_bidirectional --log-level 10 -r rise -e vessel1 -s gps/1 --publish all
```

#### Output Only
```bash  
# Generate NMEA from Keelson messages and output via UDP
python3 bin/main_bidirectional --log-level 10 -r rise -e vessel1 --output-only \
  --output-udp 192.168.1.100:8501 \
  --nmea-sentences GGA,RMC,VTG,HDT \
  --nmea-rate-hz 2.0

# Output to multiple destinations
python3 bin/main_bidirectional --log-level 10 -r rise -e vessel1 --output-only \
  --output-udp 192.168.1.100:8501 \
  --output-tcp 192.168.1.200:8502 \
  --output-serial /dev/ttyUSB0:115200 \
  --nmea-sentences GGA,RMC,VTG

# Output via multicast
python3 bin/main_bidirectional --log-level 10 -r rise -e vessel1 --output-only \
  --output-multicast 239.192.0.10:8503 \
  --nmea-sentences GGA,RMC,PASHR,HDT
```

#### Bidirectional (Input + Output)
```bash
# Read NMEA from UDP, publish to Keelson, and output regenerated NMEA via different transport
socat UDP4-RECV:8500,reuseaddr STDOUT | python3 bin/main_bidirectional \
  --log-level 10 -r rise -e vessel1 -s gps/input \
  --publish all \
  --output-udp 192.168.1.100:8501 \
  --nmea-sentences GGA,RMC,VTG

# Bridge between serial and network
sudo socat /dev/ttyUSB1,raw,echo=0,b115200 - | python3 bin/main_bidirectional \
  --log-level 10 -r rise -e vessel1 -s gps/serial \
  --publish all \
  --output-udp 192.168.1.255:8501 \
  --nmea-sentences GGA,RMC,VTG,ROT
```

#### Advanced SOCAT Integration  
```bash
# Use SOCAT for complex output routing
python3 bin/main_bidirectional --log-level 10 -r rise -e vessel1 --output-only \
  --output-socat "STDOUT | socat - UDP4-SENDTO:192.168.1.100:8501" \
  --nmea-sentences GGA,RMC,VTG

# Multiple SOCAT outputs
python3 bin/main_bidirectional --log-level 10 -r rise -e vessel1 --output-only \
  --output-socat "STDOUT | socat - UDP4-SENDTO:192.168.1.100:8501" \
  --output-socat "STDOUT | socat - /dev/ttyUSB2,raw,echo=0,b115200" \
  --nmea-sentences GGA,RMC,VTG,HDT,PASHR
```

## Requirements and Installation

### System Dependencies
```sh
# Install SOCAT for advanced I/O operations
sudo apt install socat

# Install netcat for testing (optional)
sudo apt install netcat-openbsd
```

### Python Dependencies
The connector requires Python 3.8+ and the following packages (automatically installed):
- `keelson` - Keelson protobuf messages and Zenoh integration
- `pynmea2` - NMEA sentence parsing
- `pyserial` - Serial port communication
- `pytz` - Timezone handling
- `zenoh` - Zenoh networking (installed with keelson)

## Testing the Implementation

### Quick Test
Run the test script to verify all components work:
```bash
python3 test_bidirectional.py
```

### Manual Testing

#### Test NMEA Output
1. Start the connector in output mode:
```bash
python3 bin/main_bidirectional --log-level 10 -r rise -e test_vessel --output-only \
  --output-udp 127.0.0.1:8501 --nmea-sentences GGA,RMC,VTG --nmea-rate-hz 0.5
```

2. In another terminal, listen for NMEA output:
```bash
nc -lu 8501
```

3. Publish test Keelson messages (requires Zenoh router and keelson tools)

#### Test NMEA Input  
1. Start the connector in input mode:
```bash
python3 bin/main_bidirectional --log-level 10 -r rise -e test_vessel -s test/gps --publish all
```

2. Send test NMEA data:
```bash
echo '$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47' | python3 bin/main_bidirectional --log-level 10 -r rise -e test_vessel -s test/gps --publish all
```

Setup for development environment on your own computer:

1. Install [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
   - Docker desktop provides an UI for monitoring and controlling docker containers
   - If you want to learn more about docker and its building blocks checkout [Docker quick hands-on guide](https://docs.docker.com/guides/get-started/)
2. Start up of **Zenoh router** either on your computer or another machine within your local network

   ```bash
   # Navigate to folder containing docker-compose.zenoh-router.yml

   # Start router with log output
  docker-compose -f docker-compose.zenoh-router.yml up

   # If no obvious errors, stop container with "ctrl-c"

   # Start container and let it run in the background/detached (append -d)
  docker-compose -f docker-compose.zenoh-router.yml up -d
   ```

  [docker-compose.zenoh-router.yml](docker-compose.zenoh-router.yml)

3. Now the Zenoh router should be running and available on localhost:8000. This can be tested with the [Zenoh Rest API](https://zenoh.io/docs/apis/rest/) or by continuing to the next step using the Python API
4. Set up a python virtual environment (`python >= 3.11`)
   1. Install packages with `pip install -r requirements.txt`
5. Explore example scripts in the [experimental folder](./experimental/)
   1. Samples are based on the [Zenoh Python API](https://zenoh-python.readthedocs.io/en/0.10.1-rc/#quick-start-examples)

[Zenoh CLI for debugging and problem solving](https://github.com/RISE-Maritime/zenoh-cli)
