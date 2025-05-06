# Keelson Connector NMEA

Keelson connector for NMEA devices, by using SOCAT as input.

- NMEA messages supported:
  - GGA

## Quick start (SOCAT pipe)

```bash

# UDP
socat UDP4-RECV:8500,reuseaddr STDOUT | python3 bin/main --log-level 10 -r rise -e ssrs18 -s rutx --publish raw 

# USB

sudo socat /dev/ttyUSB1,raw,echo=0,b115200 - | ./bin/main --log-level 10 -r rise -e ssrs18 -s sealog --publish all

```

## SOCAT install

```sh
sudo apt install socat

```



Setup for development environment on your own computer: 

1) Install [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
   - Docker desktop will provide you with an UI for monitoring and controlling docker containers and images along debugging 
   - If you want to learn more about docker and its building blocks of images and containers checkout [Docker quick hands-on in guide](https://docs.docker.com/guides/get-started/)
2) Start up of **Zenoh router** either in your computer or any other computer within your local network 

   ```bash
    # Navigate to folder containing docker-compose.zenoh-router.yml
  
    # Start router with log output 
    docker-compose -f containing docker-compose.zenoh-router.yml up 

    # If no obvious errors, stop container "ctrl-c"

    # Start container and let it run in the background/detached (append -d) 
    docker-compose -f containing docker-compose.zenoh-router.yml up -d
   ```

    [Link to --> docker-compose.zenoh-router.yml](docker-compose.zenoh-router.yml)

3) Now the Zenoh router is hopefully running in the background and should be available on localhost:8000. This can be example tested with [Zenoh Rest API ](https://zenoh.io/docs/apis/rest/) or continue to next step running Python API
4) Set up python virtual environment  `python >= 3.11`
   1) Install package `pip install -r requirements.txt`
5) Now you are ready to explore some example scripts in the [exploration folder](./exploration/)
    1) Sample are coming from:
         - [Zenoh Python API ](https://zenoh-python.readthedocs.io/en/0.10.1-rc/#quick-start-examples)


[Zenoh CLI for debugging and problem solving](https://github.com/RISE-Maritime/zenoh-cli)

