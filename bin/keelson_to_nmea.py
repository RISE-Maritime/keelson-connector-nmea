#!/usr/bin/env python3

"""
Keelson to NMEA Converter Module

This module subscribes to Keelson/Zenoh messages and converts them to NMEA format
for output via various transport methods.
"""

import zenoh
import logging
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass
import keelson
from keelson.payloads.Primitives_pb2 import TimestampedBytes, TimestampedInt, TimestampedFloat, TimestampedString, TimestampedTimestamp
from keelson.payloads.foxglove.LocationFix_pb2 import LocationFix

from nmea_formatter import NmeaFormatter
from nmea_output_adapter import MultiOutputAdapter


@dataclass
class SubscriptionConfig:
    """Configuration for Keelson message subscriptions."""
    realm: str
    entity_id: str
    source_patterns: List[str]  # Source ID patterns to subscribe to
    subjects: Set[str]  # Subjects to subscribe to
    nmea_sentences: Set[str]  # NMEA sentences to generate
    update_rate_hz: float = 1.0  # Rate to generate NMEA sentences
    talker_id: str = "GP"  # Default NMEA talker ID


class KeelsonToNmeaConverter:
    """
    Converts Keelson/Zenoh messages to NMEA sentences and outputs them.
    """
    
    def __init__(self, session: zenoh.Session, subscription_config: SubscriptionConfig, 
                 output_adapter: MultiOutputAdapter):
        self.session = session
        self.config = subscription_config
        self.output_adapter = output_adapter
        self.logger = logging.getLogger("KeelsonToNmea")
        
        # NMEA formatter to maintain state and generate sentences
        self.formatter = NmeaFormatter()
        
        # Subscriber tracking
        self.subscribers = []
        self._running = False
        
        # Data tracking for rate limiting
        self._last_output_time = 0.0
        self._output_interval = 1.0 / self.config.update_rate_hz
        
        # Subject to handler mapping
        self.subject_handlers = {
            "location_fix": self._handle_location_fix,
            "speed_over_ground_knots": self._handle_speed,
            "course_over_ground_deg": self._handle_course,
            "location_fix_satellites_used": self._handle_satellites_used,
            "location_fix_hdop": self._handle_hdop,
            "heading_true_north_deg": self._handle_heading_true,
            "heading_magnetic_deg": self._handle_heading_magnetic,
            "roll_deg": self._handle_roll,
            "pitch_deg": self._handle_pitch,
            "heave_m": self._handle_heave,
            "yaw_rate_degps": self._handle_yaw_rate,
            "timestamp": self._handle_timestamp,
        }
        
    async def start(self):
        """Start subscribing to Keelson messages."""
        try:
            self._running = True
            
            # Subscribe to relevant topics
            for source_pattern in self.config.source_patterns:
                for subject in self.config.subjects:
                    key_expr = keelson.construct_pubsub_key(
                        base_path=self.config.realm,
                        entity_id=self.config.entity_id,
                        subject=subject,
                        source_id=source_pattern,
                    )
                    
                    subscriber = self.session.declare_subscriber(
                        key_expr,
                        self._message_handler
                    )
                    self.subscribers.append(subscriber)
                    self.logger.info(f"Subscribed to: {key_expr}")
            
            self.logger.info(f"Started Keelson to NMEA converter with {len(self.subscribers)} subscriptions")
            
        except Exception as e:
            self.logger.error(f"Failed to start converter: {e}")
            raise
    
    async def stop(self):
        """Stop the converter and clean up subscriptions."""
        self._running = False
        
        for subscriber in self.subscribers:
            try:
                subscriber.undeclare()
            except Exception as e:
                self.logger.error(f"Error undeclaring subscriber: {e}")
        
        self.subscribers.clear()
        self.logger.info("Keelson to NMEA converter stopped")
    
    def _message_handler(self, sample):
        """Handle incoming Zenoh messages."""
        if not self._running:
            return
            
        try:
            # Parse the key to extract subject and source
            key_parts = sample.key_expr.split('/')
            if len(key_parts) < 4:
                self.logger.debug(f"Unexpected key format: {sample.key_expr}")
                return
            
            subject = key_parts[3]  # Assuming format: realm/entity/subject/source
            source = '/'.join(key_parts[4:]) if len(key_parts) > 4 else ""
            
            self.logger.debug(f"Received message - Subject: {subject}, Source: {source}")
            
            # Decode the Keelson envelope
            try:
                decoded_envelope = keelson.uncover(sample.payload)
                # keelson.uncover returns (schema_id, schema_version, payload_bytes)
                if isinstance(decoded_envelope, tuple) and len(decoded_envelope) >= 3:
                    payload_bytes = decoded_envelope[2]
                else:
                    payload_bytes = decoded_envelope
            except Exception as e:
                self.logger.warning(f"Failed to uncover Keelson envelope: {e}")
                return
            
            # Handle the message based on subject
            if subject in self.subject_handlers:
                self.subject_handlers[subject](payload_bytes, subject, source)
            else:
                self.logger.debug(f"No handler for subject: {subject}")
            
            # Generate NMEA sentences at configured rate
            self._maybe_generate_nmea()
            
        except Exception as e:
            self.logger.error(f"Error handling message: {e}")
    
    def _handle_location_fix(self, payload: bytes, subject: str, source: str):
        """Handle LocationFix messages."""
        try:
            location_fix = LocationFix()
            location_fix.ParseFromString(payload)
            self.formatter.update_location_fix(location_fix)
            self.logger.debug(f"Updated location fix: lat={location_fix.latitude:.6f}, lon={location_fix.longitude:.6f}")
        except Exception as e:
            self.logger.error(f"Error parsing LocationFix: {e}")
    
    def _handle_speed(self, payload: bytes, subject: str, source: str):
        """Handle speed over ground messages."""
        try:
            speed_msg = TimestampedFloat()
            speed_msg.ParseFromString(payload)
            self.formatter.update_speed(speed_msg.value)
            self.logger.debug(f"Updated speed: {speed_msg.value:.2f} knots")
        except Exception as e:
            self.logger.error(f"Error parsing speed: {e}")
    
    def _handle_course(self, payload: bytes, subject: str, source: str):
        """Handle course over ground messages."""
        try:
            course_msg = TimestampedFloat()
            course_msg.ParseFromString(payload)
            self.formatter.update_course(course_msg.value)
            self.logger.debug(f"Updated course: {course_msg.value:.2f} degrees")
        except Exception as e:
            self.logger.error(f"Error parsing course: {e}")
    
    def _handle_satellites_used(self, payload: bytes, subject: str, source: str):
        """Handle satellites used messages."""
        try:
            sat_msg = TimestampedInt()
            sat_msg.ParseFromString(payload)
            self.formatter.update_satellites_used(sat_msg.value)
            self.logger.debug(f"Updated satellites used: {sat_msg.value}")
        except Exception as e:
            self.logger.error(f"Error parsing satellites used: {e}")
    
    def _handle_hdop(self, payload: bytes, subject: str, source: str):
        """Handle HDOP messages."""
        try:
            hdop_msg = TimestampedFloat()
            hdop_msg.ParseFromString(payload)
            self.formatter.update_hdop(hdop_msg.value)
            self.logger.debug(f"Updated HDOP: {hdop_msg.value:.2f}")
        except Exception as e:
            self.logger.error(f"Error parsing HDOP: {e}")
    
    def _handle_heading_true(self, payload: bytes, subject: str, source: str):
        """Handle true heading messages."""
        try:
            heading_msg = TimestampedFloat()
            heading_msg.ParseFromString(payload)
            self.formatter.update_heading(heading_msg.value)
            self.logger.debug(f"Updated true heading: {heading_msg.value:.2f} degrees")
        except Exception as e:
            self.logger.error(f"Error parsing true heading: {e}")
    
    def _handle_heading_magnetic(self, payload: bytes, subject: str, source: str):
        """Handle magnetic heading messages."""
        try:
            heading_msg = TimestampedFloat()
            heading_msg.ParseFromString(payload)
            # For now, treat magnetic heading same as true heading
            self.formatter.update_heading(heading_msg.value)
            self.logger.debug(f"Updated magnetic heading: {heading_msg.value:.2f} degrees")
        except Exception as e:
            self.logger.error(f"Error parsing magnetic heading: {e}")
    
    def _handle_roll(self, payload: bytes, subject: str, source: str):
        """Handle roll messages."""
        try:
            roll_msg = TimestampedFloat()
            roll_msg.ParseFromString(payload)
            self.formatter.update_attitude(roll_deg=roll_msg.value)
            self.logger.debug(f"Updated roll: {roll_msg.value:.2f} degrees")
        except Exception as e:
            self.logger.error(f"Error parsing roll: {e}")
    
    def _handle_pitch(self, payload: bytes, subject: str, source: str):
        """Handle pitch messages."""
        try:
            pitch_msg = TimestampedFloat()
            pitch_msg.ParseFromString(payload)
            self.formatter.update_attitude(pitch_deg=pitch_msg.value)
            self.logger.debug(f"Updated pitch: {pitch_msg.value:.2f} degrees")
        except Exception as e:
            self.logger.error(f"Error parsing pitch: {e}")
    
    def _handle_heave(self, payload: bytes, subject: str, source: str):
        """Handle heave messages."""
        try:
            heave_msg = TimestampedFloat()
            heave_msg.ParseFromString(payload)
            self.formatter.update_attitude(heave_m=heave_msg.value)
            self.logger.debug(f"Updated heave: {heave_msg.value:.2f} meters")
        except Exception as e:
            self.logger.error(f"Error parsing heave: {e}")
    
    def _handle_yaw_rate(self, payload: bytes, subject: str, source: str):
        """Handle yaw rate (rate of turn) messages."""
        try:
            yaw_rate_msg = TimestampedFloat()
            yaw_rate_msg.ParseFromString(payload)
            # Convert from degrees per second to degrees per minute for NMEA ROT
            rot_deg_per_min = yaw_rate_msg.value * 60.0
            self.formatter.update_rot(rot_deg_per_min)
            self.logger.debug(f"Updated yaw rate: {yaw_rate_msg.value:.2f} deg/s ({rot_deg_per_min:.2f} deg/min)")
        except Exception as e:
            self.logger.error(f"Error parsing yaw rate: {e}")
    
    def _handle_timestamp(self, payload: bytes, subject: str, source: str):
        """Handle timestamp messages."""
        try:
            timestamp_msg = TimestampedTimestamp()
            timestamp_msg.ParseFromString(payload)
            # Could use this for ZDA messages or time synchronization
            self.logger.debug(f"Received timestamp update")
        except Exception as e:
            self.logger.error(f"Error parsing timestamp: {e}")
    
    def _maybe_generate_nmea(self):
        """Generate NMEA sentences if enough time has passed."""
        current_time = time.time()
        if current_time - self._last_output_time >= self._output_interval:
            self._generate_nmea_sentences()
            self._last_output_time = current_time
    
    def _generate_nmea_sentences(self):
        """Generate and send configured NMEA sentences."""
        sentences = []
        
        # Generate requested NMEA sentences
        if "GGA" in self.config.nmea_sentences:
            sentence = self.formatter.generate_gga_sentence(self.config.talker_id)
            if sentence:
                sentences.append(sentence)
        
        if "RMC" in self.config.nmea_sentences:
            sentence = self.formatter.generate_rmc_sentence(self.config.talker_id)
            if sentence:
                sentences.append(sentence)
        
        if "VTG" in self.config.nmea_sentences:
            sentence = self.formatter.generate_vtg_sentence(self.config.talker_id)
            if sentence:
                sentences.append(sentence)
        
        if "ROT" in self.config.nmea_sentences:
            sentence = self.formatter.generate_rot_sentence(self.config.talker_id)
            if sentence:
                sentences.append(sentence)
        
        if "HDT" in self.config.nmea_sentences:
            sentence = self.formatter.generate_hdt_sentence(self.config.talker_id)
            if sentence:
                sentences.append(sentence)
        
        if "PASHR" in self.config.nmea_sentences:
            sentence = self.formatter.generate_pashr_sentence()
            if sentence:
                sentences.append(sentence)
        
        if "ZDA" in self.config.nmea_sentences:
            sentence = self.formatter.generate_zda_sentence(self.config.talker_id)
            if sentence:
                sentences.append(sentence)
        
        # Send sentences via output adapters
        for sentence in sentences:
            try:
                self.output_adapter.send_nmea(sentence)
                self.logger.debug(f"Sent NMEA: {sentence.strip()}")
            except Exception as e:
                self.logger.error(f"Error sending NMEA sentence: {e}")
        
        if sentences:
            self.logger.debug(f"Generated and sent {len(sentences)} NMEA sentences")


def create_subscription_config(realm: str, entity_id: str, 
                             source_patterns: Optional[List[str]] = None,
                             subjects: Optional[Set[str]] = None,
                             nmea_sentences: Optional[Set[str]] = None,
                             update_rate_hz: float = 1.0,
                             talker_id: str = "GP") -> SubscriptionConfig:
    """Create a subscription configuration with sensible defaults."""
    
    if source_patterns is None:
        source_patterns = ["**"]  # Subscribe to all sources
    
    if subjects is None:
        subjects = {
            "location_fix",
            "speed_over_ground_knots", 
            "course_over_ground_deg",
            "location_fix_satellites_used",
            "location_fix_hdop",
            "heading_true_north_deg",
            "roll_deg",
            "pitch_deg", 
            "heave_m",
            "yaw_rate_degps"
        }
    
    if nmea_sentences is None:
        nmea_sentences = {"GGA", "RMC", "VTG", "HDT"}  # Common NMEA sentences
    
    return SubscriptionConfig(
        realm=realm,
        entity_id=entity_id,
        source_patterns=source_patterns,
        subjects=subjects,
        nmea_sentences=nmea_sentences,
        update_rate_hz=update_rate_hz,
        talker_id=talker_id
    )