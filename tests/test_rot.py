import os
import sys

# Ensure the bin directory is on sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'bin'))

from nmea_utils import extract_rot_value


def test_extract_rot_value():
    sentence = "$GPROT,1.5,A*00"
    assert extract_rot_value(sentence) == 1.5
