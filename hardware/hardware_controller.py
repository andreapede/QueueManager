"""
Main Hardware Controller for Queue Management System
Coordinates all hardware components
"""

import time
import threading
from datetime import datetime
from typing import Dict, Optional, Any
import logging

try:
    import RPi.GPIO as GPIO
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    GPIO = None

from config.config import Config
from .sensors import SensorController
from .display import DisplayController
from .leds import LEDController
from .buttons import ButtonController

class HardwareController:
    """Main hardware controller - coordinates all hardware components"""
    
    def __init__(self, simulation_mode: bool = None):
        self.logger = logging.getLogger(__name__)
        
        # Determine simulation mode
        self.simulation_mode = simulation_mode
        if self.simulation_mode is None:
            self.simulation_mode = not HARDWARE_AVAILABLE
        
        # Initialize component controllers
        self.sensors = SensorController(self.simulation_mode)
        self.display = DisplayController(self.simulation_mode)
        self.leds = LEDController(self.simulation_mode)
        self.buttons = ButtonController(self.simulation_mode)
        
        # Hardware state
        self.initialized = False
        self.sensor_thread = None
        self.running = False
        
        self.logger.info(f"HardwareController initialized (simulation_mode: {self.simulation_mode})")
    
    def initialize(self) -> bool:
        """Initialize all hardware components"""
        try:
            if not self.simulation_mode:
                self._setup_gpio()
            
            # Initialize all components
            if not self.sensors.initialize():
                self.logger.error("Failed to initialize sensors")
                return False
            
            if not self.display.initialize():
                self.logger.error("Failed to initialize display")
                return False
            
            if not self.leds.initialize():
                self.logger.error("Failed to initialize LEDs")
                return False
            
            if not self.buttons.initialize():
                self.logger.error("Failed to initialize buttons")
                return False
            
            self.initialized = True
            self.running = True
            
            # Start sensor monitoring thread
            self._start_sensor_monitoring()
            
            # Show initialization complete
            self.display.show_message("Sistema pronto", duration=2)
            
            self.logger.info("All hardware components initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize hardware: {e}")
            return False
    
    def _setup_gpio(self):
        """Setup GPIO for hardware mode"""
        if GPIO:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            self.logger.info("GPIO initialized")
    
    def _start_sensor_monitoring(self):
        """Start background sensor monitoring"""
        self.sensor_thread = threading.Thread(target=self._sensor_monitor_loop, daemon=True)
        self.sensor_thread.start()
        self.logger.info("Sensor monitoring thread started")
    
    def _sensor_monitor_loop(self):
        """Background thread for sensor monitoring"""
        while self.running:
            try:
                # Sensors read themselves in their own loop
                time.sleep(0.1)  # 100ms polling interval
            except Exception as e:
                self.logger.error(f"Error in sensor monitor loop: {e}")
                time.sleep(1)
    
    # Sensor methods
    def read_sensors(self) -> Dict[str, Any]:
        """Read all sensors"""
        return self.sensors.read_sensors()
    
    def get_presence_status(self) -> bool:
        """Get simple presence status"""
        return self.sensors.get_presence_status()
    
    # Display methods
    def update_display(self, display_data: Dict[str, Any]):
        """Update display with current status"""
        self.display.update_display(display_data)
    
    def show_message(self, message: str, duration: int = 3):
        """Show temporary message on display"""
        self.display.show_message(message, duration)
    
    def show_queue_warning(self):
        """Show queue active warning"""
        self.display.show_queue_warning()
    
    def show_timeout_warning(self):
        """Show timeout warning"""
        self.display.show_timeout_warning()
    
    def show_error(self, error_message: str = "Errore sistema"):
        """Show error message"""
        self.display.show_error(error_message)
    
    # LED methods
    def set_led_pattern(self, pattern: str):
        """Set LED pattern based on system state"""
        self.leds.set_led_pattern(pattern)
    
    def set_led_state(self, led_name: str, state: bool):
        """Set individual LED state"""
        self.leds.set_led_state(led_name, state)
    
    def flash_all_leds(self, count: int = 3, interval: float = 0.2):
        """Flash all LEDs for attention"""
        self.leds.flash_all_leds(count, interval)
    
    # Button methods
    def button_pressed(self, button_id: Optional[int] = None) -> bool:
        """Check if a button was pressed"""
        return self.buttons.button_pressed(button_id)
    
    def simulate_button_press(self, button_id: Optional[int] = None) -> bool:
        """Simulate button press for testing"""
        return self.buttons.simulate_button_press(button_id)
    
    # System status methods
    def get_hardware_status(self) -> Dict[str, Any]:
        """Get comprehensive hardware status"""
        sensor_data = self.sensors.read_sensors()
        
        return {
            'simulation_mode': self.simulation_mode,
            'initialized': self.initialized,
            'components': {
                'sensors': self.sensors.initialized,
                'display': self.display.initialized,
                'leds': self.leds.initialized,
                'buttons': self.buttons.initialized
            },
            'sensor_data': sensor_data,
            'led_states': self.leds.get_led_states(),
            'button_states': self.buttons.get_button_states(),
            'last_sensor_read': sensor_data.get('last_sensor_read', '').isoformat() if sensor_data.get('last_sensor_read') else None
        }
    
    def test_all_components(self) -> Dict[str, bool]:
        """Test all hardware components"""
        results = {}
        
        try:
            # Test display
            self.display.show_message("Test Display", duration=1)
            results['display'] = True
        except Exception as e:
            self.logger.error(f"Display test failed: {e}")
            results['display'] = False
        
        try:
            # Test LEDs
            self.leds.flash_all_leds(count=2, interval=0.1)
            results['leds'] = True
        except Exception as e:
            self.logger.error(f"LED test failed: {e}")
            results['leds'] = False
        
        try:
            # Test sensors
            sensor_data = self.sensors.read_sensors()
            results['sensors'] = sensor_data is not None
        except Exception as e:
            self.logger.error(f"Sensor test failed: {e}")
            results['sensors'] = False
        
        try:
            # Test buttons
            button_states = self.buttons.get_button_states()
            results['buttons'] = button_states is not None
        except Exception as e:
            self.logger.error(f"Button test failed: {e}")
            results['buttons'] = False
        
        return results
    
    def cleanup(self):
        """Clean up all hardware resources"""
        self.running = False
        
        try:
            # Wait for sensor thread to finish
            if self.sensor_thread and self.sensor_thread.is_alive():
                self.sensor_thread.join(timeout=2)
            
            # Cleanup all components
            self.leds.cleanup()
            self.display.cleanup()
            self.sensors.cleanup()
            self.buttons.cleanup()
            
            # Cleanup GPIO if in hardware mode
            if not self.simulation_mode and GPIO:
                GPIO.cleanup()
            
            self.logger.info("Hardware cleanup complete")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")