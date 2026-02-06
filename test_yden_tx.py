#!/usr/bin/env python3
"""Test if YDEN accepts ANY commands on UDP 1458"""
import socket
import time

YDEN_IP = "192.168.1.22"

# Try different ports and command formats
tests = [
    (1458, b"?VER\r\n", "Version query UDP 1458"),
    (1458, b"?INFO\r\n", "Info query UDP 1458"),
    (1458, b"?HELP\r\n", "Help query UDP 1458"),
]

for port, cmd, desc in tests:
    print(f"Testing: {desc}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1.0)
    sock.sendto(cmd, (YDEN_IP, port))
    try:
        response, _ = sock.recvfrom(1024)
        print(f"  Response: {response}")
    except socket.timeout:
        print(f"  No response (timeout)")
    sock.close()
    time.sleep(0.1)

# Check if YDEN responds to TCP commands
print("\nTesting TCP 1456 (NMEA 0183 output):")
try:
    tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_sock.settimeout(2.0)
    tcp_sock.connect((YDEN_IP, 1456))
    tcp_sock.send(b"?VER\r\n")
    time.sleep(0.5)
    data = b""
    try:
        while True:
            chunk = tcp_sock.recv(1024)
            if not chunk:
                break
            data += chunk
            if len(data) > 500:
                break
    except socket.timeout:
        pass
    print(f"  Received {len(data)} bytes")
    if data:
        for line in data.decode('latin-1').split('\n')[:5]:
            print(f"    {line.strip()}")
    tcp_sock.close()
except Exception as e:
    print(f"  Error: {e}")

print("\nNote: YDEN may be read-only for N2K. Alternative: inject VDM directly via TCP.")
