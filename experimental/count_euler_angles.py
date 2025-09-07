#!/usr/bin/env python3
"""
Simple script to count Euler angles publishing rate by filtering Zenoh samples.
This script focuses only on attitude data (heading, pitch, roll) and provides
a clean Hz measurement without verbose logging.
"""

import sys
import time
import argparse
import threading
from collections import defaultdict, deque
import zenoh

def create_arg_parser():
    parser = argparse.ArgumentParser(description="Count Euler angles publishing rate from ANavS connector")
    parser.add_argument("-e", "--entity", required=True, help="Entity name to monitor")
    parser.add_argument("-d", "--duration", type=int, default=10, help="Monitoring duration in seconds")
    return parser

class EulerAngleCounter:
    def __init__(self, entity_name):
        self.entity_name = entity_name
        self.counts = defaultdict(int)
        self.timestamps = defaultdict(lambda: deque(maxlen=1000))
        self.start_time = None
        self.running = False
        self.lock = threading.Lock()
        
        # Subscribe to attitude topics
        self.attitude_topics = [
            f"test_vessel/{entity_name}/attitude_heading",
            f"test_vessel/{entity_name}/attitude_pitch", 
            f"test_vessel/{entity_name}/attitude_roll"
        ]
        
    def sample_callback(self, sample):
        """Handle incoming Zenoh samples"""
        current_time = time.time()
        
        with self.lock:
            if not self.running:
                return
                
            # Extract topic name from key expression
            key_expr = str(sample.key_expr)
            
            # Check if this is an attitude topic
            for topic in self.attitude_topics:
                if topic in key_expr:
                    topic_short = topic.split('/')[-1]  # Get just the attitude type
                    self.counts[topic_short] += 1
                    self.timestamps[topic_short].append(current_time)
                    break
    
    def start_monitoring(self, duration):
        """Start monitoring for specified duration"""
        print(f"Starting Euler angles rate monitoring for entity '{self.entity_name}'...")
        print(f"Monitoring duration: {duration} seconds")
        print("Topics being monitored:")
        for topic in self.attitude_topics:
            print(f"  - {topic}")
        print()
        
        # Initialize Zenoh session
        config = zenoh.Config()
        session = zenoh.open(config)
        
        try:
        # Subscribe to all attitude topics with wildcard
        subscription_expr = f"test_vessel/{self.entity_name}/attitude_**"
        print(f"Subscribing to: {subscription_expr}")
        subscriber = session.declare_subscriber(subscription_expr, self.sample_callback)            # Start monitoring
            with self.lock:
                self.running = True
                self.start_time = time.time()
            
            print("Monitoring started... Press Ctrl+C to stop early\n")
            
            # Wait for specified duration
            try:
                time.sleep(duration)
            except KeyboardInterrupt:
                print("\nMonitoring interrupted by user")
            
            # Stop monitoring
            with self.lock:
                self.running = False
                end_time = time.time()
                actual_duration = end_time - self.start_time
            
            # Calculate and display results
            self.display_results(actual_duration)
            
        finally:
            session.close()
    
    def display_results(self, actual_duration):
        """Display monitoring results"""
        print(f"\n{'='*60}")
        print(f"EULER ANGLES PUBLISHING RATE ANALYSIS")
        print(f"{'='*60}")
        print(f"Entity: {self.entity_name}")
        print(f"Monitoring Duration: {actual_duration:.2f} seconds")
        print()
        
        total_euler_messages = 0
        
        print("Individual Angle Rates:")
        print("-" * 40)
        for angle_type in ['attitude_heading', 'attitude_pitch', 'attitude_roll']:
            count = self.counts.get(angle_type, 0)
            rate = count / actual_duration if actual_duration > 0 else 0
            total_euler_messages += count
            
            print(f"{angle_type:>16}: {count:>6} messages ({rate:>7.2f} Hz)")
            
            # Show recent rate if we have enough samples
            timestamps = self.timestamps.get(angle_type, deque())
            if len(timestamps) >= 10:
                recent_times = list(timestamps)[-10:]
                if len(recent_times) > 1:
                    recent_duration = recent_times[-1] - recent_times[0]
                    recent_rate = (len(recent_times) - 1) / recent_duration if recent_duration > 0 else 0
                    print(f"{' '*16}   Recent rate: {recent_rate:.2f} Hz (last 10 samples)")
        
        print("-" * 40)
        total_rate = total_euler_messages / actual_duration if actual_duration > 0 else 0
        print(f"{'TOTAL EULER':>16}: {total_euler_messages:>6} messages ({total_rate:>7.2f} Hz)")
        
        # Expected vs actual analysis
        expected_per_angle = 1000  # 1 kHz per angle
        expected_total = expected_per_angle * 3
        
        print("\nPerformance Analysis:")
        print("-" * 40)
        for angle_type in ['attitude_heading', 'attitude_pitch', 'attitude_roll']:
            count = self.counts.get(angle_type, 0)
            rate = count / actual_duration if actual_duration > 0 else 0
            efficiency = (rate / expected_per_angle) * 100 if expected_per_angle > 0 else 0
            print(f"{angle_type:>16}: {efficiency:>6.1f}% of expected 1000 Hz")
        
        total_efficiency = (total_rate / expected_total) * 100 if expected_total > 0 else 0
        print(f"{'OVERALL':>16}: {total_efficiency:>6.1f}% of expected 3000 Hz")
        
        print("\nSummary:")
        print("-" * 40)
        print(f"• ANavS connector is publishing Euler angles at {total_rate:.1f} Hz total")
        print(f"• Individual angle rates: ~{total_rate/3:.1f} Hz per angle")
        print(f"• This represents {total_efficiency:.1f}% of theoretical maximum (1000 Hz per angle)")
        
        if total_rate > 2500:
            print("✓ Excellent: Very high rate, suitable for high-frequency applications")
        elif total_rate > 1500:
            print("✓ Good: High rate, suitable for most maritime applications")
        elif total_rate > 500:
            print("⚠ Moderate: Adequate for basic navigation applications")
        else:
            print("⚠ Low: May need investigation for performance optimization")

def main():
    parser = create_arg_parser()
    args = parser.parse_args()
    
    counter = EulerAngleCounter(args.entity)
    counter.start_monitoring(args.duration)

if __name__ == "__main__":
    main()
