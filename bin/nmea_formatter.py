#!/usr/bin/env python3

"""
NMEA Formatter Module

This module converts Keelson/Zenoh messages back to NMEA format.
It provides functions to generate various NMEA sentences from structured data.
"""

import time
import math
from datetime import datetime
from typing import Optional, Dict, Any
from keelson.payloads.Primitives_pb2 import TimestampedBytes, TimestampedInt, TimestampedFloat, TimestampedString, TimestampedTimestamp
from keelson.payloads.foxglove.LocationFix_pb2 import LocationFix


def calculate_nmea_checksum(sentence: str) -> str:
    """Calculate NMEA checksum for a sentence."""
    checksum = 0
    # Remove the $ if present and stop at * if present
    sentence = sentence.lstrip('$').split('*')[0]
    for char in sentence:
        checksum ^= ord(char)
    return f"{checksum:02X}"


def format_coordinate(degrees: float, is_longitude: bool = False) -> tuple[str, str]:
    """
    Convert decimal degrees to NMEA format (DDMM.MMMMM or DDDMM.MMMMM).
    Returns (formatted_coordinate, direction)
    """
    abs_degrees = abs(degrees)
    deg_int = int(abs_degrees)
    minutes = (abs_degrees - deg_int) * 60.0
    
    if is_longitude:
        coord_str = f"{deg_int:03d}{minutes:07.4f}"
        direction = "E" if degrees >= 0 else "W"
    else:
        coord_str = f"{deg_int:02d}{minutes:07.4f}"
        direction = "N" if degrees >= 0 else "S"
    
    return coord_str, direction


def format_time(timestamp: datetime) -> str:
    """Format datetime to HHMMSS.SS format for NMEA."""
    return timestamp.strftime("%H%M%S.%f")[:-4]  # Remove last 4 digits from microseconds


def format_date(timestamp: datetime) -> str:
    """Format datetime to DDMMYY format for NMEA."""
    return timestamp.strftime("%d%m%y")


def create_gga_sentence(location_fix: LocationFix, satellites_used: Optional[int] = None, 
                       hdop: Optional[float] = None, talker_id: str = "GP") -> str:
    """Create a GGA (Global Positioning System Fix Data) sentence."""
    timestamp = location_fix.timestamp.ToDatetime()
    time_str = format_time(timestamp)
    
    lat_str, lat_dir = format_coordinate(location_fix.latitude)
    lon_str, lon_dir = format_coordinate(location_fix.longitude, is_longitude=True)
    
    # Fix quality indicator (simplified: 1 = GPS fix, 0 = invalid)
    fix_quality = "1" if location_fix.latitude != 0 and location_fix.longitude != 0 else "0"
    
    # Number of satellites
    num_sats = str(satellites_used) if satellites_used is not None else ""
    
    # HDOP
    hdop_str = f"{hdop:.1f}" if hdop is not None else ""
    
    # Altitude
    altitude_str = f"{location_fix.altitude:.1f}" if hasattr(location_fix, 'altitude') and location_fix.altitude != 0 else ""
    altitude_units = "M" if altitude_str else ""
    
    # Geoid separation (simplified - set to empty)
    geoid_sep = ""
    geoid_units = ""
    
    # Age of differential GPS data (empty)
    dgps_age = ""
    dgps_station = ""
    
    sentence = f"${talker_id}GGA,{time_str},{lat_str},{lat_dir},{lon_str},{lon_dir},{fix_quality},{num_sats},{hdop_str},{altitude_str},{altitude_units},{geoid_sep},{geoid_units},{dgps_age},{dgps_station}"
    
    checksum = calculate_nmea_checksum(sentence)
    return f"{sentence}*{checksum}"


def create_rmc_sentence(location_fix: LocationFix, speed_knots: Optional[float] = None, 
                       course_deg: Optional[float] = None, talker_id: str = "GP") -> str:
    """Create an RMC (Recommended Minimum Course) sentence."""
    timestamp = location_fix.timestamp.ToDatetime()
    time_str = format_time(timestamp)
    date_str = format_date(timestamp)
    
    # Status (A = active, V = void)
    status = "A" if location_fix.latitude != 0 and location_fix.longitude != 0 else "V"
    
    lat_str, lat_dir = format_coordinate(location_fix.latitude)
    lon_str, lon_dir = format_coordinate(location_fix.longitude, is_longitude=True)
    
    # Speed over ground in knots
    speed_str = f"{speed_knots:.1f}" if speed_knots is not None else ""
    
    # Course over ground in degrees
    course_str = f"{course_deg:.1f}" if course_deg is not None else ""
    
    # Magnetic variation (empty for now)
    mag_var = ""
    mag_var_dir = ""
    
    # Mode indicator (A = autonomous)
    mode = "A"
    
    sentence = f"${talker_id}RMC,{time_str},{status},{lat_str},{lat_dir},{lon_str},{lon_dir},{speed_str},{course_str},{date_str},{mag_var},{mag_var_dir},{mode}"
    
    checksum = calculate_nmea_checksum(sentence)
    return f"{sentence}*{checksum}"


def create_vtg_sentence(course_deg: Optional[float] = None, speed_knots: Optional[float] = None, 
                       talker_id: str = "GP") -> str:
    """Create a VTG (Track Made Good and Ground Speed) sentence."""
    
    # True course
    true_course = f"{course_deg:.1f}" if course_deg is not None else ""
    true_indicator = "T" if true_course else ""
    
    # Magnetic course (same as true for simplicity)
    mag_course = true_course
    mag_indicator = "M" if mag_course else ""
    
    # Speed in knots
    speed_knots_str = f"{speed_knots:.1f}" if speed_knots is not None else ""
    knots_indicator = "N" if speed_knots_str else ""
    
    # Speed in km/h
    speed_kmh_str = f"{speed_knots * 1.852:.1f}" if speed_knots is not None else ""
    kmh_indicator = "K" if speed_kmh_str else ""
    
    # Mode indicator (A = autonomous)
    mode = "A" if course_deg is not None or speed_knots is not None else ""
    
    sentence = f"${talker_id}VTG,{true_course},{true_indicator},{mag_course},{mag_indicator},{speed_knots_str},{knots_indicator},{speed_kmh_str},{kmh_indicator},{mode}"
    
    checksum = calculate_nmea_checksum(sentence)
    return f"{sentence}*{checksum}"


def create_rot_sentence(rot_deg_per_min: float, talker_id: str = "GP") -> str:
    """Create a ROT (Rate of Turn) sentence."""
    
    # Rate of turn in degrees per minute
    rot_str = f"{rot_deg_per_min:.1f}"
    
    # Status (A = data valid)
    status = "A"
    
    sentence = f"${talker_id}ROT,{rot_str},{status}"
    
    checksum = calculate_nmea_checksum(sentence)
    return f"{sentence}*{checksum}"


def create_hdt_sentence(heading_deg: float, talker_id: str = "GP") -> str:
    """Create an HDT (Heading True) sentence."""
    
    heading_str = f"{heading_deg:.1f}"
    
    sentence = f"${talker_id}HDT,{heading_str},T"
    
    checksum = calculate_nmea_checksum(sentence)
    return f"{sentence}*{checksum}"


def create_pashr_sentence(timestamp: datetime, heading_deg: Optional[float] = None, 
                         roll_deg: Optional[float] = None, pitch_deg: Optional[float] = None,
                         heave_m: Optional[float] = None, is_true_heading: bool = True) -> str:
    """Create a PASHR (RT300 proprietary roll and pitch) sentence."""
    
    time_str = format_time(timestamp)
    
    # Heading
    heading_str = f"{heading_deg:.1f}" if heading_deg is not None else ""
    heading_type = "T" if is_true_heading else "M"
    
    # Roll (positive = port side down)
    roll_str = f"{roll_deg:.1f}" if roll_deg is not None else ""
    
    # Pitch (positive = bow up)  
    pitch_str = f"{pitch_deg:.1f}" if pitch_deg is not None else ""
    
    # Heave (positive = up)
    heave_str = f"{heave_m:.2f}" if heave_m is not None else ""
    
    # Accuracy estimates (simplified - empty for now)
    roll_acc = ""
    pitch_acc = ""
    heading_acc = ""
    
    # Status flags (simplified)
    aiding_status = "1"  # GPS + inertial
    imu_status = "0"     # Good
    
    sentence = f"$PASHR,{time_str},{heading_str},{heading_type},{roll_str},{pitch_str},{heave_str},{roll_acc},{pitch_acc},{heading_acc},{aiding_status},{imu_status}"
    
    checksum = calculate_nmea_checksum(sentence)
    return f"{sentence}*{checksum}"


def create_zda_sentence(timestamp: datetime, talker_id: str = "GP") -> str:
    """Create a ZDA (Date and Time) sentence."""
    
    time_str = format_time(timestamp)
    day = timestamp.strftime("%d")
    month = timestamp.strftime("%m")
    year = timestamp.strftime("%Y")
    
    # Local zone description (00,00 for UTC)
    local_zone_hours = "00"
    local_zone_minutes = "00"
    
    sentence = f"${talker_id}ZDA,{time_str},{day},{month},{year},{local_zone_hours},{local_zone_minutes}"
    
    checksum = calculate_nmea_checksum(sentence)
    return f"{sentence}*{checksum}"


class NmeaFormatter:
    """
    NMEA Formatter class that maintains state and provides high-level formatting methods.
    """
    
    def __init__(self):
        self.last_location_fix = None
        self.last_speed_knots = None
        self.last_course_deg = None
        self.last_satellites_used = None
        self.last_hdop = None
        self.last_heading_deg = None
        self.last_roll_deg = None
        self.last_pitch_deg = None
        self.last_heave_m = None
        self.last_rot_deg_per_min = None
    
    def update_location_fix(self, location_fix: LocationFix):
        """Update the stored location fix data."""
        self.last_location_fix = location_fix
    
    def update_speed(self, speed_knots: float):
        """Update the stored speed data."""
        self.last_speed_knots = speed_knots
    
    def update_course(self, course_deg: float):
        """Update the stored course data."""
        self.last_course_deg = course_deg
    
    def update_satellites_used(self, satellites_used: int):
        """Update the stored satellites used data."""
        self.last_satellites_used = satellites_used
    
    def update_hdop(self, hdop: float):
        """Update the stored HDOP data."""
        self.last_hdop = hdop
    
    def update_heading(self, heading_deg: float):
        """Update the stored heading data."""
        self.last_heading_deg = heading_deg
    
    def update_attitude(self, roll_deg: Optional[float] = None, 
                       pitch_deg: Optional[float] = None, heave_m: Optional[float] = None):
        """Update the stored attitude data."""
        if roll_deg is not None:
            self.last_roll_deg = roll_deg
        if pitch_deg is not None:
            self.last_pitch_deg = pitch_deg
        if heave_m is not None:
            self.last_heave_m = heave_m
    
    def update_rot(self, rot_deg_per_min: float):
        """Update the stored rate of turn data."""
        self.last_rot_deg_per_min = rot_deg_per_min
    
    def generate_gga_sentence(self, talker_id: str = "GP") -> Optional[str]:
        """Generate a GGA sentence from stored data."""
        if self.last_location_fix is None:
            return None
        return create_gga_sentence(self.last_location_fix, self.last_satellites_used, 
                                 self.last_hdop, talker_id)
    
    def generate_rmc_sentence(self, talker_id: str = "GP") -> Optional[str]:
        """Generate an RMC sentence from stored data."""
        if self.last_location_fix is None:
            return None
        return create_rmc_sentence(self.last_location_fix, self.last_speed_knots, 
                                 self.last_course_deg, talker_id)
    
    def generate_vtg_sentence(self, talker_id: str = "GP") -> Optional[str]:
        """Generate a VTG sentence from stored data."""
        if self.last_course_deg is None and self.last_speed_knots is None:
            return None
        return create_vtg_sentence(self.last_course_deg, self.last_speed_knots, talker_id)
    
    def generate_rot_sentence(self, talker_id: str = "GP") -> Optional[str]:
        """Generate a ROT sentence from stored data."""
        if self.last_rot_deg_per_min is None:
            return None
        return create_rot_sentence(self.last_rot_deg_per_min, talker_id)
    
    def generate_hdt_sentence(self, talker_id: str = "GP") -> Optional[str]:
        """Generate an HDT sentence from stored data."""
        if self.last_heading_deg is None:
            return None
        return create_hdt_sentence(self.last_heading_deg, talker_id)
    
    def generate_pashr_sentence(self) -> Optional[str]:
        """Generate a PASHR sentence from stored data."""
        if all(x is None for x in [self.last_heading_deg, self.last_roll_deg, 
                                  self.last_pitch_deg, self.last_heave_m]):
            return None
        
        timestamp = datetime.now() if self.last_location_fix is None else self.last_location_fix.timestamp.ToDatetime()
        return create_pashr_sentence(timestamp, self.last_heading_deg, self.last_roll_deg,
                                   self.last_pitch_deg, self.last_heave_m)
    
    def generate_zda_sentence(self, talker_id: str = "GP") -> str:
        """Generate a ZDA sentence with current time."""
        timestamp = datetime.now() if self.last_location_fix is None else self.last_location_fix.timestamp.ToDatetime()
        return create_zda_sentence(timestamp, talker_id)