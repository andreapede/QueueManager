"""
Sensor Controller for Queue Management System
Handles PIR motion sensor and Ultrasonic distance sensor
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging

try:
    import RPi.GPIO as GPIO
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    GPIO = None

from config.config import Config

class SensorController:
    """Manages PIR and Ultrasonic sensors"""
    
    def __init__(self, simulation_mode: bool = False):
        self.logger = logging.getLogger(__name__)
        self.simulation_mode = simulation_mode
        
        # GPIO pins from config
        self.pir_pin = Config.GPIO.PIR_SENSOR
        self.trig_pin = Config.GPIO.ULTRASONIC_TRIG
        self.echo_pin = Config.GPIO.ULTRASONIC_ECHO
        
        # Sensor state
        self.initialized = False
        self.pir_movement = False
        self.ultrasonic_distance = 999  # cm
        self.last_movement_time = None
        self.presence_detected = False
        
        # Threading
        self.sensor_thread = None
        self.running = False
        self.lock = threading.Lock()
        
        # Simulation data
        self.sim_movement = False
        self.sim_distance = 250  # cm
        
        self.logger.info(f"SensorController initialized (simulation: {simulation_mode})")
    
    def initialize(self) -> bool:
        """Initialize sensors"""
        try:
            if not self.simulation_mode:
                self._setup_hardware_sensors()
            
            # Start sensor monitoring thread
            self.running = True
            self.sensor_thread = threading.Thread(target=self._sensor_loop, daemon=True)
            self.sensor_thread.start()
            
            self.initialized = True
            self.logger.info("Sensors initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize sensors: {e}")
            return False
    
    def _setup_hardware_sensors(self):
        """Setup hardware sensors GPIO"""
        if not GPIO:
            raise RuntimeError("GPIO not available")
        
        # PIR sensor setup
        GPIO.setup(self.pir_pin, GPIO.IN)
        
        # Ultrasonic sensor setup
        GPIO.setup(self.trig_pin, GPIO.OUT)
        GPIO.setup(self.echo_pin, GPIO.IN)
        
        # Initialize trigger to LOW
        GPIO.output(self.trig_pin, False)
        time.sleep(0.1)
        
        self.logger.info("Hardware sensors GPIO configured")
    
    def _sensor_loop(self):
        """Main sensor monitoring loop"""
        while self.running:
            try:
                if self.simulation_mode:
                    self._read_simulated_sensors()
                else:
                    self._read_hardware_sensors()
                
                # Update presence detection logic
                self._update_presence_logic()
                
                # Sleep based on config
                time.sleep(Config.ULTRASONIC_POLLING_SECONDS)
                
            except Exception as e:
                self.logger.error(f"Error in sensor loop: {e}")
                time.sleep(1)
    
    def _read_hardware_sensors(self):
        """Read actual hardware sensors"""
        with self.lock:
            # Read PIR sensor
            if Config.USE_PIR_SENSOR:
                self.pir_movement = GPIO.input(self.pir_pin) == GPIO.HIGH
                if self.pir_movement:
                    self.last_movement_time = datetime.now()
            
            # Read ultrasonic sensor
            if Config.USE_ULTRASONIC_SENSOR:
                self.ultrasonic_distance = self._measure_distance()
    
    def _read_simulated_sensors(self):
        """Read simulated sensor data"""
        with self.lock:
            # Simulate some movement occasionally
            if time.time() % 10 < 1:  # Movement every 10 seconds
                self.sim_movement = not self.sim_movement
                if self.sim_movement:
                    self.last_movement_time = datetime.now()
            
            self.pir_movement = self.sim_movement
            
            # Simulate distance changes
            self.ultrasonic_distance = self.sim_distance + (time.time() % 50)
    
    def _measure_distance(self) -> float:
        """Measure distance using ultrasonic sensor"""
        try:
            # Trigger pulse
            GPIO.output(self.trig_pin, True)
            time.sleep(0.00001)  # 10 microseconds
            GPIO.output(self.trig_pin, False)
            
            # Wait for echo start
            pulse_start = time.time()
            timeout_start = pulse_start
            while GPIO.input(self.echo_pin) == 0:
                pulse_start = time.time()
                if pulse_start - timeout_start > 0.1:  # 100ms timeout
                    return 999  # Return max distance on timeout
            
            # Wait for echo end
            pulse_end = time.time()
            timeout_end = pulse_end
            while GPIO.input(self.echo_pin) == 1:
                pulse_end = time.time()
                if pulse_end - timeout_end > 0.1:  # 100ms timeout
                    return 999
            
            # Calculate distance
            pulse_duration = pulse_end - pulse_start
            distance = pulse_duration * 17150  # Speed of sound / 2
            
            return min(distance, 999)  # Cap at 999cm
            
        except Exception as e:
            self.logger.error(f"Error measuring distance: {e}")
            return 999
    
    def _update_presence_logic(self):
        """Update presence detection based on sensor combination"""
        with self.lock:
            # Check if object is within presence threshold
            distance_presence = self.ultrasonic_distance < Config.PRESENCE_THRESHOLD_CM
            
            # Check if recent movement detected
            movement_presence = False
            if self.last_movement_time:
                time_since_movement = datetime.now() - self.last_movement_time
                movement_presence = time_since_movement.total_seconds() < (Config.MOVEMENT_TIMEOUT_MINUTES * 60)
            
            # Combine sensors based on configuration
            if Config.DUAL_SENSOR_MODE == 'AND':
                # Both sensors must agree
                self.presence_detected = distance_presence and (self.pir_movement or movement_presence)
            else:  # 'OR'
                # Either sensor can detect presence
                self.presence_detected = distance_presence or movement_presence
    
    def read_sensors(self) -> Dict[str, Any]:
        """Get current sensor readings"""
        with self.lock:
            return {
                'pir_movement': self.pir_movement,
                'ultrasonic_distance_cm': round(self.ultrasonic_distance, 1),
                'presence_detected': self.presence_detected,
                'last_movement_time': self.last_movement_time,
                'last_sensor_read': datetime.now(),
                'sensors_enabled': {
                    'pir': Config.USE_PIR_SENSOR,
                    'ultrasonic': Config.USE_ULTRASONIC_SENSOR
                },
                'sensor_mode': Config.DUAL_SENSOR_MODE
            }
    
    def get_presence_status(self) -> bool:
        """Get simple presence status"""
        with self.lock:
            return self.presence_detected
    
    def simulate_movement(self):
        """Simulate movement for testing"""
        if self.simulation_mode:
            with self.lock:
                self.sim_movement = True
                self.last_movement_time = datetime.now()
                self.logger.info("Simulated movement triggered")
    
    def simulate_presence(self, present: bool = True):
        """Simulate presence for testing"""
        if self.simulation_mode:
            with self.lock:
                self.sim_distance = 100 if present else 300  # Within/outside threshold
                self.logger.info(f"Simulated presence: {present}")
    
    def get_movement_time_ago(self) -> Optional[int]:
        """Get seconds since last movement"""
        if not self.last_movement_time:
            return None
        
        time_diff = datetime.now() - self.last_movement_time
        return int(time_diff.total_seconds())
    
    def is_movement_warning_needed(self) -> bool:
        """Check if movement warning should be shown"""
        time_ago = self.get_movement_time_ago()
        if time_ago is None:
            return False
        
        warning_seconds = Config.MOVEMENT_WARNING_MINUTES * 60
        return time_ago >= warning_seconds
    
    def cleanup(self):
        """Clean up sensor resources"""
        self.running = False
        
        if self.sensor_thread and self.sensor_thread.is_alive():
            self.sensor_thread.join(timeout=2)
        
        self.logger.info("Sensors cleanup complete")
