#!/bin/bash

# Send a fake AIS message to NGX-1 on /dev/ttyUSB0
# This simulates a vessel at a specific position

SERIAL_PORT="/dev/ttyUSB0"
BAUD_RATE="4800"

# AIS Type 1 Position Report (Class A vessel)
# MMSI: 211512000, Speed: 12.3 knots, Course: 72.2°, Lat: 54.89°N, Lon: 26.0°E
AIS_MESSAGE="!AIVDM,1,1,,A,13HOI:0P00?wK8UMDTph8wwwP05M,0*5C"

echo "Configuring serial port $SERIAL_PORT at $BAUD_RATE baud..."
sudo stty -F "$SERIAL_PORT" "$BAUD_RATE" raw -echo

echo "Sending fake AIS message to NGX-1..."
echo "$AIS_MESSAGE" | sudo tee "$SERIAL_PORT" > /dev/null

echo "✓ Sent: $AIS_MESSAGE"
echo ""
echo "This message represents:"
echo "  - MMSI: 211512000"
echo "  - Message Type: 1 (Position Report)"
echo "  - Navigation Status: Under way using engine"
echo "  - Position: 54.89°N, 26.0°E (Baltic Sea)"
echo "  - Speed: ~12.3 knots"
echo "  - Course: ~72°"
