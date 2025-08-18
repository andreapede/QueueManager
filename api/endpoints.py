"""
API Endpoints for Queue Management System
RESTful API for web interface and external integrations
"""

import logging
from datetime import datetime
from flask import Blueprint, jsonify, request, session
from typing import Dict, Any

# Import configuration
from config.config import Config

# This will be set by the main app
db_manager = None
hardware_controller = None
notification_manager = None
app_instance = None

# Create blueprint
api_bp = Blueprint('api', __name__)
logger = logging.getLogger(__name__)

def init_api(db, hardware, notifications, app):
    """Initialize API with required components"""
    global db_manager, hardware_controller, notification_manager, app_instance
    db_manager = db
    hardware_controller = hardware
    notification_manager = notifications
    app_instance = app
    logger.info("API endpoints initialized")

# Public endpoints
@api_bp.route('/status', methods=['GET'])
def get_status():
    """Get current system status"""
    try:
        if not app_instance:
            return jsonify({'error': 'System not initialized'}), 500
        
        # Get system state
        current_state = getattr(app_instance, 'current_state', 'UNKNOWN')
        occupation_start = getattr(app_instance, 'occupation_start', None)
        reserved_for_user = getattr(app_instance, 'reserved_for_user', None)
        
        # Get queue data
        queue_data = db_manager.get_queue() if db_manager else []
        
        # Get sensor data
        sensor_data = hardware_controller.read_sensors() if hardware_controller else {}
        
        # Calculate occupation duration
        occupation_duration_minutes = 0
        if occupation_start:
            occupation_duration_minutes = (datetime.now() - occupation_start).total_seconds() / 60
        
        # Prepare response
        response = {
            'status': current_state,
            'occupied_by': reserved_for_user,
            'occupation_start': occupation_start.isoformat() if occupation_start else None,
            'occupation_duration_minutes': round(occupation_duration_minutes, 1),
            'queue_size': len(queue_data),
            'queue': [
                {
                    'position': i + 1,
                    'user_code': item['user_code'],
                    'user_name': item.get('user_name', 'Unknown'),
                    'wait_time_minutes': (datetime.now() - datetime.fromisoformat(item['timestamp'])).seconds // 60
                }
                for i, item in enumerate(queue_data)
            ],
            'next_user': queue_data[0]['user_code'] if queue_data else None,
            'estimated_wait_minutes': len(queue_data) * 8,  # 8 min average per person
            'sensors': {
                'pir_movement': sensor_data.get('pir_movement', False),
                'ultrasonic_distance_cm': sensor_data.get('ultrasonic_distance_cm', 999),
                'presence_detected': sensor_data.get('presence_detected', False),
                'last_movement': sensor_data.get('last_movement_time').isoformat() if sensor_data.get('last_movement_time') else None
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/book', methods=['POST'])
def book_office():
    """Create new reservation"""
    try:
        data = request.get_json()
        user_code = data.get('user_code')
        
        if not user_code:
            return jsonify({'error': 'user_code required'}), 400
        
        if not db_manager:
            return jsonify({'error': 'Database not available'}), 500
        
        # Check if user exists
        user = db_manager.get_user(user_code)
        if not user:
            return jsonify({'error': 'Invalid user code'}), 400
        
        # Check queue size limit
        queue_size = len(db_manager.get_queue())
        if queue_size >= 7:  # Config.MAX_QUEUE_SIZE
            return jsonify({'error': 'Queue is full'}), 400
        
        # Check if user already in queue
        existing_reservation = db_manager.get_user_in_queue(user_code)
        if existing_reservation:
            return jsonify({'error': 'User already has an active reservation'}), 400
        
        # Add to queue
        reservation_id = db_manager.add_to_queue(user_code)
        
        # Get position in queue
        queue = db_manager.get_queue()
        position = next(i + 1 for i, item in enumerate(queue) if item['id'] == reservation_id)
        
        # Send notification
        if notification_manager:
            notification_manager.send_reservation_confirmed(
                user_code=user_code,
                position=position,
                wait_time=position * 8
            )
        
        return jsonify({
            'success': True,
            'message': 'Prenotazione confermata',
            'reservation_id': reservation_id,
            'position': position,
            'estimated_wait_minutes': position * 8
        })
        
    except Exception as e:
        logger.error(f"Error booking office: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/queue', methods=['GET'])
def get_queue():
    """Get current queue"""
    try:
        if not db_manager:
            return jsonify({'error': 'Database not available'}), 500
        
        queue_data = db_manager.get_queue()
        
        queue_list = [
            {
                'position': i + 1,
                'user_code': item['user_code'],
                'user_name': item.get('user_name', 'Unknown'),
                'timestamp': item['timestamp'],
                'wait_time_minutes': (datetime.now() - datetime.fromisoformat(item['timestamp'])).seconds // 60
            }
            for i, item in enumerate(queue_data)
        ]
        
        return jsonify({
            'queue': queue_list,
            'size': len(queue_list)
        })
        
    except Exception as e:
        logger.error(f"Error getting queue: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/users', methods=['GET'])
def get_users():
    """Get available user codes"""
    try:
        if not db_manager:
            return jsonify({'error': 'Database not available'}), 500
        
        users = db_manager.get_users()
        
        return jsonify({
            'users': [
                {
                    'code': user['code'],
                    'name': user['name']
                }
                for user in users
            ]
        })
        
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/stats', methods=['GET'])
def get_stats():
    """Get public statistics"""
    try:
        if not db_manager:
            return jsonify({'error': 'Database not available'}), 500
        
        # Get basic stats
        stats = db_manager.get_daily_stats()
        
        return jsonify({
            'today': {
                'total_sessions': stats.get('total_sessions', 0),
                'average_duration_minutes': stats.get('avg_duration', 0),
                'occupancy_percentage': stats.get('occupancy_percentage', 0),
                'queue_peak': stats.get('max_queue_size', 0)
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Admin endpoints (protected)
def require_admin_auth():
    """Check if user is authenticated as admin"""
    if not session.get('admin_logged_in'):
        return False
    
    # Check session timeout (30 minutes)
    login_time_str = session.get('admin_login_time')
    if not login_time_str:
        return False
    
    login_time = datetime.fromisoformat(login_time_str)
    if (datetime.now() - login_time).total_seconds() > (30 * 60):  # 30 minutes
        session.pop('admin_logged_in', None)
        session.pop('admin_login_time', None)
        return False
    
    return True

@api_bp.route('/admin/login', methods=['POST'])
def admin_login():
    """Admin login"""
    try:
        data = request.get_json()
        password = data.get('password')
        
        if password == 'admin123':  # Config.ADMIN_PASSWORD
            session['admin_logged_in'] = True
            session['admin_login_time'] = datetime.now().isoformat()
            return jsonify({'success': True, 'message': 'Login successful'})
        else:
            return jsonify({'error': 'Invalid password'}), 401
            
    except Exception as e:
        logger.error(f"Error in admin login: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/admin/logout', methods=['POST'])
def admin_logout():
    """Admin logout"""
    session.pop('admin_logged_in', None)
    session.pop('admin_login_time', None)
    return jsonify({'success': True, 'message': 'Logged out'})

@api_bp.route('/admin/status', methods=['GET'])
def admin_status():
    """Check admin authentication status"""
    if require_admin_auth():
        return jsonify({'authenticated': True})
    else:
        return jsonify({'authenticated': False}), 401

@api_bp.route('/admin/reset', methods=['POST'])
def admin_reset():
    """Reset entire system"""
    if not require_admin_auth():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if app_instance:
            # Reset application state
            app_instance.current_state = 'LIBERO'
            app_instance.occupation_start = None
            app_instance.reserved_for_user = None
            app_instance.reservation_timeout = None
        
        if db_manager:
            # Clear queue
            db_manager.clear_queue()
        
        if hardware_controller:
            # Reset hardware
            hardware_controller.set_led_pattern('LIBERO')
            hardware_controller.show_message('Sistema resettato', duration=3)
        
        if notification_manager:
            notification_manager.send_system_reset()
        
        logger.info("System reset by admin")
        return jsonify({'success': True, 'message': 'System reset complete'})
        
    except Exception as e:
        logger.error(f"Error resetting system: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/admin/clear_queue', methods=['POST'])
def admin_clear_queue():
    """Clear queue only"""
    if not require_admin_auth():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if db_manager:
            cleared_count = len(db_manager.get_queue())
            db_manager.clear_queue()
            
            if notification_manager:
                notification_manager.send_queue_cleared()
            
            logger.info(f"Queue cleared by admin ({cleared_count} reservations)")
            return jsonify({
                'success': True, 
                'message': f'Queue cleared ({cleared_count} reservations)'
            })
        else:
            return jsonify({'error': 'Database not available'}), 500
            
    except Exception as e:
        logger.error(f"Error clearing queue: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/admin/force_unlock', methods=['POST'])
def admin_force_unlock():
    """Force unlock office"""
    if not require_admin_auth():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if app_instance:
            # Force unlock
            app_instance.current_state = 'LIBERO'
            app_instance.occupation_start = None
            app_instance.reserved_for_user = None
            app_instance.reservation_timeout = None
            
            if hardware_controller:
                hardware_controller.set_led_pattern('LIBERO')
                hardware_controller.show_message('Ufficio liberato', duration=3)
            
            logger.info("Office force unlocked by admin")
            return jsonify({'success': True, 'message': 'Office unlocked'})
        else:
            return jsonify({'error': 'Application not available'}), 500
            
    except Exception as e:
        logger.error(f"Error force unlocking office: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/admin/config', methods=['GET'])
def get_admin_config():
    """Get current system configuration"""
    if not require_admin_auth():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        # Get all configuration values from Config class
        config_data = {}
        
        # Time settings
        config_data['reservation_timeout_minutes'] = Config.RESERVATION_TIMEOUT_MINUTES
        config_data['max_occupancy_minutes'] = Config.MAX_OCCUPANCY_MINUTES
        config_data['movement_timeout_minutes'] = Config.MOVEMENT_TIMEOUT_MINUTES
        config_data['auto_reset_time'] = Config.AUTO_RESET_TIME
        
        # Queue settings
        config_data['max_queue_size'] = Config.MAX_QUEUE_SIZE
        config_data['conflict_priority'] = Config.CONFLICT_PRIORITY
        
        # Sensor settings
        config_data['use_pir_sensor'] = Config.USE_PIR_SENSOR
        config_data['use_ultrasonic_sensor'] = Config.USE_ULTRASONIC_SENSOR
        config_data['presence_threshold_cm'] = Config.PRESENCE_THRESHOLD_CM
        config_data['dual_sensor_mode'] = Config.DUAL_SENSOR_MODE
        config_data['pir_absence_seconds'] = Config.PIR_ABSENCE_SECONDS
        config_data['ultrasonic_polling_seconds'] = Config.ULTRASONIC_POLLING_SECONDS
        
        # Notification settings
        config_data['pushover_enabled'] = Config.PUSHOVER_ENABLED
        config_data['pushover_user_key'] = Config.PUSHOVER_USER_KEY if Config.PUSHOVER_ENABLED else ''
        config_data['pushover_api_token'] = Config.PUSHOVER_API_TOKEN if Config.PUSHOVER_ENABLED else ''
        
        # Security settings
        config_data['session_timeout_minutes'] = Config.SESSION_TIMEOUT_MINUTES
        config_data['max_login_attempts'] = Config.MAX_LOGIN_ATTEMPTS
        config_data['lockout_duration_minutes'] = Config.LOCKOUT_DURATION_MINUTES
        
        return jsonify({
            'success': True,
            'config': config_data
        })
        
    except Exception as e:
        logger.error(f"Error getting admin config: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/admin/config', methods=['POST'])
def update_admin_config():
    """Update system configuration"""
    if not require_admin_auth():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        config_updates = request.get_json()
        
        # Validate and update configuration
        # Note: In a real implementation, you would want to:
        # 1. Validate all values
        # 2. Save to a config file or database
        # 3. Apply changes to running system
        
        # For now, we'll just log the changes
        logger.info(f"Admin config update requested: {config_updates}")
        
        # Simulate updating some runtime values
        updated_keys = []
        
        # Update specific config values that can be changed at runtime
        if 'reservation_timeout_minutes' in config_updates:
            Config.RESERVATION_TIMEOUT_MINUTES = int(config_updates['reservation_timeout_minutes'])
            updated_keys.append('reservation_timeout_minutes')
        
        if 'max_occupancy_minutes' in config_updates:
            Config.MAX_OCCUPANCY_MINUTES = int(config_updates['max_occupancy_minutes'])
            updated_keys.append('max_occupancy_minutes')
        
        if 'max_queue_size' in config_updates:
            Config.MAX_QUEUE_SIZE = int(config_updates['max_queue_size'])
            updated_keys.append('max_queue_size')
        
        if 'conflict_priority' in config_updates:
            Config.CONFLICT_PRIORITY = config_updates['conflict_priority']
            updated_keys.append('conflict_priority')
        
        if 'presence_threshold_cm' in config_updates:
            Config.PRESENCE_THRESHOLD_CM = int(config_updates['presence_threshold_cm'])
            updated_keys.append('presence_threshold_cm')
        
        # Handle password change
        if config_updates.get('new_admin_password'):
            Config.ADMIN_PASSWORD = config_updates['new_admin_password']
            updated_keys.append('admin_password')
        
        logger.info(f"Admin updated configuration keys: {updated_keys}")
        
        return jsonify({
            'success': True,
            'message': f'Configurazione aggiornata ({len(updated_keys)} parametri)',
            'updated_keys': updated_keys
        })
        
    except Exception as e:
        logger.error(f"Error updating admin config: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/admin/config/reset', methods=['POST'])
def reset_admin_config():
    """Reset configuration to defaults"""
    if not require_admin_auth():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        # Reset to default values
        Config.RESERVATION_TIMEOUT_MINUTES = 3
        Config.MAX_OCCUPANCY_MINUTES = 10
        Config.MAX_QUEUE_SIZE = 7
        Config.CONFLICT_PRIORITY = 'presence'
        Config.USE_PIR_SENSOR = True
        Config.USE_ULTRASONIC_SENSOR = True
        Config.PRESENCE_THRESHOLD_CM = 200
        Config.DUAL_SENSOR_MODE = 'AND'
        Config.PIR_ABSENCE_SECONDS = 30
        Config.ULTRASONIC_POLLING_SECONDS = 2
        Config.PUSHOVER_ENABLED = False
        Config.SESSION_TIMEOUT_MINUTES = 30
        Config.MAX_LOGIN_ATTEMPTS = 3
        Config.LOCKOUT_DURATION_MINUTES = 15
        Config.ADMIN_PASSWORD = 'admin123'
        
        logger.info("Admin reset configuration to defaults")
        
        return jsonify({
            'success': True,
            'message': 'Configurazione ripristinata ai valori di default'
        })
        
    except Exception as e:
        logger.error(f"Error resetting admin config: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/admin/config/test', methods=['POST'])
def test_admin_config():
    """Test current configuration"""
    if not require_admin_auth():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        test_results = {}
        
        # Test timeout values are reasonable
        test_results['timeout_values'] = (
            1 <= Config.RESERVATION_TIMEOUT_MINUTES <= 15 and
            5 <= Config.MAX_OCCUPANCY_MINUTES <= 60 and
            Config.RESERVATION_TIMEOUT_MINUTES < Config.MAX_OCCUPANCY_MINUTES
        )
        
        # Test queue size is reasonable
        test_results['queue_size'] = (1 <= Config.MAX_QUEUE_SIZE <= 20)
        
        # Test sensor thresholds
        test_results['sensor_thresholds'] = (
            50 <= Config.PRESENCE_THRESHOLD_CM <= 400 and
            10 <= Config.PIR_ABSENCE_SECONDS <= 300 and
            1 <= Config.ULTRASONIC_POLLING_SECONDS <= 10
        )
        
        # Test security settings
        test_results['security_settings'] = (
            10 <= Config.SESSION_TIMEOUT_MINUTES <= 120 and
            3 <= Config.MAX_LOGIN_ATTEMPTS <= 10 and
            5 <= Config.LOCKOUT_DURATION_MINUTES <= 60
        )
        
        # Test conflict priority is valid
        test_results['conflict_priority'] = Config.CONFLICT_PRIORITY in ['presence', 'reservation']
        
        # Test dual sensor mode is valid
        test_results['dual_sensor_mode'] = Config.DUAL_SENSOR_MODE in ['AND', 'OR']
        
        # Test Pushover config if enabled
        if Config.PUSHOVER_ENABLED:
            test_results['pushover_config'] = (
                len(Config.PUSHOVER_USER_KEY) > 10 and
                len(Config.PUSHOVER_API_TOKEN) > 10
            )
        else:
            test_results['pushover_config'] = True
        
        # Test password strength (basic check)
        test_results['password_strength'] = len(Config.ADMIN_PASSWORD) >= 6
        
        all_passed = all(test_results.values())
        
        logger.info(f"Admin config test results: {test_results}")
        
        return jsonify({
            'success': True,
            'tests': test_results,
            'allPassed': all_passed,
            'message': 'Test configurazione completato'
        })
        
    except Exception as e:
        logger.error(f"Error testing admin config: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# User management endpoints
@api_bp.route('/admin/users', methods=['GET'])
def get_admin_users():
    """Get all users (admin only)"""
    if not require_admin_auth():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if not db_manager:
            return jsonify({'error': 'Database not available'}), 500
        
        users = db_manager.get_users()
        
        return jsonify({
            'success': True,
            'users': users,
            'count': len(users)
        })
        
    except Exception as e:
        logger.error(f"Error getting admin users: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/admin/users', methods=['POST'])
def create_user():
    """Create a new user"""
    if not require_admin_auth():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        code = data.get('code', '').strip()
        name = data.get('name', '').strip()
        
        # Validation
        if not code or not name:
            return jsonify({'error': 'Code and name are required'}), 400
        
        if len(code) != 2 or not code.isdigit():
            return jsonify({'error': 'Code must be exactly 2 digits'}), 400
        
        if len(name) > 50:
            return jsonify({'error': 'Name must be max 50 characters'}), 400
        
        if not db_manager:
            return jsonify({'error': 'Database not available'}), 500
        
        # Check if code already exists
        existing_user = db_manager.get_user(code)
        if existing_user:
            return jsonify({'error': f'Code {code} already exists'}), 400
        
        # Create user
        success = db_manager.add_user(code, name)
        
        if success:
            logger.info(f"Admin created user: {code} - {name}")
            return jsonify({
                'success': True,
                'message': f'User {code} created successfully',
                'user': {'code': code, 'name': name}
            })
        else:
            return jsonify({'error': 'Failed to create user'}), 500
            
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/admin/users/<code>', methods=['PUT'])
def update_user(code):
    """Update an existing user"""
    if not require_admin_auth():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        new_code = data.get('code', '').strip()
        name = data.get('name', '').strip()
        
        # Validation
        if not new_code or not name:
            return jsonify({'error': 'Code and name are required'}), 400
        
        if len(new_code) != 2 or not new_code.isdigit():
            return jsonify({'error': 'Code must be exactly 2 digits'}), 400
        
        if len(name) > 50:
            return jsonify({'error': 'Name must be max 50 characters'}), 400
        
        if not db_manager:
            return jsonify({'error': 'Database not available'}), 500
        
        # Check if original user exists
        original_user = db_manager.get_user(code)
        if not original_user:
            return jsonify({'error': f'User {code} not found'}), 404
        
        # If code changed, check if new code already exists
        if new_code != code:
            existing_user = db_manager.get_user(new_code)
            if existing_user:
                return jsonify({'error': f'Code {new_code} already exists'}), 400
        
        # Update user
        success = db_manager.update_user(code, new_code, name)
        
        if success:
            logger.info(f"Admin updated user: {code} -> {new_code} - {name}")
            return jsonify({
                'success': True,
                'message': f'User updated successfully',
                'user': {'code': new_code, 'name': name}
            })
        else:
            return jsonify({'error': 'Failed to update user'}), 500
            
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/admin/users/<code>', methods=['DELETE'])
def delete_user(code):
    """Delete a specific user"""
    if not require_admin_auth():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if not db_manager:
            return jsonify({'error': 'Database not available'}), 500
        
        # Check if user exists
        user = db_manager.get_user(code)
        if not user:
            return jsonify({'error': f'User {code} not found'}), 404
        
        # Check if user is currently in queue
        queue_entry = db_manager.get_user_in_queue(code)
        if queue_entry:
            return jsonify({'error': f'Cannot delete user {code}: currently in queue'}), 400
        
        # Delete user
        success = db_manager.delete_user(code)
        
        if success:
            logger.info(f"Admin deleted user: {code} - {user.get('name', 'Unknown')}")
            return jsonify({
                'success': True,
                'message': f'User {code} deleted successfully'
            })
        else:
            return jsonify({'error': 'Failed to delete user'}), 500
            
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/admin/users', methods=['DELETE'])
def delete_all_users():
    """Delete all users"""
    if not require_admin_auth():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        if not db_manager:
            return jsonify({'error': 'Database not available'}), 500
        
        # Check if anyone is currently in queue
        queue = db_manager.get_queue()
        if queue:
            return jsonify({'error': 'Cannot delete users: there are active reservations in queue'}), 400
        
        # Get count before deletion
        users = db_manager.get_users()
        user_count = len(users)
        
        if user_count == 0:
            return jsonify({'error': 'No users to delete'}), 400
        
        # Delete all users
        success = db_manager.delete_all_users()
        
        if success:
            logger.info(f"Admin deleted all {user_count} users")
            return jsonify({
                'success': True,
                'message': f'All {user_count} users deleted successfully'
            })
        else:
            return jsonify({'error': 'Failed to delete users'}), 500
            
    except Exception as e:
        logger.error(f"Error deleting all users: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@api_bp.route('/admin/users/import', methods=['POST'])
def import_users():
    """Import multiple users from CSV data"""
    if not require_admin_auth():
        return jsonify({'error': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        csv_data = data.get('csv_data', '').strip()
        
        if not csv_data:
            return jsonify({'error': 'No data provided'}), 400
        
        if not db_manager:
            return jsonify({'error': 'Database not available'}), 500
        
        # Parse CSV data
        lines = csv_data.split('\n')
        users_to_create = []
        errors = []
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
                
            parts = line.split(',')
            if len(parts) != 2:
                errors.append(f"Line {i}: Invalid format (expected: code,name)")
                continue
            
            code = parts[0].strip()
            name = parts[1].strip()
            
            # Validate code
            if len(code) != 2 or not code.isdigit():
                errors.append(f"Line {i}: Code '{code}' must be exactly 2 digits")
                continue
            
            # Validate name
            if not name or len(name) > 50:
                errors.append(f"Line {i}: Name invalid (empty or > 50 chars)")
                continue
            
            # Check for duplicates in this import
            if any(u['code'] == code for u in users_to_create):
                errors.append(f"Line {i}: Code '{code}' duplicated in import data")
                continue
            
            # Check if code already exists in database
            existing_user = db_manager.get_user(code)
            if existing_user:
                errors.append(f"Line {i}: Code '{code}' already exists in database")
                continue
            
            users_to_create.append({'code': code, 'name': name})
        
        if errors:
            return jsonify({
                'success': False,
                'error': 'Import validation failed',
                'errors': errors,
                'valid_users': len(users_to_create)
            }), 400
        
        if not users_to_create:
            return jsonify({'error': 'No valid users to import'}), 400
        
        # Create users
        created_count = 0
        creation_errors = []
        
        for user_data in users_to_create:
            success = db_manager.add_user(user_data['code'], user_data['name'])
            if success:
                created_count += 1
            else:
                creation_errors.append(f"Failed to create user {user_data['code']}")
        
        logger.info(f"Admin imported {created_count} users")
        
        result = {
            'success': True,
            'message': f'Successfully imported {created_count} users',
            'created_count': created_count,
            'total_attempted': len(users_to_create)
        }
        
        if creation_errors:
            result['warnings'] = creation_errors
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error importing users: {e}")
        return jsonify({'error': 'Internal server error'}), 500
