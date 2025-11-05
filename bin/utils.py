#!/usr/bin/env python3

"""Shared utility functions for NMEA-Keelson connectors."""

import logging
from typing import Optional, Sequence, Any
from datetime import datetime, timezone

import keelson
from keelson.payloads.Primitives_pb2 import (
    TimestampedFloat,
    TimestampedInt,
    TimestampedString,
    TimestampedTimestamp,
)
from keelson.payloads.foxglove.LocationFix_pb2 import LocationFix
from google.protobuf.timestamp_pb2 import Timestamp

logger = logging.getLogger(__name__)


def get_first(items: Sequence) -> Optional[Any]:
    """Safely get the first item from a sequence, or None if empty."""
    return next(iter(items), None)


def unpack(sample):
    """
    Unpack a Keelson envelope and return the decoded payload.

    Args:
        sample: A skarv.Sample or zenoh sample containing Keelson envelope

    Returns:
        The decoded protobuf message (schema determined by subject context)
    """
    try:
        schema_id, schema_version, payload_bytes = keelson.uncover(sample.payload)
        return payload_bytes
    except Exception as e:
        logger.error(f"Failed to unpack sample: {e}")
        return None


def create_timestamp(dt: Optional[datetime] = None) -> Timestamp:
    """
    Create a protobuf Timestamp from a datetime object.

    Args:
        dt: datetime object (defaults to current UTC time if None)

    Returns:
        Google protobuf Timestamp
    """
    if dt is None:
        dt = datetime.now(timezone.utc)
    elif dt.tzinfo is None:
        # Assume UTC if no timezone specified
        dt = dt.replace(tzinfo=timezone.utc)

    timestamp = Timestamp()
    timestamp.FromDatetime(dt)
    return timestamp


def enclose_from_float(value: float, timestamp: Optional[datetime] = None) -> bytes:
    """
    Create a Keelson envelope containing a TimestampedFloat.

    Args:
        value: The float value to enclose
        timestamp: Optional datetime (defaults to current UTC time)

    Returns:
        Serialized Keelson envelope as bytes
    """
    msg = TimestampedFloat()
    msg.value = value
    msg.timestamp.CopyFrom(create_timestamp(timestamp))

    payload = msg.SerializeToString()
    return keelson.enclose(payload)


def enclose_from_int(value: int, timestamp: Optional[datetime] = None) -> bytes:
    """
    Create a Keelson envelope containing a TimestampedInt.

    Args:
        value: The integer value to enclose
        timestamp: Optional datetime (defaults to current UTC time)

    Returns:
        Serialized Keelson envelope as bytes
    """
    msg = TimestampedInt()
    msg.value = value
    msg.timestamp.CopyFrom(create_timestamp(timestamp))

    payload = msg.SerializeToString()
    return keelson.enclose(payload)


def enclose_from_string(value: str, timestamp: Optional[datetime] = None) -> bytes:
    """
    Create a Keelson envelope containing a TimestampedString.

    Args:
        value: The string value to enclose
        timestamp: Optional datetime (defaults to current UTC time)

    Returns:
        Serialized Keelson envelope as bytes
    """
    msg = TimestampedString()
    msg.value = value
    msg.timestamp.CopyFrom(create_timestamp(timestamp))

    payload = msg.SerializeToString()
    return keelson.enclose(payload)


def enclose_from_timestamp(dt: datetime) -> bytes:
    """
    Create a Keelson envelope containing a TimestampedTimestamp.

    Args:
        dt: The datetime to enclose

    Returns:
        Serialized Keelson envelope as bytes
    """
    msg = TimestampedTimestamp()
    msg.value.CopyFrom(create_timestamp(dt))
    msg.timestamp.CopyFrom(create_timestamp())  # Current time as metadata timestamp

    payload = msg.SerializeToString()
    return keelson.enclose(payload)


def enclose_from_location(
    latitude: float,
    longitude: float,
    altitude: Optional[float] = None,
    timestamp: Optional[datetime] = None
) -> bytes:
    """
    Create a Keelson envelope containing a LocationFix.

    Args:
        latitude: Latitude in decimal degrees
        longitude: Longitude in decimal degrees
        altitude: Optional altitude in meters
        timestamp: Optional datetime (defaults to current UTC time)

    Returns:
        Serialized Keelson envelope as bytes
    """
    msg = LocationFix()
    msg.latitude = latitude
    msg.longitude = longitude

    if altitude is not None:
        msg.altitude = altitude

    msg.timestamp.CopyFrom(create_timestamp(timestamp))

    payload = msg.SerializeToString()
    return keelson.enclose(payload)


def mirror(zenoh_session, zenoh_key: str, skarv_key: str):
    """
    Mirror a Zenoh topic to a skarv vault key.

    This function subscribes to a Zenoh key expression and stores
    all received samples in the skarv vault under the specified key.
    It also fetches the latest historical value if available.

    Args:
        zenoh_session: Active Zenoh session
        zenoh_key: Zenoh key expression to subscribe to
        skarv_key: Key to use in skarv vault for storing data
    """
    import skarv

    def callback(sample):
        skarv.put(skarv_key, sample)

    # Subscribe to future updates
    zenoh_session.declare_subscriber(zenoh_key, callback)

    # Fetch historical value if available
    try:
        replies = zenoh_session.get(zenoh_key)
        for reply in replies:
            if reply.ok:
                skarv.put(skarv_key, reply.ok)
                logger.debug(f"Fetched historical value for {skarv_key}")
    except Exception as e:
        logger.debug(f"No historical value for {skarv_key}: {e}")
