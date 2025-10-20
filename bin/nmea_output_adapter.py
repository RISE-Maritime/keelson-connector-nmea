#!/usr/bin/env python3

"""
NMEA Output Adapter Module

This module handles sending NMEA sentences via various transport methods:
- UDP unicast/broadcast
- TCP client
- Serial port
- UDP multicast
- SOCAT processes for complex configurations
"""

import asyncio
import socket
import subprocess
import logging
import threading
import queue
from typing import Optional, List, Dict, Any, Union
from enum import Enum
from dataclasses import dataclass

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    serial = None


class OutputType(Enum):
    """Supported output transport types."""
    UDP = "udp"
    TCP = "tcp" 
    SERIAL = "serial"
    MULTICAST = "multicast"
    SOCAT = "socat"


@dataclass
class OutputConfig:
    """Configuration for NMEA output."""
    output_type: OutputType
    host: Optional[str] = None
    port: Optional[int] = None
    device: Optional[str] = None  # For serial
    baudrate: Optional[int] = None  # For serial
    multicast_group: Optional[str] = None
    interface: Optional[str] = None
    socat_command: Optional[str] = None
    enabled: bool = True


class NmeaOutputAdapter:
    """
    Handles NMEA sentence output via various transport methods.
    """
    
    def __init__(self, config: OutputConfig):
        self.config = config
        self.logger = logging.getLogger(f"NmeaOutput-{config.output_type.value}")
        self._running = False
        self._message_queue = queue.Queue(maxsize=1000)
        self._worker_thread = None
        
        # Transport-specific objects
        self._socket = None
        self._serial = None
        self._socat_process = None
        
    async def start(self):
        """Start the output adapter."""
        if not self.config.enabled:
            self.logger.info("Output adapter disabled in config")
            return
            
        try:
            await self._initialize_transport()
            self._running = True
            self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self._worker_thread.start()
            self.logger.info(f"NMEA output adapter started for {self.config.output_type.value}")
        except Exception as e:
            self.logger.error(f"Failed to start output adapter: {e}")
            raise
    
    async def stop(self):
        """Stop the output adapter."""
        self._running = False
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5.0)
        await self._cleanup_transport()
        self.logger.info("NMEA output adapter stopped")
    
    def send_nmea(self, sentence: str):
        """Send an NMEA sentence (non-blocking)."""
        if not self._running:
            return
            
        try:
            # Add newline if not present
            if not sentence.endswith('\n'):
                sentence += '\n'
            self._message_queue.put_nowait(sentence.encode('utf-8'))
        except queue.Full:
            self.logger.warning("Output message queue full, dropping message")
    
    async def _initialize_transport(self):
        """Initialize the transport method."""
        if self.config.output_type == OutputType.UDP:
            await self._init_udp()
        elif self.config.output_type == OutputType.TCP:
            await self._init_tcp()
        elif self.config.output_type == OutputType.SERIAL:
            await self._init_serial()
        elif self.config.output_type == OutputType.MULTICAST:
            await self._init_multicast()
        elif self.config.output_type == OutputType.SOCAT:
            await self._init_socat()
        else:
            raise ValueError(f"Unsupported output type: {self.config.output_type}")
    
    async def _init_udp(self):
        """Initialize UDP socket."""
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if self.config.host is None or self.config.port is None:
            raise ValueError("UDP output requires host and port")
        
        # Enable broadcast if needed
        if self.config.host == "255.255.255.255" or self.config.host.endswith(".255"):
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        self.logger.info(f"UDP output configured for {self.config.host}:{self.config.port}")
    
    async def _init_tcp(self):
        """Initialize TCP client socket."""
        if self.config.host is None or self.config.port is None:
            raise ValueError("TCP output requires host and port")
            
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((self.config.host, self.config.port))
        self.logger.info(f"TCP output connected to {self.config.host}:{self.config.port}")
    
    async def _init_serial(self):
        """Initialize serial port."""
        if not SERIAL_AVAILABLE:
            raise ValueError("Serial output requires pyserial package: pip install pyserial")
        if self.config.device is None:
            raise ValueError("Serial output requires device path")
            
        baudrate = self.config.baudrate or 115200
        self._serial = serial.Serial(  # type: ignore
            port=self.config.device,
            baudrate=baudrate,
            timeout=1.0
        )
        self.logger.info(f"Serial output configured for {self.config.device} at {baudrate} baud")
    
    async def _init_multicast(self):
        """Initialize UDP multicast socket."""
        if self.config.multicast_group is None or self.config.port is None:
            raise ValueError("Multicast output requires multicast_group and port")
            
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Set TTL for multicast
        self._socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        
        # Bind to specific interface if specified
        if self.config.interface:
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, 
                                  self.config.interface.encode())
        
        self.logger.info(f"Multicast output configured for {self.config.multicast_group}:{self.config.port}")
    
    async def _init_socat(self):
        """Initialize SOCAT process."""
        if self.config.socat_command is None:
            raise ValueError("SOCAT output requires socat_command")
        
        # Start socat process
        self._socat_process = subprocess.Popen(
            self.config.socat_command,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False
        )
        self.logger.info(f"SOCAT process started: {self.config.socat_command}")
    
    async def _cleanup_transport(self):
        """Clean up transport resources."""
        if self._socket:
            self._socket.close()
            self._socket = None
            
        if self._serial:
            self._serial.close()
            self._serial = None
            
        if self._socat_process:
            try:
                self._socat_process.terminate()
                self._socat_process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                self._socat_process.kill()
                self._socat_process.wait()
            self._socat_process = None
    
    def _worker_loop(self):
        """Worker thread loop for sending messages."""
        while self._running:
            try:
                # Get message with timeout
                try:
                    message = self._message_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Send via configured transport
                success = self._send_message(message)
                if not success:
                    self.logger.warning("Failed to send NMEA message")
                    
            except Exception as e:
                self.logger.error(f"Error in worker loop: {e}")
    
    def _send_message(self, message: bytes) -> bool:
        """Send message via configured transport."""
        try:
            if self.config.output_type == OutputType.UDP:
                if self._socket and self.config.host and self.config.port:
                    self._socket.sendto(message, (self.config.host, self.config.port))
            elif self.config.output_type == OutputType.TCP:
                if self._socket:
                    self._socket.sendall(message)
            elif self.config.output_type == OutputType.SERIAL:
                if self._serial:
                    self._serial.write(message)
                    self._serial.flush()
            elif self.config.output_type == OutputType.MULTICAST:
                if self._socket and self.config.multicast_group and self.config.port:
                    self._socket.sendto(message, (self.config.multicast_group, self.config.port))
            elif self.config.output_type == OutputType.SOCAT:
                if self._socat_process and self._socat_process.stdin:
                    self._socat_process.stdin.write(message)
                    self._socat_process.stdin.flush()
                else:
                    return False
            else:
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Transport error: {e}")
            return False


class MultiOutputAdapter:
    """
    Manages multiple NMEA output adapters simultaneously.
    """
    
    def __init__(self, configs: List[OutputConfig]):
        self.configs = configs
        self.adapters: List[NmeaOutputAdapter] = []
        self.logger = logging.getLogger("MultiNmeaOutput")
    
    async def start(self):
        """Start all configured output adapters."""
        for config in self.configs:
            if config.enabled:
                adapter = NmeaOutputAdapter(config)
                try:
                    await adapter.start()
                    self.adapters.append(adapter)
                except Exception as e:
                    self.logger.error(f"Failed to start adapter {config.output_type.value}: {e}")
        
        self.logger.info(f"Started {len(self.adapters)} NMEA output adapters")
    
    async def stop(self):
        """Stop all output adapters."""
        for adapter in self.adapters:
            try:
                await adapter.stop()
            except Exception as e:
                self.logger.error(f"Error stopping adapter: {e}")
        
        self.adapters.clear()
        self.logger.info("All NMEA output adapters stopped")
    
    def send_nmea(self, sentence: str):
        """Send NMEA sentence to all active adapters."""
        for adapter in self.adapters:
            try:
                adapter.send_nmea(sentence)
            except Exception as e:
                self.logger.error(f"Error sending to adapter: {e}")
    
    def get_active_adapters(self) -> int:
        """Get count of active adapters."""
        return len(self.adapters)


# Convenience functions for creating common configurations

def create_udp_config(host: str, port: int, enabled: bool = True) -> OutputConfig:
    """Create UDP output configuration."""
    return OutputConfig(
        output_type=OutputType.UDP,
        host=host,
        port=port,
        enabled=enabled
    )


def create_tcp_config(host: str, port: int, enabled: bool = True) -> OutputConfig:
    """Create TCP output configuration."""
    return OutputConfig(
        output_type=OutputType.TCP,
        host=host,
        port=port,
        enabled=enabled
    )


def create_serial_config(device: str, baudrate: int = 115200, enabled: bool = True) -> OutputConfig:
    """Create serial output configuration."""
    return OutputConfig(
        output_type=OutputType.SERIAL,
        device=device,
        baudrate=baudrate,
        enabled=enabled
    )


def create_multicast_config(group: str, port: int, interface: Optional[str] = None, enabled: bool = True) -> OutputConfig:
    """Create multicast output configuration."""
    return OutputConfig(
        output_type=OutputType.MULTICAST,
        multicast_group=group,
        port=port,
        interface=interface,
        enabled=enabled
    )


def create_socat_config(command: str, enabled: bool = True) -> OutputConfig:
    """Create SOCAT output configuration."""
    return OutputConfig(
        output_type=OutputType.SOCAT,
        socat_command=command,
        enabled=enabled
    )