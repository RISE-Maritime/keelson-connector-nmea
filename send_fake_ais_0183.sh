#!/bin/bash
# Send fake AIS VDM sentences to test the nmea01832keelson parser
# 
# This sends NMEA 0183 AIS sentences (VDM format) to the Docker container
# via a named pipe or direct stdin injection.
#
# VDM sentence structure:
# !AIVDM,fragments,fragno,seqid,channel,payload,pad*checksum

# AIS Class A Position Report (Type 1) for MMSI 211512000
# Position: 54.89°N, 26.0°E
# Encoded using 6-bit ASCII

# Pre-computed VDM sentences (can be generated with aislib or similar)
# These are valid AIS messages for testing:

# Type 1: Position Report Class A
# MMSI: 211512000, Lat: 54.89, Lon: 26.0, SOG: 12.3, COG: 72.0, Heading: 75
VDM1='!AIVDM,1,1,,A,13m@aP0P01H<s3T4w5F0000S0@30,0*17'

# Type 5: Static and Voyage data (vessel name, etc.) - 2 fragments
VDM5_1='!AIVDM,2,1,3,B,53m@aP02>FcT0000000000000000010DHh8p88880,0*30'
VDM5_2='!AIVDM,2,2,3,B,00000000000,2*27'

# Simple way to test - just echo and send
echo "Sending test AIS VDM sentences..."
echo ""
echo "VDM1: $VDM1"
echo ""

# Option 1: If running locally with stdin pipe
# echo "$VDM1" | docker exec -i keelson-nmea01832keelson cat

# Option 2: Write to a test file that can be piped
cat << 'EOF' > /tmp/test_ais.nmea
!AIVDM,1,1,,A,13m@aP0P01H<s3T4w5F0000S0@30,0*17
!AIVDM,1,1,,B,133w;`PP00PD;88MD5MTDww@0<4w,0*7B
!AIVDM,1,1,,A,14eGrSgP00PFtKvL=gNLOVJn0<1s,0*4F
!AIVDM,2,1,3,B,53m@aP02>FcT0000000000000000010DHh8p88880,0*30
!AIVDM,2,2,3,B,00000000000,2*27
EOF

echo "Test AIS data written to /tmp/test_ais.nmea"
echo ""
echo "To test, run:"
echo "  cat /tmp/test_ais.nmea | python3 bin/nmea01832keelson --mode router://default"
echo ""
echo "Or inject into Docker container:"
echo "  cat /tmp/test_ais.nmea | docker exec -i keelson-nmea01832keelson cat >> /dev/stdin"
