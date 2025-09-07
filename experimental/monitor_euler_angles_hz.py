#!/usr/bin/env python3
"""
Count ANavS Connector Euler Angles Publishing Rate in Hz

This script monitors the Keelson/Zenoh topics for attitude (Euler angles) 
published by the ANavS connector and measures the publishing rate in Hz.
"""

import zenoh
import json
import time
import logging
from datetime import datetime
from collections import defaultdict
import sys

def monitor_euler_angles_hz(realm="rise", entity_id=None, source_id="anavs/0", duration=10):
    """
    Monitor the publishing rate of Euler angles from ANavS connector
    
    Args:
        realm: Zenoh realm (default: "rise")
        entity_id: Entity ID to monitor
        source_id: Source ID to monitor (default: "anavs/0")
        duration: Monitoring duration in seconds
    """
    
    print(f"=== ANavS Euler Angles Publishing Rate Monitor ===")
    print(f"Realm: {realm}")
    print(f"Entity ID: {entity_id}")
    print(f"Source ID: {source_id}")
    print(f"Duration: {duration} seconds")
    print(f"Monitoring topics:")
    print(f"  - attitude_heading")
    print(f"  - attitude_pitch") 
    print(f"  - attitude_roll")
    print()
    
    # Message counters for each angle
    message_counts = {
        'heading': 0,
        'pitch': 0,
        'roll': 0
    }
    
    # Timing data
    start_time = time.time()
    last_update = start_time
    message_times = defaultdict(list)
    
    # Configure Zenoh
    conf = zenoh.Config()
    
    with zenoh.open(conf) as session:
        print(f"✅ Zenoh session opened")
        
        # Construct key expressions for attitude topics
        if entity_id:
            key_patterns = {
                'heading': f"{realm}/{entity_id}/attitude_heading/{source_id}/binary",
                'pitch': f"{realm}/{entity_id}/attitude_pitch/{source_id}/binary", 
                'roll': f"{realm}/{entity_id}/attitude_roll/{source_id}/binary"
            }
        else:
            # Use wildcards if no entity_id specified
            key_patterns = {
                'heading': f"{realm}/*/attitude_heading/{source_id}/binary",
                'pitch': f"{realm}/*/attitude_pitch/{source_id}/binary",
                'roll': f"{realm}/*/attitude_roll/{source_id}/binary"
            }
        
        print("📡 Subscribing to attitude topics:")
        for angle, pattern in key_patterns.items():
            print(f"  {angle}: {pattern}")
        
        # Callback function to count messages
        def attitude_callback(angle_type):
            def callback(sample):
                current_time = time.time()
                message_counts[angle_type] += 1
                message_times[angle_type].append(current_time)
                
                # Print periodic updates
                nonlocal last_update
                if current_time - last_update >= 1.0:
                    elapsed = current_time - start_time
                    rates = {}
                    for angle in ['heading', 'pitch', 'roll']:
                        count = message_counts[angle]
                        rate = count / elapsed if elapsed > 0 else 0
                        rates[angle] = rate
                    
                    print(f"{elapsed:6.1f}s | H:{rates['heading']:6.1f} Hz | P:{rates['pitch']:6.1f} Hz | R:{rates['roll']:6.1f} Hz | "
                          f"Total: H:{message_counts['heading']:5d} P:{message_counts['pitch']:5d} R:{message_counts['roll']:5d}")
                    last_update = current_time
                    
            return callback
        
        # Subscribe to each attitude topic
        subscribers = {}
        for angle, pattern in key_patterns.items():
            try:
                sub = session.declare_subscriber(pattern, attitude_callback(angle))
                subscribers[angle] = sub
                print(f"✅ Subscribed to {angle}: {pattern}")
            except Exception as e:
                print(f"❌ Failed to subscribe to {angle}: {e}")
        
        print(f"\n📊 Starting measurement at {datetime.now().strftime('%H:%M:%S')}")
        print("Time   | Heading Hz | Pitch Hz | Roll Hz | Message Counts")
        print("-" * 70)
        
        # Monitor for specified duration
        try:
            while True:
                current_time = time.time()
                elapsed = current_time - start_time
                
                if elapsed >= duration:
                    break
                    
                time.sleep(0.1)  # Small sleep to prevent busy waiting
                
        except KeyboardInterrupt:
            print(f"\n⏹️  Monitoring stopped by user")
        
        # Close subscribers
        for sub in subscribers.values():
            sub.undeclare()
    
    # Calculate final statistics
    end_time = time.time()
    total_duration = end_time - start_time
    
    print(f"\n=== Final Results ===")
    print(f"Monitoring duration: {total_duration:.2f} seconds")
    
    for angle in ['heading', 'pitch', 'roll']:
        count = message_counts[angle]
        avg_rate = count / total_duration if total_duration > 0 else 0
        print(f"{angle.capitalize():8} messages: {count:5d} | Average rate: {avg_rate:7.2f} Hz")
        
        # Calculate timing statistics
        times = message_times[angle]
        if len(times) > 1:
            intervals = []
            for i in range(1, len(times)):
                interval = times[i] - times[i-1]
                intervals.append(interval)
            
            if intervals:
                avg_interval = sum(intervals) / len(intervals)
                min_interval = min(intervals)
                max_interval = max(intervals)
                
                print(f"         Avg interval: {avg_interval*1000:.1f} ms ({1/avg_interval:.1f} Hz)")
                print(f"         Min interval: {min_interval*1000:.1f} ms ({1/min_interval:.1f} Hz)")
                print(f"         Max interval: {max_interval*1000:.1f} ms ({1/max_interval:.1f} Hz)")
                
                # Calculate jitter
                if len(intervals) > 2:
                    import statistics
                    jitter = statistics.stdev(intervals)
                    print(f"         Timing jitter: ±{jitter*1000:.2f} ms")
    
    # Overall statistics
    total_messages = sum(message_counts.values())
    overall_rate = total_messages / total_duration if total_duration > 0 else 0
    
    print(f"\n=== Overall Attitude Publishing Statistics ===")
    print(f"Total attitude messages: {total_messages}")
    print(f"Overall message rate: {overall_rate:.2f} Hz")
    print(f"Expected rate (3 topics × 1000 Hz): 3000 Hz")
    print(f"Efficiency: {(overall_rate/3000)*100:.1f}% of expected rate")
    
    return {
        'duration': total_duration,
        'message_counts': message_counts,
        'total_messages': total_messages,
        'overall_rate': overall_rate,
        'individual_rates': {angle: message_counts[angle]/total_duration for angle in message_counts}
    }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Monitor ANavS Euler angles publishing rate")
    parser.add_argument("-r", "--realm", default="rise", help="Zenoh realm")
    parser.add_argument("-e", "--entity-id", help="Entity ID to monitor")
    parser.add_argument("-s", "--source-id", default="anavs/0", help="Source ID to monitor")
    parser.add_argument("--duration", type=int, default=10, help="Monitoring duration in seconds")
    parser.add_argument("--log-level", type=int, default=30, help="Log level")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=args.log_level)
    
    if not args.entity_id:
        print("⚠️  No entity ID specified. Using wildcard pattern (may match multiple entities)")
        print("   For specific monitoring, use: -e <entity_id>")
        print()
    
    try:
        result = monitor_euler_angles_hz(
            realm=args.realm,
            entity_id=args.entity_id, 
            source_id=args.source_id,
            duration=args.duration
        )
        print(f"\n🏁 Monitoring complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
