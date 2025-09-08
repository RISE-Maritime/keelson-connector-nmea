# Keelson Connector NMEA

Keelson connector for NMEA devices using SOCAT as input.

This project reads NMEA sentences from a serial or UDP stream and publishes them on a Zenoh network using the Keelson data model. The main script parses various GNSS message types and publishes raw strings as well as structured location and navigation data.

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
### `bin/main`
Reads NMEA sentences from `stdin`, parses them with `pynmea2` and publishes selected fields using `keelson` and `zenoh`. Each NMEA type has a dedicated handler that serializes data into the appropriate Keelson protobuf payload such as `LocationFix`, `TimestampedFloat` or `TimestampedInt`.

### `bin/terminal_inputs.py`
Defines command line arguments for the connector including log level, Zenoh connection information and which NMEA sentences to publish.

### Docker setup
The `Dockerfile` builds a container containing the connector. `docker-compose.nmea.yml` provides examples for running the connector with SOCAT using either an UDP or USB source.

### Experimental notebooks
The `experimental` folder contains Jupyter notebooks and recorded JSON examples that demonstrate how to work with the produced data.

## Quick start (SOCAT pipe)
```bash
# UDP
socat UDP4-RECV:8500,reuseaddr STDOUT | python3 bin/main --log-level 10 -r rise -e ssrs18 -s rutx --publish raw

# TCP
socat TCP:192.168.1.124:6001 STDOUT | ./experimental/can-anavs-msg.py

# TCP with Enhanced ANavS Connector (1 kHz binary data)
socat TCP:192.168.1.124:6001 STDOUT | python3 ./experimental/anavs_connector.py --input-mode stdin -e vessel_name --publish all

# USB
sudo socat /dev/ttyUSB1,raw,echo=0,b115200 - | ./bin/main --log-level 10 -r rise -e ssrs18 -s sealog --publish all

# Multicast NMEA 
socat UDP4-RECV:60003,ip-add-membership=239.192.0.3:0.0.0.0,reuseaddr STDOUT | ./bin/main  --log-level 10 -r rise -e stena -s ins/1/anavs --publish all


```

## SOCAT install
```sh
sudo apt install socat
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
