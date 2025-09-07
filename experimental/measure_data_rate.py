#!/usr/bin/env python3
"""
Measure ANavS binary data output rate in Hz

This script connects to the ANavS device and measures the actual data output rate
by counting messages received over a time period.
"""

import sys
import socket
import time
import struct
from datetime import datetime
import logging

# Add parent directory to import our modules
sys.path.append('/home/sealog/keelson-connector-nmea/experimental')
from anavs_connector import parse_anavs_binary, SYNC_CHAR_1, SYNC_CHAR_2

def measure_anavs_data_rate(host='192.168.1.124', port=6001, measurement_duration=10):
    """
    Measure the data rate from ANavS device
    
    Args:
        host: ANavS device IP address
        port: ANavS device port
        measurement_duration: How long to measure in seconds
    
    Returns:
        dict with measurement results
    """
    
    print(f"=== ANavS Binary Data Rate Measurement ===")
    print(f"Connecting to {host}:{port}")
    print(f"Measurement duration: {measurement_duration} seconds")
    print(f"Press Ctrl+C to stop early...\n")
    
    try:
        # Connect to ANavS device
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5.0)  # 5 second timeout
        sock.connect((host, port))
        print(f"✅ Connected to ANavS device at {host}:{port}")
        
        # Measurement variables
        message_count = 0
        total_bytes = 0
        data_buffer = b''
        start_time = time.time()
        last_update = start_time
        message_times = []
        
        print(f"📊 Starting measurement at {datetime.now().strftime('%H:%M:%S')}")
        print("Time    | Messages | Rate (Hz) | Bytes/sec | Last Message")
        print("-" * 65)
        
        while True:
            current_time = time.time()
            elapsed = current_time - start_time
            
            # Check if measurement duration reached
            if elapsed >= measurement_duration:
                break
                
            # Read data from socket
            try:
                data = sock.recv(1024)
                if not data:
                    print("Connection closed by device")
                    break
                    
                data_buffer += data
                total_bytes += len(data)
                
                # Parse messages from buffer
                while True:
                    consumed, messages = parse_anavs_binary(data_buffer)
                    
                    if not messages:
                        break  # No complete messages
                        
                    # Process each message
                    for msg in messages:
                        message_count += 1
                        message_times.append(current_time)
                        
                        # Print periodic updates
                        if current_time - last_update >= 1.0:  # Update every second
                            rate_hz = message_count / elapsed if elapsed > 0 else 0
                            bytes_per_sec = total_bytes / elapsed if elapsed > 0 else 0
                            
                            print(f"{elapsed:6.1f}s | {message_count:8d} | {rate_hz:7.2f} | {bytes_per_sec:8.1f} | "
                                  f"GPS Week {msg.get('week', 'N/A')}, TOW {msg.get('tow', 0):.3f}")
                            last_update = current_time
                    
                    # Remove consumed bytes
                    data_buffer = data_buffer[consumed:]
                    
            except socket.timeout:
                continue
            except KeyboardInterrupt:
                print(f"\n⏹️  Measurement stopped by user")
                break
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return None
    finally:
        if 'sock' in locals():
            sock.close()
    
    # Calculate final statistics
    end_time = time.time()
    total_duration = end_time - start_time
    
    print(f"\n=== Measurement Results ===")
    print(f"Duration: {total_duration:.2f} seconds")
    print(f"Total messages: {message_count}")
    print(f"Total bytes: {total_bytes}")
    print(f"Average data rate: {message_count / total_duration:.2f} Hz")
    print(f"Average throughput: {total_bytes / total_duration:.1f} bytes/sec")
    
    # Calculate message interval statistics
    if len(message_times) > 1:
        intervals = []
        for i in range(1, len(message_times)):
            interval = message_times[i] - message_times[i-1]
            intervals.append(interval)
        
        avg_interval = sum(intervals) / len(intervals)
        min_interval = min(intervals)
        max_interval = max(intervals)
        
        print(f"\n=== Message Timing Analysis ===")
        print(f"Average interval: {avg_interval*1000:.1f} ms ({1/avg_interval:.2f} Hz)")
        if min_interval > 0:
            print(f"Minimum interval: {min_interval*1000:.1f} ms ({1/min_interval:.2f} Hz)")
        else:
            print(f"Minimum interval: {min_interval*1000:.1f} ms (instantaneous)")
        if max_interval > 0:
            print(f"Maximum interval: {max_interval*1000:.1f} ms ({1/max_interval:.2f} Hz)")
        else:
            print(f"Maximum interval: {max_interval*1000:.1f} ms")
        
        # Check for common update rates
        common_rates = [1, 2, 5, 10, 20, 50, 100]
        detected_rate = 1 / avg_interval
        closest_rate = min(common_rates, key=lambda x: abs(x - detected_rate))
        
        print(f"Detected rate: {detected_rate:.2f} Hz")
        print(f"Closest standard rate: {closest_rate} Hz")
        
        # Jitter analysis
        if len(intervals) > 2:
            import statistics
            jitter = statistics.stdev(intervals)
            print(f"Timing jitter: ±{jitter*1000:.2f} ms")
    
    return {
        'duration': total_duration,
        'message_count': message_count,
        'rate_hz': message_count / total_duration,
        'bytes_per_sec': total_bytes / total_duration,
        'total_bytes': total_bytes
    }

def measure_via_stdin(measurement_duration=10):
    """
    Measure data rate from stdin (when using socat)
    """
    print(f"=== ANavS Binary Data Rate Measurement (stdin) ===")
    print(f"Reading from stdin (use with: socat TCP:192.168.1.124:6001 STDOUT | python3 measure_data_rate.py --stdin)")
    print(f"Measurement duration: {measurement_duration} seconds")
    print(f"Press Ctrl+C to stop early...\n")
    
    message_count = 0
    total_bytes = 0
    data_buffer = b''
    start_time = time.time()
    last_update = start_time
    message_times = []
    
    print(f"📊 Starting measurement at {datetime.now().strftime('%H:%M:%S')}")
    print("Time    | Messages | Rate (Hz) | Bytes/sec | Last Message")
    print("-" * 65)
    
    try:
        while True:
            current_time = time.time()
            elapsed = current_time - start_time
            
            if elapsed >= measurement_duration:
                break
                
            # Read from stdin
            data = sys.stdin.buffer.read(1024)
            if not data:
                break
                
            data_buffer += data
            total_bytes += len(data)
            
            # Parse messages
            while True:
                consumed, messages = parse_anavs_binary(data_buffer)
                
                if not messages:
                    break
                    
                for msg in messages:
                    message_count += 1
                    message_times.append(current_time)
                    
                    if current_time - last_update >= 1.0:
                        rate_hz = message_count / elapsed if elapsed > 0 else 0
                        bytes_per_sec = total_bytes / elapsed if elapsed > 0 else 0
                        
                        print(f"{elapsed:6.1f}s | {message_count:8d} | {rate_hz:7.2f} | {bytes_per_sec:8.1f} | "
                              f"GPS Week {msg.get('week', 'N/A')}, TOW {msg.get('tow', 0):.3f}")
                        last_update = current_time
                
                data_buffer = data_buffer[consumed:]
                
    except KeyboardInterrupt:
        print(f"\n⏹️  Measurement stopped by user")
    
    end_time = time.time()
    total_duration = end_time - start_time
    
    print(f"\n=== Final Results ===")
    print(f"Messages received: {message_count}")
    print(f"Average rate: {message_count / total_duration:.2f} Hz")
    print(f"Total bytes: {total_bytes}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Measure ANavS binary data output rate")
    parser.add_argument("--host", default="192.168.1.124", help="ANavS device IP address")
    parser.add_argument("--port", type=int, default=6001, help="ANavS device port")
    parser.add_argument("--duration", type=int, default=10, help="Measurement duration in seconds")
    parser.add_argument("--stdin", action="store_true", help="Read from stdin instead of TCP")
    
    args = parser.parse_args()
    
    if args.stdin:
        measure_via_stdin(args.duration)
    else:
        result = measure_anavs_data_rate(args.host, args.port, args.duration)
        
    print(f"\n🏁 Measurement complete!")
