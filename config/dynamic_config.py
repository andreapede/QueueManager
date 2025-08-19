"""
Dynamic Configuration Manager
Loads configuration from database with fallback to static config
"""

import logging
from typing import Any, Union
from config.config import Config as StaticConfig

logger = logging.getLogger(__name__)

class DynamicConfig:
    """Dynamic configuration that reads from database"""
    
    def __init__(self, db_manager=None):
        self.db_manager = db_manager
        self._cache = {}
        
    def _get_value(self, key: str, default_value: Any, value_type: type = str) -> Any:
        """Get configuration value from database with type conversion"""
        if not self.db_manager:
            # Fallback to static config
            return getattr(StaticConfig, key.upper(), default_value)
        
        try:
            # Try cache first
            if key in self._cache:
                return self._cache[key]
                
            # Get from database
            db_value = self.db_manager.get_config_value(key, None)
            
            if db_value is not None:
                # Convert to appropriate type
                if value_type == int:
                    converted_value = int(db_value)
                elif value_type == float:
                    converted_value = float(db_value)
                elif value_type == bool:
                    converted_value = str(db_value).lower() in ('true', '1', 'yes', 'on')
                else:
                    converted_value = str(db_value)
                
                # Cache the converted value
                self._cache[key] = converted_value
                return converted_value
            else:
                # Not in database, use default and cache it
                self._cache[key] = default_value
                return default_value
                
        except Exception as e:
            logger.error(f"Error getting config value {key}: {e}")
            # Fallback to static config
            return getattr(StaticConfig, key.upper(), default_value)
    
    def clear_cache(self):
        """Clear configuration cache"""
        self._cache.clear()
    
    def update_value(self, key: str, value: Any, description: str = None) -> bool:
        """Update configuration value in database"""
        if not self.db_manager:
            return False
            
        success = self.db_manager.set_config_value(key, value, description)
        if success:
            # Update cache
            self._cache[key] = value
        return success
    
    # Time settings
    @property
    def RESERVATION_TIMEOUT_MINUTES(self) -> int:
        return self._get_value('reservation_timeout_minutes', StaticConfig.RESERVATION_TIMEOUT_MINUTES, int)
    
    @property
    def MAX_OCCUPANCY_MINUTES(self) -> int:
        return self._get_value('max_occupancy_minutes', StaticConfig.MAX_OCCUPANCY_MINUTES, int)
    
    @property
    def MOVEMENT_TIMEOUT_MINUTES(self) -> int:
        return self._get_value('movement_timeout_minutes', StaticConfig.MOVEMENT_TIMEOUT_MINUTES, int)
    
    @property
    def AUTO_RESET_TIME(self) -> str:
        return self._get_value('auto_reset_time', StaticConfig.AUTO_RESET_TIME, str)
    
    # Queue settings
    @property
    def MAX_QUEUE_SIZE(self) -> int:
        return self._get_value('max_queue_size', StaticConfig.MAX_QUEUE_SIZE, int)
    
    @property
    def CONFLICT_PRIORITY(self) -> str:
        return self._get_value('conflict_priority', StaticConfig.CONFLICT_PRIORITY, str)
    
    # Sensor settings
    @property
    def USE_PIR_SENSOR(self) -> bool:
        return self._get_value('use_pir_sensor', StaticConfig.USE_PIR_SENSOR, bool)
    
    @property
    def USE_ULTRASONIC_SENSOR(self) -> bool:
        return self._get_value('use_ultrasonic_sensor', StaticConfig.USE_ULTRASONIC_SENSOR, bool)
    
    @property
    def PRESENCE_THRESHOLD_CM(self) -> int:
        return self._get_value('presence_threshold_cm', StaticConfig.PRESENCE_THRESHOLD_CM, int)
    
    @property
    def DUAL_SENSOR_MODE(self) -> str:
        return self._get_value('dual_sensor_mode', StaticConfig.DUAL_SENSOR_MODE, str)
    
    @property
    def PIR_ABSENCE_SECONDS(self) -> int:
        return self._get_value('pir_absence_seconds', StaticConfig.PIR_ABSENCE_SECONDS, int)
    
    @property
    def ULTRASONIC_POLLING_SECONDS(self) -> int:
        return self._get_value('ultrasonic_polling_seconds', StaticConfig.ULTRASONIC_POLLING_SECONDS, int)
    
    # Notification settings
    @property
    def PUSHOVER_ENABLED(self) -> bool:
        return self._get_value('pushover_enabled', StaticConfig.PUSHOVER_ENABLED, bool)
    
    @property
    def PUSHOVER_USER_KEY(self) -> str:
        return self._get_value('pushover_user_key', StaticConfig.PUSHOVER_USER_KEY, str)
    
    @property
    def PUSHOVER_API_TOKEN(self) -> str:
        return self._get_value('pushover_api_token', StaticConfig.PUSHOVER_API_TOKEN, str)
    
    # Security settings
    @property
    def SESSION_TIMEOUT_MINUTES(self) -> int:
        return self._get_value('session_timeout_minutes', StaticConfig.SESSION_TIMEOUT_MINUTES, int)
    
    @property
    def MAX_LOGIN_ATTEMPTS(self) -> int:
        return self._get_value('max_login_attempts', StaticConfig.MAX_LOGIN_ATTEMPTS, int)
    
    @property
    def LOCKOUT_DURATION_MINUTES(self) -> int:
        return self._get_value('lockout_duration_minutes', StaticConfig.LOCKOUT_DURATION_MINUTES, int)
    
    @property
    def ADMIN_PASSWORD(self) -> str:
        # Password always from static config for security
        return StaticConfig.ADMIN_PASSWORD

# Global instance (will be initialized by main app)
dynamic_config = None

def get_config():
    """Get the global dynamic config instance"""
    return dynamic_config if dynamic_config else StaticConfig
