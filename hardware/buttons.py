"""
Button Controller for Queue Management System
Handles 2 tactile buttons with debouncing
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional
import logging

try:
    import RPi.GPIO as GPIO
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    GPIO = None

from config.config import Config

class ButtonController:
    """Manages button input with debouncing"""
    
    def __init__(self, simulation_mode: bool = False):
        self.logger = logging.getLogger(__name__)
        self.simulation_mode = simulation_mode
        
        # GPIO pins from config
        self.button_pins = {
            1: Config.GPIO.BUTTON_1,  # Primary button
            2: Config.GPIO.BUTTON_2   # Secondary button
        }
        
        # Button states
        self.button_states = {1: False, 2: False}
        self.last_press_time = {1: None, 2: None}
        self.press_events = {1: [], 2: []}
        
        # Debouncing
        self.debounce_time = 0.05  # 50ms debounce
        self.button_lock = threading.Lock()
        
        # Event detection
        self.button_pressed_flags = {1: False, 2: False}
        
        self.initialized = False
        
        self.logger.info(f"ButtonController initialized (simulation: {simulation_mode})")
    
    def initialize(self) -> bool:
        """Initialize button GPIO pins"""
        try:
            if not self.simulation_mode:
                self._setup_hardware_buttons()
            
            self.initialized = True
            self.logger.info("Buttons initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize buttons: {e}")
            return False
    
    def _setup_hardware_buttons(self):
        """Setup button GPIO pins with interrupts"""
        if not GPIO:
            raise RuntimeError("GPIO not available")
        
        # Setup button pins as inputs with pull-up resistors
        for button_id, pin in self.button_pins.items():
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            # Add event detection for button press (falling edge due to pull-up)
            GPIO.add_event_detect(
                pin, 
                GPIO.FALLING,
                callback=lambda channel, btn_id=button_id: self._button_callback(btn_id),
                bouncetime=int(self.debounce_time * 1000)  # Convert to milliseconds
            )
        
        self.logger.info("Button GPIO pins configured with interrupts")
    
    def _button_callback(self, button_id: int):
        """GPIO interrupt callback for button press"""
        with self.button_lock:
            now = datetime.now()
            
            # Additional software debouncing
            if self.last_press_time[button_id]:
                time_since_last = now - self.last_press_time[button_id]
                if time_since_last.total_seconds() < self.debounce_time:
                    return  # Ignore - too soon after last press
            
            # Record button press
            self.last_press_time[button_id] = now
            self.button_pressed_flags[button_id] = True
            
            # Add to event list (keep last 10 events)
            self.press_events[button_id].append(now)
            if len(self.press_events[button_id]) > 10:
                self.press_events[button_id].pop(0)
            
            self.logger.info(f"Button {button_id} pressed")
    
    def button_pressed(self, button_id: Optional[int] = None) -> bool:
        """Check if button was pressed (consume event)"""
        with self.button_lock:
            if button_id is None:
                # Check any button
                any_pressed = any(self.button_pressed_flags.values())
                if any_pressed:
                    # Clear all flags
                    for btn_id in self.button_pressed_flags:
                        self.button_pressed_flags[btn_id] = False
                return any_pressed
            
            elif button_id in self.button_pressed_flags:
                # Check specific button
                was_pressed = self.button_pressed_flags[button_id]
                self.button_pressed_flags[button_id] = False  # Consume event
                return was_pressed
            
            return False
    
    def is_button_currently_pressed(self, button_id: int) -> bool:
        """Check if button is currently being pressed (real-time state)"""
        if button_id not in self.button_pins:
            return False
        
        if self.simulation_mode:
            return self.button_states[button_id]
        
        if not GPIO:
            return False
        
        # Read current GPIO state (LOW = pressed due to pull-up)
        pin = self.button_pins[button_id]
        return GPIO.input(pin) == GPIO.LOW
    
    def get_button_states(self) -> Dict[int, bool]:
        """Get current button states"""
        states = {}
        for button_id in self.button_pins:
            states[button_id] = self.is_button_currently_pressed(button_id)
        return states
    
    def get_last_press_time(self, button_id: int) -> Optional[datetime]:
        """Get time of last button press"""
        return self.last_press_time.get(button_id)
    
    def get_press_history(self, button_id: int) -> list:
        """Get recent press history for button"""
        with self.button_lock:
            return self.press_events[button_id].copy()
    
    def simulate_button_press(self, button_id: Optional[int] = None) -> bool:
        """Simulate button press for testing"""
        if not self.simulation_mode:
            self.logger.warning("simulate_button_press called in hardware mode")
            return False
        
        target_button = button_id if button_id is not None else 1
        
        if target_button not in self.button_pins:
            self.logger.warning(f"Invalid button ID for simulation: {target_button}")
            return False
        
        with self.button_lock:
            # Simulate press event
            now = datetime.now()
            self.last_press_time[target_button] = now
            self.button_pressed_flags[target_button] = True
            
            # Add to event list
            self.press_events[target_button].append(now)
            if len(self.press_events[target_button]) > 10:
                self.press_events[target_button].pop(0)
            
            self.logger.info(f"[SIMULATION] Button {target_button} pressed")
            return True
    
    def simulate_button_hold(self, button_id: int, duration: float = 1.0):
        """Simulate holding a button for testing"""
        if not self.simulation_mode:
            self.logger.warning("simulate_button_hold called in hardware mode")
            return
        
        if button_id not in self.button_pins:
            self.logger.warning(f"Invalid button ID for simulation: {button_id}")
            return
        
        self.logger.info(f"[SIMULATION] Button {button_id} held for {duration}s")
        
        # Set button as pressed
        self.button_states[button_id] = True
        time.sleep(duration)
        self.button_states[button_id] = False
        
        # Generate press event at the end
        self.simulate_button_press(button_id)
    
    def wait_for_button_press(self, timeout: Optional[float] = None) -> Optional[int]:
        """Wait for any button press and return which button"""
        start_time = time.time()
        
        while True:
            # Check all buttons
            for button_id in self.button_pins:
                if self.button_pressed(button_id):
                    return button_id
            
            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                return None
            
            time.sleep(0.01)  # 10ms polling
    
    def clear_all_events(self):
        """Clear all pending button events"""
        with self.button_lock:
            for button_id in self.button_pressed_flags:
                self.button_pressed_flags[button_id] = False
            self.logger.info("All button events cleared")
    
    def get_button_stats(self) -> Dict[int, Dict]:
        """Get button statistics"""
        stats = {}
        
        with self.button_lock:
            for button_id in self.button_pins:
                last_press = self.last_press_time[button_id]
                press_count = len(self.press_events[button_id])
                
                # Calculate press frequency (last minute)
                recent_presses = 0
                if press_count > 0:
                    one_minute_ago = datetime.now() - timedelta(minutes=1)
                    recent_presses = sum(1 for press_time in self.press_events[button_id] 
                                       if press_time > one_minute_ago)
                
                stats[button_id] = {
                    'last_press': last_press.isoformat() if last_press else None,
                    'total_presses': press_count,
                    'recent_presses_per_minute': recent_presses,
                    'currently_pressed': self.is_button_currently_pressed(button_id)
                }
        
        return stats
    
    def test_buttons(self):
        """Test button functionality"""
        self.logger.info("Starting button test")
        
        if self.simulation_mode:
            # Test simulation
            for button_id in [1, 2]:
                self.logger.info(f"Testing button {button_id} simulation")
                self.simulate_button_press(button_id)
                time.sleep(0.5)
                
                # Check if event was registered
                if self.button_pressed(button_id):
                    self.logger.info(f"Button {button_id} simulation successful")
                else:
                    self.logger.error(f"Button {button_id} simulation failed")
        else:
            # Test hardware - wait for user input
            self.logger.info("Press each button to test (10 second timeout per button)")
            for button_id in [1, 2]:
                self.logger.info(f"Press button {button_id}...")
                result = self.wait_for_button_press(timeout=10)
                if result == button_id:
                    self.logger.info(f"Button {button_id} test successful")
                else:
                    self.logger.warning(f"Button {button_id} test failed or timeout")
        
        self.logger.info("Button test completed")
    
    def cleanup(self):
        """Clean up button resources"""
        if not self.simulation_mode and GPIO:
            # Remove event detection
            for pin in self.button_pins.values():
                try:
                    GPIO.remove_event_detect(pin)
                except Exception:
                    pass  # Ignore errors during cleanup
        
        self.clear_all_events()
        self.logger.info("Button cleanup complete")
