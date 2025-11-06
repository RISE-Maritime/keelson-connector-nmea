#!/usr/bin/env python3

"""Shared utility functions for NMEA-Keelson connectors."""

import logging
import time

from keelson import enclose
from keelson.payloads.Primitives_pb2 import (
    TimestampedFloat,
    TimestampedInt,
    TimestampedString,
    TimestampedBytes,
    TimestampedTimestamp,
)
from keelson.payloads.foxglove.LocationFix_pb2 import LocationFix
from google.protobuf.timestamp_pb2 import Timestamp

logger = logging.getLogger(__name__)


def enclose_from_bytes(value: bytes, timestamp: int = None) -> bytes:
    payload = TimestampedBytes()
    payload.timestamp.FromNanoseconds(timestamp or time.time_ns())
    payload.value = value

    return enclose(payload.SerializeToString())


def enclose_from_integer(value: int, timestamp: int = None) -> bytes:
    payload = TimestampedInt()
    payload.timestamp.FromNanoseconds(timestamp or time.time_ns())
    payload.value = value

    return enclose(payload.SerializeToString())


def enclose_from_float(value: float, timestamp: int = None) -> bytes:
    payload = TimestampedFloat()
    payload.timestamp.FromNanoseconds(timestamp or time.time_ns())
    payload.value = value

    return enclose(payload.SerializeToString())


def enclose_from_string(value: str, timestamp: int = None) -> bytes:
    payload = TimestampedString()
    payload.timestamp.FromNanoseconds(timestamp or time.time_ns())
    payload.value = value

    return enclose(payload.SerializeToString())


def enclose_from_lon_lat(
    longitude: float, latitude: float, timestamp: int = None
) -> bytes:
    payload = LocationFix()
    payload.timestamp.FromNanoseconds(timestamp or time.time_ns())
    payload.latitude = latitude
    payload.longitude = longitude

    return enclose(payload.SerializeToString())


def enclose_from_timestamp(value: int, timestamp: int = None) -> bytes:
    payload = TimestampedTimestamp()
    payload.timestamp.FromNanoseconds(timestamp or time.time_ns())
    payload.value.FromNanoseconds(value)

    return enclose(payload.SerializeToString())
