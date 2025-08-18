"""
Display Controller for Queue Management System
Handles OLED SSD1306 128x64 display
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any
import logging

try:
    from luma.core.interface.serial import i2c
    from luma.core.render import canvas
    from luma.oled.device import ssd1306
    DISPLAY_AVAILABLE = True
except ImportError:
    DISPLAY_AVAILABLE = False

class DisplayController:
    """Manages OLED display output"""
    
    def __init__(self, simulation_mode: bool = False):
        self.logger = logging.getLogger(__name__)
        self.simulation_mode = simulation_mode
        
        # Display device
        self.device = None
        self.initialized = False
        
        # Display state
        self.current_screen = 'init'
        self.temp_message = None
        self.temp_message_end = None
        
        # Threading for display updates
        self.display_lock = threading.Lock()
        
        self.logger.info(f"DisplayController initialized (simulation: {simulation_mode})")
    
    def initialize(self) -> bool:
        """Initialize OLED display"""
        try:
            if not self.simulation_mode and DISPLAY_AVAILABLE:
                self._setup_hardware_display()
            
            self.initialized = True
            
            # Show startup message
            self.show_message("Inizializzazione...", duration=2)
            
            self.logger.info("Display initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize display: {e}")
            return False
    
    def _setup_hardware_display(self):
        """Setup hardware OLED display"""
        try:
            # Create I2C interface
            serial = i2c(port=1, address=0x3C)
            
            # Create display device
            self.device = ssd1306(serial, width=128, height=64)
            
            # Clear display
            self.device.clear()
            
            self.logger.info("Hardware OLED display configured")
            
        except Exception as e:
            self.logger.error(f"Failed to setup hardware display: {e}")
            raise
    
    def update_display(self, display_data: Dict[str, Any]):
        """Update display with current system status"""
        with self.display_lock:
            try:
                # Check for temporary message
                if self._is_temp_message_active():
                    return  # Don't override temp message
                
                state = display_data.get('state', 'UNKNOWN')
                
                if state == 'LIBERO':
                    self._show_free_screen(display_data)
                elif state in ['OCCUPATO_DIRETTO', 'OCCUPATO_PRENOTATO']:
                    self._show_occupied_screen(display_data)
                elif state == 'IN_CODA':
                    self._show_queue_screen(display_data)
                elif state == 'RISERVATO_ATTESA':
                    self._show_reserved_screen(display_data)
                elif state == 'WARNING_TIMEOUT':
                    self._show_warning_screen(display_data)
                else:
                    self._show_error_screen(f"Stato: {state}")
                
                self.current_screen = state
                
            except Exception as e:
                self.logger.error(f"Error updating display: {e}")
    
    def _show_free_screen(self, data: Dict[str, Any]):
        """Show free office screen"""
        queue_size = data.get('queue_size', 0)
        
        if self.simulation_mode:
            self.logger.info(f"[DISPLAY] UFFICIO: LIBERO | Coda: {queue_size} persone | Premi per entrare")
            return
        
        if not self.device:
            return
        
        with canvas(self.device) as draw:
            # Title
            draw.text((10, 5), "UFFICIO: LIBERO", fill="white")
            draw.text((10, 20), f"Coda: {queue_size} persone", fill="white")
            
            # Instructions
            if queue_size == 0:
                draw.text((10, 40), "Premi per entrare", fill="white")
            else:
                draw.text((10, 40), "Prenota online o", fill="white")
                draw.text((10, 52), "premi per saltare", fill="white")
    
    def _show_occupied_screen(self, data: Dict[str, Any]):
        """Show occupied office screen"""
        queue_size = data.get('queue_size', 0)
        occupation_duration = data.get('occupation_duration_minutes', 0)
        user_name = data.get('occupied_by', 'Sconosciuto')
        next_user = data.get('next_user', None)
        
        if self.simulation_mode:
            self.logger.info(f"[DISPLAY] UFFICIO: OCCUPATO | Tempo: {occupation_duration:02d}:{occupation_duration%60:02d} | Coda: {queue_size}")
            return
        
        if not self.device:
            return
        
        with canvas(self.device) as draw:
            # Title
            draw.text((5, 2), "UFFICIO: OCCUPATO", fill="white")
            
            # Duration
            mins = int(occupation_duration)
            secs = int((occupation_duration - mins) * 60)
            draw.text((5, 16), f"Tempo: {mins:02d}:{secs:02d}", fill="white")
            
            # Queue info
            draw.text((5, 30), f"Coda: {queue_size} persone", fill="white")
            
            if next_user and queue_size > 0:
                # Truncate long user codes
                display_user = next_user[:12] if len(next_user) > 12 else next_user
                draw.text((5, 44), "Prossimo:", fill="white")
                draw.text((5, 56), display_user, fill="white")
    
    def _show_queue_screen(self, data: Dict[str, Any]):
        """Show queue active screen"""
        queue_size = data.get('queue_size', 0)
        next_user = data.get('next_user', 'N/A')
        estimated_wait = data.get('estimated_wait_minutes', 0)
        
        if self.simulation_mode:
            self.logger.info(f"[DISPLAY] CODA ATTIVA | {queue_size} in attesa | Prossimo: {next_user}")
            return
        
        if not self.device:
            return
        
        with canvas(self.device) as draw:
            draw.text((10, 5), "CODA ATTIVA", fill="white")
            draw.text((5, 20), f"{queue_size} in attesa", fill="white")
            draw.text((5, 35), "Prossimo:", fill="white")
            
            # Truncate user code if too long
            display_user = next_user[:12] if len(next_user) > 12 else next_user
            draw.text((5, 48), display_user, fill="white")
    
    def _show_reserved_screen(self, data: Dict[str, Any]):
        """Show reserved for user screen"""
        user_name = data.get('reserved_for', 'Utente')
        timeout_remaining = data.get('timeout_remaining_seconds', 180)
        
        if self.simulation_mode:
            self.logger.info(f"[DISPLAY] RISERVATO per {user_name} | {timeout_remaining}s rimasti")
            return
        
        if not self.device:
            return
        
        with canvas(self.device) as draw:
            draw.text((15, 5), "RISERVATO", fill="white")
            
            # User name (truncated)
            display_user = user_name[:12] if len(user_name) > 12 else user_name
            draw.text((5, 20), f"Per: {display_user}", fill="white")
            
            # Countdown
            mins = timeout_remaining // 60
            secs = timeout_remaining % 60
            draw.text((5, 35), f"Tempo: {mins:02d}:{secs:02d}", fill="white")
            draw.text((5, 50), "Premi per entrare", fill="white")
    
    def _show_warning_screen(self, data: Dict[str, Any]):
        """Show timeout warning screen"""
        occupation_duration = data.get('occupation_duration_minutes', 0)
        movement_time_ago = data.get('movement_time_ago_minutes', 0)
        
        if self.simulation_mode:
            self.logger.info(f"[DISPLAY] WARNING | Occupato da {occupation_duration} min | Ultimo movimento: {movement_time_ago} min fa")
            return
        
        if not self.device:
            return
        
        with canvas(self.device) as draw:
            draw.text((5, 2), "UFFICIO: OCCUPATO", fill="white")
            draw.text((5, 16), "Ultimo movimento:", fill="white")
            draw.text((5, 30), f"{movement_time_ago} minuti fa", fill="white")
            draw.text((5, 44), "Muoversi per", fill="white")
            draw.text((5, 56), "confermare presenza", fill="white")
    
    def _show_error_screen(self, error_msg: str = "Errore sistema"):
        """Show error screen"""
        if self.simulation_mode:
            self.logger.info(f"[DISPLAY] ERRORE: {error_msg}")
            return
        
        if not self.device:
            return
        
        with canvas(self.device) as draw:
            draw.text((20, 15), "ERRORE", fill="white")
            draw.text((5, 35), error_msg[:18], fill="white")  # Truncate long messages
            draw.text((5, 50), "Contattare assistenza", fill="white")
    
    def show_message(self, message: str, duration: int = 3):
        """Show temporary message"""
        with self.display_lock:
            self.temp_message = message
            self.temp_message_end = datetime.now() + timedelta(seconds=duration)
            
            if self.simulation_mode:
                self.logger.info(f"[DISPLAY] TEMP MESSAGE: {message} ({duration}s)")
                return
            
            if not self.device:
                return
            
            # Clear and show message
            with canvas(self.device) as draw:
                # Center the message
                lines = message.split('\n')
                y_start = 32 - (len(lines) * 8)
                
                for i, line in enumerate(lines):
                    y_pos = y_start + (i * 16)
                    # Center text horizontally (approximate)
                    x_pos = max(5, (128 - len(line) * 6) // 2)
                    draw.text((x_pos, y_pos), line, fill="white")
    
    def show_queue_warning(self):
        """Show queue active warning"""
        self.show_message("CODA ATTIVA\nPrenota online", duration=3)
    
    def show_timeout_warning(self):
        """Show timeout warning"""
        self.show_message("TEMPO SCADUTO\nLiberare ufficio", duration=5)
    
    def show_error(self, error_message: str = "Errore sistema"):
        """Show error message"""
        self.show_message(f"ERRORE\n{error_message}", duration=10)
    
    def _is_temp_message_active(self) -> bool:
        """Check if temporary message should still be shown"""
        if not self.temp_message_end:
            return False
        
        if datetime.now() > self.temp_message_end:
            self.temp_message = None
            self.temp_message_end = None
            return False
        
        return True
    
    def clear_display(self):
        """Clear the display"""
        if self.simulation_mode:
            self.logger.info("[DISPLAY] CLEARED")
            return
        
        if self.device:
            self.device.clear()
    
    def test_display(self):
        """Test display functionality"""
        test_messages = [
            "Test Display 1",
            "Test Display 2\nMulti-line",
            "123456789012345678"  # Long text test
        ]
        
        for i, msg in enumerate(test_messages):
            self.show_message(msg, duration=1)
            time.sleep(1.5)
        
        self.logger.info("Display test completed")
    
    def cleanup(self):
        """Clean up display resources"""
        if self.device:
            self.device.clear()
        
        self.logger.info("Display cleanup complete")
