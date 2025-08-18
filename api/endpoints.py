"""
API Endpoints for Queue Management System
RESTful API for web interface and external integrations
"""

import logging
from datetime import datetime
from flask import Blueprint, jsonify, request, session
from typing import Dict, Any

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
        user = db_manager.get_user_by_code(user_code)
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
        
        users = db_manager.get_all_users()
        
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
