"""
Configuration settings for Queue Manager System
"""

import os
from datetime import time

class Config:
    """Main configuration class"""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'queue-manager-secret-key-2025'
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    PORT = int(os.environ.get('PORT', 5000))
    
    # Database settings
    DATABASE_PATH = os.environ.get('DATABASE_PATH') or 'data/queue_manager.db'
    DATABASE_BACKUP_PATH = os.environ.get('DATABASE_BACKUP_PATH') or 'data/backups/'
    
    # System timeouts (minutes)
    RESERVATION_TIMEOUT_MINUTES = int(os.environ.get('RESERVATION_TIMEOUT_MINUTES', 3))
    MAX_OCCUPANCY_MINUTES = int(os.environ.get('MAX_OCCUPANCY_MINUTES', 10))
    MAX_QUEUE_SIZE = int(os.environ.get('MAX_QUEUE_SIZE', 7))
    
    # Conflict resolution
    CONFLICT_PRIORITY = os.environ.get('CONFLICT_PRIORITY', 'presence')  # 'presence' or 'reservation'
    
    # Daily reset time
    AUTO_RESET_TIME = os.environ.get('AUTO_RESET_TIME', '23:59')
    
    # Sensor settings
    PIR_ABSENCE_SECONDS = int(os.environ.get('PIR_ABSENCE_SECONDS', 30))
    MOVEMENT_TIMEOUT_MINUTES = int(os.environ.get('MOVEMENT_TIMEOUT_MINUTES', 5))
    MOVEMENT_WARNING_MINUTES = int(os.environ.get('MOVEMENT_WARNING_MINUTES', 3))
    MAX_STATIC_OCCUPANCY_MINUTES = int(os.environ.get('MAX_STATIC_OCCUPANCY_MINUTES', 30))
    PRESENCE_THRESHOLD_CM = int(os.environ.get('PRESENCE_THRESHOLD_CM', 200))
    ULTRASONIC_POLLING_SECONDS = int(os.environ.get('ULTRASONIC_POLLING_SECONDS', 2))
    
    # Sensor configuration
    USE_PIR_SENSOR = os.environ.get('USE_PIR_SENSOR', 'True').lower() == 'true'
    USE_ULTRASONIC_SENSOR = os.environ.get('USE_ULTRASONIC_SENSOR', 'True').lower() == 'true'
    DUAL_SENSOR_MODE = os.environ.get('DUAL_SENSOR_MODE', 'AND')  # 'AND' or 'OR'
    
    # Warning settings
    WARNING_FLASH_INTERVAL_SECONDS = int(os.environ.get('WARNING_FLASH_INTERVAL_SECONDS', 2))
    
    # Pushover notifications (optional)
    PUSHOVER_ENABLED = os.environ.get('PUSHOVER_ENABLED', 'False').lower() == 'true'
    PUSHOVER_USER_KEY = os.environ.get('PUSHOVER_USER_KEY', '')
    PUSHOVER_API_TOKEN = os.environ.get('PUSHOVER_API_TOKEN', '')
    
    # Admin settings
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
    SESSION_TIMEOUT_MINUTES = int(os.environ.get('SESSION_TIMEOUT_MINUTES', 30))
    MAX_LOGIN_ATTEMPTS = int(os.environ.get('MAX_LOGIN_ATTEMPTS', 3))
    LOCKOUT_DURATION_MINUTES = int(os.environ.get('LOCKOUT_DURATION_MINUTES', 15))
    
    # GPIO pin assignments
    class GPIO:
        # Display I2C
        DISPLAY_SDA = 2
        DISPLAY_SCL = 3
        
        # Sensors
        PIR_SENSOR = 4
        ULTRASONIC_TRIG = 18
        ULTRASONIC_ECHO = 24
        
        # Buttons
        BUTTON_1 = 17
        BUTTON_2 = 27
        
        # LEDs
        LED_1_RED = 22
        LED_1_GREEN = 23
        LED_2_RED = 25
        LED_2_GREEN = 26
    
    # Logging settings
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/queue_manager.log')
    LOG_MAX_BYTES = int(os.environ.get('LOG_MAX_BYTES', 10485760))  # 10MB
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', 5))
    
    # Default users
    DEFAULT_USERS = [
        {'code': 'USER_001', 'name': 'Mario Rossi'},
        {'code': 'USER_002', 'name': 'Luigi Verdi'},
        {'code': 'USER_003', 'name': 'Giuseppe Bianchi'},
        {'code': 'USER_004', 'name': 'Francesco Neri'},
        {'code': 'USER_005', 'name': 'Antonio Blu'},
        {'code': 'ADMIN', 'name': 'Amministratore'},
        {'code': 'GUEST', 'name': 'Ospite'},
        {'code': 'TECH', 'name': 'Tecnico'},
        {'code': 'MAINT', 'name': 'Manutenzione'},
        {'code': 'TEST', 'name': 'Test User'}
    ]
    
    @classmethod
    def get_all_settings(cls):
        """Get all configuration settings as dictionary"""
        settings = {}
        for attr in dir(cls):
            if not attr.startswith('_') and not callable(getattr(cls, attr)):
                value = getattr(cls, attr)
                if not isinstance(value, type):
                    settings[attr] = value
        return settings
    
    @classmethod
    def update_setting(cls, key, value):
        """Update a configuration setting"""
        if hasattr(cls, key):
            setattr(cls, key, value)
            return True
        return False

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    USE_PIR_SENSOR = False  # Disable hardware sensors for development
    USE_ULTRASONIC_SENSOR = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'change-this-in-production'

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DATABASE_PATH = ':memory:'  # Use in-memory database for tests
    USE_PIR_SENSOR = False
    USE_ULTRASONIC_SENSOR = False

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
