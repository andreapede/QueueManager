"""
Notification Manager for Queue Management System
Handles Pushover notifications (optional)
"""

import logging
import requests
from typing import Dict, Any, Optional
from datetime import datetime

from config.config import Config

class NotificationManager:
    """Manages push notifications via Pushover API"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.enabled = Config.PUSHOVER_ENABLED
        self.user_key = Config.PUSHOVER_USER_KEY
        self.api_token = Config.PUSHOVER_API_TOKEN
        
        # Notification templates
        self.templates = {
            'reservation_confirmed': "✅ Prenotazione confermata! Posizione in coda: {position}. Attesa stimata: {wait_time} min",
            'your_turn': "🚪 È il tuo turno! Hai {timeout} min per entrare nell'ufficio",
            'no_show': "⚠️ Prenotazione scaduta. Non ti sei presentato entro il tempo limite",
            'queue_cleared': "🔄 Coda svuotata dall'amministratore",
            'system_error': "❌ Sistema in errore. Contattare assistenza",
            'timeout_warning': "⏰ Tempo di occupazione scaduto. Liberare l'ufficio",
            'system_reset': "🔄 Sistema resettato. Tutte le prenotazioni sono state cancellate"
        }
        
        if self.enabled:
            self.logger.info("NotificationManager initialized with Pushover enabled")
        else:
            self.logger.info("NotificationManager initialized (Pushover disabled)")
    
    def send_notification(self, 
                         message_type: str, 
                         user_code: Optional[str] = None,
                         **kwargs) -> bool:
        """Send notification to user"""
        
        if not self.enabled:
            self.logger.debug(f"Notification not sent (disabled): {message_type}")
            return True
        
        if not self.user_key or not self.api_token:
            self.logger.warning("Pushover credentials not configured")
            return False
        
        try:
            # Get message template
            template = self.templates.get(message_type)
            if not template:
                self.logger.warning(f"Unknown notification type: {message_type}")
                return False
            
            # Format message
            message = template.format(**kwargs)
            
            # Prepare notification data
            data = {
                'token': self.api_token,
                'user': self.user_key,
                'message': message,
                'title': 'Queue Manager',
                'timestamp': int(datetime.now().timestamp())
            }
            
            # Add user-specific title if provided
            if user_code:
                data['title'] = f'Queue Manager - {user_code}'
            
            # Set priority based on message type
            priority = self._get_priority(message_type)
            if priority is not None:
                data['priority'] = priority
            
            # Send notification
            response = requests.post(
                'https://api.pushover.net/1/messages.json',
                data=data,
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.info(f"Notification sent: {message_type} to {user_code or 'all'}")
                return True
            else:
                self.logger.error(f"Failed to send notification: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending notification: {e}")
            return False
    
    def _get_priority(self, message_type: str) -> Optional[int]:
        """Get notification priority based on message type"""
        high_priority = ['system_error', 'timeout_warning']
        normal_priority = ['your_turn', 'no_show']
        low_priority = ['reservation_confirmed', 'queue_cleared', 'system_reset']
        
        if message_type in high_priority:
            return 1  # High priority
        elif message_type in normal_priority:
            return 0  # Normal priority
        elif message_type in low_priority:
            return -1  # Low priority
        
        return None  # Default priority
    
    def send_reservation_confirmed(self, user_code: str, position: int, wait_time: int) -> bool:
        """Send reservation confirmed notification"""
        return self.send_notification(
            'reservation_confirmed',
            user_code=user_code,
            position=position,
            wait_time=wait_time
        )
    
    def send_your_turn(self, user_code: str, timeout_minutes: int = 3) -> bool:
        """Send 'your turn' notification"""
        return self.send_notification(
            'your_turn',
            user_code=user_code,
            timeout=timeout_minutes
        )
    
    def send_no_show(self, user_code: str) -> bool:
        """Send no-show notification"""
        return self.send_notification(
            'no_show',
            user_code=user_code
        )
    
    def send_system_error(self, error_details: str = "") -> bool:
        """Send system error notification"""
        return self.send_notification(
            'system_error',
            error=error_details
        )
    
    def send_timeout_warning(self, user_code: Optional[str] = None) -> bool:
        """Send timeout warning notification"""
        return self.send_notification(
            'timeout_warning',
            user_code=user_code
        )
    
    def send_your_turn_notification(self, user_code: str, timeout_minutes: int = 3) -> bool:
        """Send 'your turn' notification to user"""
        return self.send_notification(
            'your_turn', 
            user_code=user_code,
            timeout=timeout_minutes
        )
    
    def send_queue_cleared(self) -> bool:
        """Send queue cleared notification"""
        return self.send_notification('queue_cleared')
    
    def send_system_reset(self) -> bool:
        """Send system reset notification"""
        return self.send_notification('system_reset')
    
    def test_notification(self) -> bool:
        """Send test notification"""
        return self.send_notification(
            'reservation_confirmed',
            user_code='TEST',
            position=1,
            wait_time=5
        )
    
    def is_enabled(self) -> bool:
        """Check if notifications are enabled"""
        return self.enabled
    
    def get_status(self) -> Dict[str, Any]:
        """Get notification system status"""
        return {
            'enabled': self.enabled,
            'configured': bool(self.user_key and self.api_token),
            'user_key_set': bool(self.user_key),
            'api_token_set': bool(self.api_token),
            'templates_count': len(self.templates)
        }
