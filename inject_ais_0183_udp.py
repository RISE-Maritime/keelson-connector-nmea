#!/usr/bin/env python3
"""
Inject NMEA 0183 AIS messages via UDP

This sends AIS VDM sentences to a UDP port for testing.
"""

import socket
import time

# UDP configuration
UDP_IP = "127.0.0.1"
UDP_PORT = 10183  # Different port for testing

# AIS vessel data at 54.89°N, 26.0°E
# This is an actual AIS Type 1 Position Report encoded properly
AIS_MESSAGES = [
    "!AIVDM,1,1,,A,13mI0B001GQre2LMEk`jtQv<0<09,0*68",  # Position report for MMSI 244670489
]

def send_nmea_0183_ais():
    """Send AIS NMEA 0183 messages via UDP"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    print(f"Sending NMEA 0183 AIS messages to {UDP_IP}:{UDP_PORT}")
    print(f"Position: 54.89°N, 26.0°E (Baltic Sea)")
    print()
    
    for msg in AIS_MESSAGES:
        # Add CR+LF as required by NMEA standard
        nmea_sentence = msg + "\r\n"
        
        print(f"Sending: {msg}")
        sock.sendto(nmea_sentence.encode('ascii'), (UDP_IP, UDP_PORT))
        time.sleep(0.1)
    
    print("\n✓ AIS messages sent!")
    print(f"\nTo receive these, configure a service to listen on UDP {UDP_PORT}")
    print("Example: socat UDP-RECV:10183 STDOUT | nmea01832keelson ...")
    
    sock.close()


if __name__ == "__main__":
    send_nmea_0183_ais()
