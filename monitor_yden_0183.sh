#!/bin/bash

# Monitor YDEN NMEA 0183 output to verify AIS injection
# This should show VDM sentences if your injection worked

echo "Monitoring YDEN NMEA 0183 output (port 1456)..."
echo "Press Ctrl+C to stop"
echo ""

nc 192.168.1.22 1456
