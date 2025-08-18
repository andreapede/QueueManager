"""
LED Controller for Queue Management System
Manages 4 LEDs (2 Red, 2 Green) through transistors
"""

import time
import threading
from typing import Dict, Any
import logging

try:
    import RPi.GPIO as GPIO
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    GPIO = None

from config.config import Config

class LEDController:
    """Manages LED states and patterns"""
    
    def __init__(self, simulation_mode: bool = False):
        self.logger = logging.getLogger(__name__)
        self.simulation_mode = simulation_mode
        
        # GPIO pins from config
        self.led_pins = {
            'led1_red': Config.GPIO.LED_1_RED,
            'led1_green': Config.GPIO.LED_1_GREEN,
            'led2_red': Config.GPIO.LED_2_RED,
            'led2_green': Config.GPIO.LED_2_GREEN
        }
        
        # LED states
        self.led_states = {
            'led1_red': False,
            'led1_green': False,
            'led2_red': False,
            'led2_green': False
        }
        
        # Pattern control
        self.current_pattern = None
        self.pattern_thread = None
        self.pattern_running = False
        self.pattern_lock = threading.Lock()
        
        self.initialized = False
        
        self.logger.info(f"LEDController initialized (simulation: {simulation_mode})")
    
    def initialize(self) -> bool:
        """Initialize LED GPIO pins"""
        try:
            if not self.simulation_mode:
                self._setup_hardware_leds()
            
            # Turn off all LEDs initially
            self._set_all_leds_off()
            
            self.initialized = True
            self.logger.info("LEDs initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize LEDs: {e}")
            return False
    
    def _setup_hardware_leds(self):
        """Setup LED GPIO pins"""
        if not GPIO:
            raise RuntimeError("GPIO not available")
        
        # Setup all LED pins as outputs
        for pin in self.led_pins.values():
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)  # Start with LEDs off
        
        self.logger.info("LED GPIO pins configured")
    
    def set_led_state(self, led_name: str, state: bool):
        """Set individual LED state"""
        if led_name not in self.led_pins:
            self.logger.warning(f"Unknown LED: {led_name}")
            return
        
        self.led_states[led_name] = state
        
        if self.simulation_mode:
            status = "ON" if state else "OFF"
            self.logger.info(f"[LED] {led_name.upper()}: {status}")
            return
        
        if not self.simulation_mode and GPIO:
            pin = self.led_pins[led_name]
            GPIO.output(pin, GPIO.HIGH if state else GPIO.LOW)
    
    def get_led_states(self) -> Dict[str, bool]:
        """Get current LED states"""
        return self.led_states.copy()
    
    def _set_all_leds_off(self):
        """Turn off all LEDs"""
        for led_name in self.led_pins.keys():
            self.set_led_state(led_name, False)
    
    def _set_all_leds_on(self):
        """Turn on all LEDs"""
        for led_name in self.led_pins.keys():
            self.set_led_state(led_name, True)
    
    def set_led_pattern(self, pattern: str):
        """Set LED pattern based on system state"""
        with self.pattern_lock:
            # Stop any existing pattern
            self._stop_pattern()
            
            self.current_pattern = pattern
            
            if pattern == 'LIBERO':
                self._pattern_free()
            elif pattern == 'OCCUPATO':
                self._pattern_occupied()
            elif pattern == 'IN_CODA':
                self._pattern_queue()
            elif pattern == 'RISERVATO_ATTESA':
                self._pattern_reserved()
            elif pattern == 'WARNING_TIMEOUT':
                self._pattern_warning()
            elif pattern == 'ERROR':
                self._pattern_error()
            elif pattern == 'OFF':
                self._set_all_leds_off()
            else:
                self.logger.warning(f"Unknown LED pattern: {pattern}")
    
    def _pattern_free(self):
        """LED pattern for free office - Green solid"""
        self._set_all_leds_off()
        self.set_led_state('led1_green', True)  # Button LED green
        self.set_led_state('led2_green', True)  # Status LED green
        
        if self.simulation_mode:
            self.logger.info("[LED PATTERN] LIBERO: Verde fisso")
    
    def _pattern_occupied(self):
        """LED pattern for occupied office - Red solid"""
        self._set_all_leds_off()
        self.set_led_state('led1_red', True)   # Button LED red
        self.set_led_state('led2_red', True)   # Status LED red
        
        if self.simulation_mode:
            self.logger.info("[LED PATTERN] OCCUPATO: Rosso fisso")
    
    def _pattern_queue(self):
        """LED pattern for queue active - Green blinking + Yellow effect"""
        self._set_all_leds_off()
        
        # Start blinking pattern
        self._start_blinking_pattern([
            ('led1_green', True),   # Button LED green blink
            ('led2_red', True),     # Status LED red blink (red+green = yellow effect)
            ('led2_green', True)
        ], interval=1.0)
        
        if self.simulation_mode:
            self.logger.info("[LED PATTERN] IN_CODA: Verde lampeggio + giallo")
    
    def _pattern_reserved(self):
        """LED pattern for reserved - Alternate green/red"""
        self._set_all_leds_off()
        
        # Start alternating pattern
        self._start_alternating_pattern(interval=0.5)
        
        if self.simulation_mode:
            self.logger.info("[LED PATTERN] RISERVATO: Alternato verde/rosso")
    
    def _pattern_warning(self):
        """LED pattern for timeout warning - Red blinking"""
        self._set_all_leds_off()
        
        # Fast red blinking
        self._start_blinking_pattern([
            ('led1_red', True),
            ('led2_red', True)
        ], interval=0.3)
        
        if self.simulation_mode:
            self.logger.info("[LED PATTERN] WARNING: Rosso lampeggio veloce")
    
    def _pattern_error(self):
        """LED pattern for system error - Status LED red, button off"""
        self._set_all_leds_off()
        self.set_led_state('led2_red', True)  # Only status LED red
        
        if self.simulation_mode:
            self.logger.info("[LED PATTERN] ERROR: Solo LED stato rosso")
    
    def _start_blinking_pattern(self, leds_to_blink: list, interval: float = 1.0):
        """Start blinking pattern for specified LEDs"""
        self.pattern_running = True
        self.pattern_thread = threading.Thread(
            target=self._blinking_loop, 
            args=(leds_to_blink, interval),
            daemon=True
        )
        self.pattern_thread.start()
    
    def _start_alternating_pattern(self, interval: float = 0.5):
        """Start alternating green/red pattern"""
        self.pattern_running = True
        self.pattern_thread = threading.Thread(
            target=self._alternating_loop, 
            args=(interval,),
            daemon=True
        )
        self.pattern_thread.start()
    
    def _blinking_loop(self, leds_to_blink: list, interval: float):
        """Blinking pattern loop"""
        state = False
        while self.pattern_running:
            state = not state
            
            for led_name, _ in leds_to_blink:
                self.set_led_state(led_name, state)
            
            time.sleep(interval)
    
    def _alternating_loop(self, interval: float):
        """Alternating green/red pattern loop"""
        green_on = True
        while self.pattern_running:
            if green_on:
                # Green phase
                self.set_led_state('led1_green', True)
                self.set_led_state('led2_green', True)
                self.set_led_state('led1_red', False)
                self.set_led_state('led2_red', False)
            else:
                # Red phase
                self.set_led_state('led1_green', False)
                self.set_led_state('led2_green', False)
                self.set_led_state('led1_red', True)
                self.set_led_state('led2_red', True)
            
            green_on = not green_on
            time.sleep(interval)
    
    def _stop_pattern(self):
        """Stop current pattern"""
        self.pattern_running = False
        if self.pattern_thread and self.pattern_thread.is_alive():
            self.pattern_thread.join(timeout=1)
        self.pattern_thread = None
    
    def flash_all_leds(self, count: int = 3, interval: float = 0.2):
        """Flash all LEDs for attention"""
        with self.pattern_lock:
            # Stop current pattern
            current_pattern = self.current_pattern
            self._stop_pattern()
            
            if self.simulation_mode:
                self.logger.info(f"[LED] FLASH ALL: {count} volte, interval {interval}s")
                time.sleep(count * interval * 2)  # Simulate flash duration
            else:
                # Flash sequence
                for i in range(count):
                    self._set_all_leds_on()
                    time.sleep(interval)
                    self._set_all_leds_off()
                    time.sleep(interval)
            
            # Restore previous pattern
            if current_pattern:
                self.set_led_pattern(current_pattern)
    
    def test_leds(self):
        """Test all LEDs individually"""
        self.logger.info("Starting LED test sequence")
        
        # Test each LED individually
        for led_name in self.led_pins.keys():
            self.logger.info(f"Testing {led_name}")
            self._set_all_leds_off()
            self.set_led_state(led_name, True)
            time.sleep(0.5)
        
        # Test all patterns
        patterns = ['LIBERO', 'OCCUPATO', 'IN_CODA', 'WARNING_TIMEOUT', 'ERROR']
        for pattern in patterns:
            self.logger.info(f"Testing pattern: {pattern}")
            self.set_led_pattern(pattern)
            time.sleep(2)
        
        # Turn off
        self.set_led_pattern('OFF')
        self.logger.info("LED test completed")
    
    def cleanup(self):
        """Clean up LED resources"""
        with self.pattern_lock:
            self._stop_pattern()
            self._set_all_leds_off()
        
        self.logger.info("LED cleanup complete")
