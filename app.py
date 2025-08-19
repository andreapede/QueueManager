#!/usr/bin/env python3
"""
Queue Manager System - Main Application
Sistema di gestione coda per ufficio

Author: Andrea Pede
Date: August 18, 2025
"""

import os
import sys
import logging
from datetime import datetime, timedelta
import threading
import time

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit
from apscheduler.schedulers.background import BackgroundScheduler

# Import custom modules
from config.config import Config
from config.dynamic_config import DynamicConfig, dynamic_config
from database.db_manager import DatabaseManager
from hardware.hardware_controller import HardwareController
from utils.logger import setup_logger
from utils.notifications import NotificationManager
from api.endpoints import api_bp, init_api

class QueueManagerApp:
    def __init__(self):
        self.app = Flask(__name__, 
                         template_folder='web/templates',
                         static_folder='web/static')
        self.app.config.from_object(Config)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # Initialize components
        self.db = DatabaseManager()
        
        # Initialize dynamic configuration
        global dynamic_config
        if not dynamic_config:
            import config.dynamic_config
            config.dynamic_config.dynamic_config = DynamicConfig(self.db)
            dynamic_config = config.dynamic_config.dynamic_config
            
        # Initialize default config in database if needed
        self.db.init_default_config()
        
        self.hardware = HardwareController()
        self.notifications = NotificationManager()
        self.logger = setup_logger('QueueManager')
        
        # State management
        self.current_state = 'LIBERO'
        self.occupation_start = None
        self.reserved_for_user = None
        self.reservation_timeout = None
        self.running = True
        
        # Setup scheduler for periodic tasks
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(
            func=self.periodic_check,
            trigger="interval",
            seconds=1,
            id='periodic_check'
        )
        
        # Register blueprints
        self.app.register_blueprint(api_bp, url_prefix='/api')
        
        # Initialize API with components
        init_api(self.db, self.hardware, self.notifications, self)
        
        # Setup routes
        self.setup_routes()
        self.setup_socketio_events()
        
        self.logger.info("QueueManagerApp initialized")
    
    def get_dynamic_config(self):
        """Get dynamic configuration instance"""
        from config.dynamic_config import get_config
        return get_config()
    
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            return render_template('index.html')
        
        @self.app.route('/admin')
        def admin():
            if not self.check_admin_session():
                return redirect(url_for('admin_login'))
            return render_template('admin.html')
        
        @self.app.route('/admin/login', methods=['GET', 'POST'])
        def admin_login():
            if request.method == 'POST':
                password = request.form.get('password')
                if password == Config.ADMIN_PASSWORD:
                    session['admin_logged_in'] = True
                    session['admin_login_time'] = datetime.now().isoformat()
                    return redirect(url_for('admin'))
                else:
                    return render_template('admin_login.html', error='Password non corretta')
            return render_template('admin_login.html')
        
        @self.app.route('/admin/logout')
        def admin_logout():
            session.pop('admin_logged_in', None)
            session.pop('admin_login_time', None)
            return redirect(url_for('index'))
        
        @self.app.route('/admin/config')
        def admin_config():
            if not self.check_admin_session():
                return redirect(url_for('admin_login'))
            return render_template('admin_config.html')
        
        @self.app.route('/admin/users')
        def admin_users():
            if not self.check_admin_session():
                return redirect(url_for('admin_login'))
            return render_template('admin_users.html')
    
    def setup_socketio_events(self):
        """Setup SocketIO events for real-time updates"""
        
        @self.socketio.on('connect')
        def handle_connect():
            self.logger.info(f"Client connected: {request.sid}")
            # Send current status to new client
            emit('status_update', self.get_system_status())
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            self.logger.info(f"Client disconnected: {request.sid}")
    
    def check_admin_session(self):
        """Check if admin session is valid"""
        if not session.get('admin_logged_in'):
            return False
        
        login_time_str = session.get('admin_login_time')
        if not login_time_str:
            return False
        
        login_time = datetime.fromisoformat(login_time_str)
        if datetime.now() - login_time > timedelta(minutes=Config.SESSION_TIMEOUT_MINUTES):
            session.pop('admin_logged_in', None)
            session.pop('admin_login_time', None)
            return False
        
        return True
    
    def get_system_status(self):
        """Get current system status for API responses"""
        queue = self.db.get_queue()
        sensors = self.hardware.read_sensors()
        
        # Calculate estimated wait times for each position
        avg_duration = self.db.get_average_occupation_time() or Config.MAX_OCCUPANCY_MINUTES
        base_wait_time = 0
        
        # If office is currently occupied, calculate remaining time
        if self.current_state in ['OCCUPATO_DIRETTO', 'OCCUPATO_PRENOTATO', 'RISERVATO_ATTESA'] and self.occupation_start:
            elapsed = (datetime.now() - self.occupation_start).total_seconds() / 60
            base_wait_time = max(0, avg_duration - elapsed)
        elif self.current_state == 'RISERVATO_ATTESA':
            # If reserved but not occupied yet, add reservation timeout
            base_wait_time = Config.RESERVATION_TIMEOUT_MINUTES
        
        status = {
            'status': self.current_state,
            'occupied_by': self.reserved_for_user,
            'occupation_start': self.occupation_start.isoformat() if self.occupation_start else None,
            'reservation_timeout': self.reservation_timeout.isoformat() if self.reservation_timeout else None,
            'reservation_timeout_seconds': int((self.reservation_timeout - datetime.now()).total_seconds()) if self.reservation_timeout and self.reservation_timeout > datetime.now() else 0,
            'queue_size': len(queue),
            'queue': [{
                'position': i + 1,
                'user_code': item['user_code'],
                'user_name': self.db.get_user_name(item['user_code']),
                'estimated_time': (datetime.now() + timedelta(minutes=int(base_wait_time + (i * avg_duration)))).isoformat(),
                'wait_time_minutes': int(base_wait_time + (i * avg_duration))
            } for i, item in enumerate(queue)],
            'next_user': queue[0]['user_code'] if queue else None,
            'estimated_wait_minutes': self.calculate_estimated_wait(),
            'sensors': {
                'pir_movement': sensors.get('pir_movement', False),
                'ultrasonic_presence': sensors.get('ultrasonic_presence', False),
                'last_movement': sensors.get('last_movement_time', '').isoformat() if sensors.get('last_movement_time') else None
            }
        }
        
        return status
    
    def calculate_estimated_wait(self):
        """Calculate estimated wait time for next person in queue"""
        if self.current_state == 'LIBERO':
            return 0
        
        # Basic estimation: assume average occupation time
        avg_duration = self.db.get_average_occupation_time() or Config.MAX_OCCUPANCY_MINUTES
        
        if self.occupation_start:
            elapsed = (datetime.now() - self.occupation_start).total_seconds() / 60
            remaining = max(0, avg_duration - elapsed)
            return int(remaining)
        
        return int(avg_duration)
    
    def periodic_check(self):
        """Periodic system check - runs every second"""
        try:
            self.update_system_state()
            self.check_timeouts()
            self.update_display()
            self.broadcast_status_update()
        except Exception as e:
            self.logger.error(f"Error in periodic check: {e}")
    
    def update_system_state(self):
        """Update system state based on sensors and timers"""
        sensors = self.hardware.read_sensors()
        presence_detected = sensors.get('presence_detected', False)
        
        if self.current_state == 'LIBERO':
            # Check for direct button press
            if self.hardware.button_pressed():
                self.handle_direct_access()
            
            # Check if there's a queue and office is free
            elif not presence_detected:
                self.process_queue()
        
        elif self.current_state in ['OCCUPATO_DIRETTO', 'OCCUPATO_PRENOTATO']:
            # Check if office is now empty
            if not presence_detected:
                self.handle_office_vacated()
        
        elif self.current_state == 'RISERVATO_ATTESA':
            # Check if reserved user entered
            if presence_detected:
                self.current_state = 'OCCUPATO_PRENOTATO'
                self.occupation_start = datetime.now()
                
                # Log user entered office event
                self.db.log_event(
                    event_type='USER_ENTERED_OFFICE',
                    user_code=self.reserved_for_user,
                    state_from='RISERVATO_ATTESA',
                    state_to='OCCUPATO_PRENOTATO',
                    details=f'Utente {self.reserved_for_user} entrato in ufficio'
                )
                
                self.logger.info(f"User {self.reserved_for_user} entered office")
    
    def handle_direct_access(self):
        """Handle direct button press access"""
        if Config.CONFLICT_PRIORITY == 'presence' or not self.db.get_queue():
            self.current_state = 'OCCUPATO_DIRETTO'
            self.occupation_start = datetime.now()
            self.reserved_for_user = None
            self.logger.info("Direct access granted")
            
            # Log the event
            self.db.log_event(
                event_type='USER_ENTERED_OFFICE',
                state_from='LIBERO',
                state_to='OCCUPATO_DIRETTO',
                details='Accesso diretto tramite pulsante'
            )
        else:
            # Respect queue - show message on display
            self.hardware.show_queue_warning()
    
    def handle_office_vacated(self):
        """Handle when office becomes empty"""
        duration = None
        if self.occupation_start:
            duration = int((datetime.now() - self.occupation_start).total_seconds() / 60)
        
        # Log the occupation
        self.db.log_occupancy(
            start_time=self.occupation_start,
            end_time=datetime.now(),
            access_type='direct' if self.current_state == 'OCCUPATO_DIRETTO' else 'reservation',
            user_code=self.reserved_for_user,
            duration_minutes=duration
        )
        
        # Log office vacated event
        self.db.log_event(
            event_type='USER_LEFT_OFFICE',
            user_code=self.reserved_for_user,
            duration_minutes=duration,
            state_from=self.current_state,
            state_to='LIBERO',
            details=f'Durata occupazione: {duration} minuti' if duration else 'Ufficio liberato'
        )
        
        # Reset state
        self.current_state = 'LIBERO'
        self.occupation_start = None
        self.reserved_for_user = None
        
        # Process next in queue
        self.process_queue()
        
        self.logger.info(f"Office vacated after {duration} minutes")
    
    def process_queue(self):
        """Process next person in queue"""
        queue = self.db.get_queue()
        if queue:
            next_reservation = queue[0]
            self.current_state = 'RISERVATO_ATTESA'
            self.reserved_for_user = next_reservation['user_code']
            self.reservation_timeout = datetime.now() + timedelta(minutes=self.get_dynamic_config().RESERVATION_TIMEOUT_MINUTES)
            
            # Mark as active
            self.db.mark_reservation_active(next_reservation['id'])
            
            # Send notification
            self.notifications.send_your_turn_notification(
                user_code=self.reserved_for_user,
                timeout_minutes=self.get_dynamic_config().RESERVATION_TIMEOUT_MINUTES
            )
            
            self.logger.info(f"Activated reservation for {self.reserved_for_user}")
    
    def check_timeouts(self):
        """Check for various timeout conditions"""
        now = datetime.now()
        
        # Check reservation timeout
        if (self.current_state == 'RISERVATO_ATTESA' and 
            self.reservation_timeout and 
            now > self.reservation_timeout):
            
            self.logger.info(f"Reservation timeout for {self.reserved_for_user}")
            
            # Mark as no-show
            self.db.mark_reservation_no_show(self.reserved_for_user)
            
            # Send no-show notification
            self.notifications.send_no_show_notification(self.reserved_for_user)
            
            # Reset state and process next
            self.current_state = 'LIBERO'
            self.reserved_for_user = None
            self.reservation_timeout = None
            self.process_queue()
        
        # Check occupation timeout warning
        if (self.current_state in ['OCCUPATO_DIRETTO', 'OCCUPATO_PRENOTATO'] and 
            self.occupation_start):
            
            duration = (now - self.occupation_start).total_seconds() / 60
            
            if duration > Config.MAX_OCCUPANCY_MINUTES:
                # Show warning but don't force exit
                self.hardware.show_timeout_warning()
                if duration > Config.MAX_OCCUPANCY_MINUTES + 5:  # Grace period
                    self.logger.warning(f"Office occupied for {duration:.1f} minutes - extended use")
    
    def update_display(self):
        """Update OLED display with current status"""
        display_data = {
            'state': self.current_state,
            'queue_size': len(self.db.get_queue()),
            'occupation_time': None,
            'next_user': None
        }
        
        if self.occupation_start:
            duration = (datetime.now() - self.occupation_start).total_seconds() / 60
            display_data['occupation_time'] = f"{int(duration//60):02d}:{int(duration%60):02d}"
        
        queue = self.db.get_queue()
        if queue:
            display_data['next_user'] = queue[0]['user_code']
        
        self.hardware.update_display(display_data)
    
    def broadcast_status_update(self):
        """Broadcast status update to all connected clients"""
        try:
            status = self.get_system_status()
            self.socketio.emit('status_update', status)
        except Exception as e:
            self.logger.error(f"Error broadcasting status: {e}")
    
    def book_reservation(self, user_code):
        """Book a new reservation"""
        try:
            # Check if user exists
            if not self.db.user_exists(user_code):
                return {'success': False, 'message': 'Codice utente non valido'}
            
            # Check queue size limit
            queue = self.db.get_queue()
            if len(queue) >= self.get_dynamic_config().MAX_QUEUE_SIZE:
                return {'success': False, 'message': 'Coda piena, riprovare più tardi'}
            
            # Check if user already in queue
            if any(item['user_code'] == user_code for item in queue):
                return {'success': False, 'message': 'Sei già in coda'}
            
            # Add to queue
            reservation_id = self.db.add_to_queue(user_code)
            position = len(queue) + 1
            estimated_wait = self.calculate_estimated_wait() + (position - 1) * Config.MAX_OCCUPANCY_MINUTES
            
            # Send confirmation notification
            self.notifications.send_reservation_confirmation(
                user_code=user_code,
                position=position,
                wait_time=estimated_wait
            )
            
            # If office is free and this is first in queue, activate immediately
            if self.current_state == 'LIBERO' and position == 1:
                self.process_queue()
            
            self.logger.info(f"Reservation booked for {user_code}, position {position}")
            
            return {
                'success': True,
                'message': 'Prenotazione confermata',
                'position': position,
                'estimated_wait_minutes': estimated_wait,
                'reservation_id': reservation_id
            }
            
        except Exception as e:
            self.logger.error(f"Error booking reservation: {e}")
            return {'success': False, 'message': 'Errore interno del sistema'}
    
    def run(self):
        """Start the application"""
        try:
            # Initialize database
            self.db.initialize()
            
            # Initialize hardware
            self.hardware.initialize()
            
            # Start scheduler
            self.scheduler.start()
            
            self.logger.info("Queue Manager System started")
            
            # Run Flask app
            self.socketio.run(
                self.app,
                host='0.0.0.0',
                port=Config.PORT,
                debug=Config.DEBUG
            )
            
        except KeyboardInterrupt:
            self.logger.info("Shutdown requested")
        except Exception as e:
            self.logger.error(f"Fatal error: {e}")
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Clean shutdown"""
        self.running = False
        
        try:
            self.scheduler.shutdown()
        except:
            pass
        
        try:
            self.hardware.cleanup()
        except:
            pass
        
        self.logger.info("Queue Manager System shutdown complete")

# Create global app instance
app_instance = None

def create_app():
    """Application factory"""
    global app_instance
    if app_instance is None:
        app_instance = QueueManagerApp()
    return app_instance

if __name__ == '__main__':
    app = create_app()
    app.run()
