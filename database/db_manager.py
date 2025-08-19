"""
Database Manager for Queue Management System
Handles all database operations using SQLite
"""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import logging
from contextlib import contextmanager

from config.config import Config

class DatabaseManager:
    """Manages all database operations for the queue system"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or Config.DATABASE_PATH
        self.logger = logging.getLogger(__name__)
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def initialize(self) -> bool:
        """Initialize database with required tables"""
        try:
            with self.get_connection() as conn:
                # Create tables
                self._create_tables(conn)
                
                # Insert default data
                self._insert_default_data(conn)
                
                conn.commit()
                self.logger.info("Database initialized successfully")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            return False
    
    def _create_tables(self, conn: sqlite3.Connection):
        """Create all required tables"""
        
        # Users table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Queue table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_code TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'waiting',
                start_time DATETIME,
                end_time DATETIME,
                FOREIGN KEY (user_code) REFERENCES users(code)
            )
        """)
        
        # Occupancy statistics table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS occupancy_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_time DATETIME NOT NULL,
                end_time DATETIME,
                access_type TEXT NOT NULL,
                user_code TEXT,
                duration_minutes INTEGER,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_code) REFERENCES users(code)
            )
        """)
        
        # Events table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT NOT NULL,
                user_code TEXT,
                duration_minutes INTEGER,
                state_from TEXT,
                state_to TEXT,
                queue_size INTEGER,
                no_show BOOLEAN DEFAULT FALSE,
                conflict_occurred BOOLEAN DEFAULT FALSE,
                details TEXT
            )
        """)
        
        # Configuration table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                description TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Admin sessions table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS admin_sessions (
                session_id TEXT PRIMARY KEY,
                login_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        # Login attempts table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS login_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL,
                attempt_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN DEFAULT FALSE,
                lockout_until DATETIME
            )
        """)
        
        # Create indexes for better performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_queue_status ON queue(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_queue_timestamp ON queue(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_occupancy_start ON occupancy_stats(start_time)")
    
    def _insert_default_data(self, conn: sqlite3.Connection):
        """Insert default users and configuration"""
        
        # Insert default users if they don't exist
        for user in Config.DEFAULT_USERS:
            conn.execute(
                "INSERT OR IGNORE INTO users (code, name) VALUES (?, ?)",
                (user['code'], user['name'])
            )
        
        # Insert default configuration
        default_config = {
            'reservation_timeout_minutes': str(Config.RESERVATION_TIMEOUT_MINUTES),
            'max_occupancy_minutes': str(Config.MAX_OCCUPANCY_MINUTES),
            'max_queue_size': str(Config.MAX_QUEUE_SIZE),
            'conflict_priority': Config.CONFLICT_PRIORITY,
            'auto_reset_time': Config.AUTO_RESET_TIME,
            'pir_absence_seconds': str(Config.PIR_ABSENCE_SECONDS),
            'movement_timeout_minutes': str(Config.MOVEMENT_TIMEOUT_MINUTES),
            'presence_threshold_cm': str(Config.PRESENCE_THRESHOLD_CM),
            'use_pir_sensor': str(Config.USE_PIR_SENSOR),
            'use_ultrasonic_sensor': str(Config.USE_ULTRASONIC_SENSOR),
            'dual_sensor_mode': Config.DUAL_SENSOR_MODE,
            'pushover_enabled': str(Config.PUSHOVER_ENABLED)
        }
        
        for key, value in default_config.items():
            conn.execute(
                "INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)",
                (key, value)
            )
    
    # User management methods
    def get_users(self) -> List[Dict]:
        """Get all users"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT code, name FROM users ORDER BY name")
            return [dict(row) for row in cursor.fetchall()]
    
    def user_exists(self, user_code: str) -> bool:
        """Check if user exists"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT 1 FROM users WHERE code = ?", (user_code,))
            return cursor.fetchone() is not None
    
    def get_user_name(self, user_code: str) -> Optional[str]:
        """Get user name by code"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT name FROM users WHERE code = ?", (user_code,))
            row = cursor.fetchone()
            return row['name'] if row else None
    
    def add_user(self, user_code: str, name: str) -> bool:
        """Add new user"""
        try:
            with self.get_connection() as conn:
                conn.execute(
                    "INSERT INTO users (code, name) VALUES (?, ?)",
                    (user_code, name)
                )
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False
    
    def update_user(self, user_code: str, name: str) -> bool:
        """Update user name"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(
                    "UPDATE users SET name = ? WHERE code = ?",
                    (name, user_code)
                )
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error:
            return False
    
    def delete_user(self, user_code: str) -> bool:
        """Delete user if not in queue or has no history"""
        try:
            with self.get_connection() as conn:
                # Check if user has queue entries or occupancy history
                cursor = conn.execute(
                    "SELECT 1 FROM queue WHERE user_code = ? UNION SELECT 1 FROM occupancy_stats WHERE user_code = ? LIMIT 1",
                    (user_code, user_code)
                )
                if cursor.fetchone():
                    return False  # User has history, cannot delete
                
                cursor = conn.execute(
                    "DELETE FROM users WHERE code = ?",
                    (user_code,)
                )
                conn.commit()
                return cursor.rowcount > 0
        except sqlite3.Error:
            return False
    
    def get_user(self, user_code: str) -> Optional[Dict]:
        """Get user details by code"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT code, name FROM users WHERE code = ?",
                (user_code,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def validate_user_code(self, user_code: str) -> bool:
        """Validate user code format (2 digits)"""
        import re
        return bool(re.match(r'^\d{2}$', user_code))
    
    def bulk_delete_users(self, user_codes: List[str]) -> Dict[str, bool]:
        """Delete multiple users, returns dict with success/failure for each"""
        results = {}
        for code in user_codes:
            results[code] = self.delete_user(code)
        return results
    
    def import_users_from_csv(self, csv_data: str) -> Dict[str, Any]:
        """Import users from CSV data"""
        import csv
        from io import StringIO
        
        results = {
            'success': 0,
            'errors': 0,
            'duplicates': 0,
            'invalid': 0,
            'details': []
        }
        
        try:
            csv_file = StringIO(csv_data)
            reader = csv.DictReader(csv_file)
            
            for row_num, row in enumerate(reader, start=2):  # Start from 2 (accounting for header)
                code = row.get('code', '').strip()
                name = row.get('name', '').strip()
                
                if not code or not name:
                    results['invalid'] += 1
                    results['details'].append(f"Riga {row_num}: Codice o nome mancante")
                    continue
                
                if not self.validate_user_code(code):
                    results['invalid'] += 1
                    results['details'].append(f"Riga {row_num}: Codice '{code}' non valido (deve essere 2 cifre)")
                    continue
                
                if self.user_exists(code):
                    results['duplicates'] += 1
                    results['details'].append(f"Riga {row_num}: Utente '{code}' già esistente")
                    continue
                
                if self.add_user(code, name):
                    results['success'] += 1
                else:
                    results['errors'] += 1
                    results['details'].append(f"Riga {row_num}: Errore nell'aggiungere utente '{code}'")
                    
        except Exception as e:
            results['details'].append(f"Errore nella lettura del CSV: {str(e)}")
            results['errors'] += 1
        
        return results
    
    def delete_all_users(self) -> bool:
        """Delete all users (only if no history exists)"""
        try:
            with self.get_connection() as conn:
                # Check if any users have queue entries or occupancy history
                cursor = conn.execute("""
                    SELECT 1 FROM queue WHERE user_code IS NOT NULL 
                    UNION 
                    SELECT 1 FROM occupancy_stats WHERE user_code IS NOT NULL 
                    LIMIT 1
                """)
                if cursor.fetchone():
                    return False  # Users have history, cannot delete
                
                cursor = conn.execute("DELETE FROM users")
                conn.commit()
                return True
        except sqlite3.Error:
            return False
    
    # Queue management methods
    def get_queue(self) -> List[Dict]:
        """Get current queue ordered by timestamp"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT q.id, q.user_code, q.timestamp, q.status, u.name as user_name
                FROM queue q
                JOIN users u ON q.user_code = u.code
                WHERE q.status = 'waiting'
                ORDER BY q.timestamp
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def add_to_queue(self, user_code: str) -> int:
        """Add user to queue, returns reservation ID"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO queue (user_code) VALUES (?)",
                (user_code,)
            )
            conn.commit()
            return cursor.lastrowid
    
    def mark_reservation_active(self, reservation_id: int):
        """Mark reservation as active"""
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE queue SET status = 'active', start_time = ? WHERE id = ?",
                (datetime.now().isoformat(), reservation_id)
            )
            conn.commit()
    
    def mark_reservation_completed(self, reservation_id: int):
        """Mark reservation as completed"""
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE queue SET status = 'completed', end_time = ? WHERE id = ?",
                (datetime.now().isoformat(), reservation_id)
            )
            conn.commit()
    
    def mark_reservation_no_show(self, user_code: str):
        """Mark reservation as no-show"""
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE queue SET status = 'no_show' WHERE user_code = ? AND status IN ('waiting', 'reserved')",
                (user_code,)
            )
            conn.commit()
    
    def remove_from_queue(self, user_code: str) -> bool:
        """Remove user from queue"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM queue WHERE user_code = ? AND status = 'waiting'",
                (user_code,)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def clear_queue(self):
        """Clear entire queue"""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM queue WHERE status = 'waiting'")
            conn.commit()
    
    def get_queue_position(self, user_code: str) -> Optional[int]:
        """Get user's position in queue (1-indexed)"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT ROW_NUMBER() OVER (ORDER BY timestamp) as position
                FROM queue
                WHERE user_code = ? AND status = 'waiting'
            """, (user_code,))
            row = cursor.fetchone()
            return row['position'] if row else None
    
    def get_user_in_queue(self, user_code: str) -> Optional[Dict]:
        """Get user's queue entry if they are currently in queue"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT q.id, q.user_code, q.timestamp, q.status, u.name as user_name
                FROM queue q
                JOIN users u ON q.user_code = u.code
                WHERE q.user_code = ? AND q.status = 'waiting'
            """, (user_code,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # Statistics and analytics methods
    def log_occupancy(self, start_time: datetime, end_time: datetime, 
                     access_type: str, user_code: str = None, 
                     duration_minutes: int = None):
        """Log occupancy statistics"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO occupancy_stats 
                (start_time, end_time, access_type, user_code, duration_minutes)
                VALUES (?, ?, ?, ?, ?)
            """, (start_time.isoformat(), end_time.isoformat(), 
                  access_type, user_code, duration_minutes))
            conn.commit()
    
    def log_event(self, event_type: str, user_code: str = None, 
                  duration_minutes: int = None, state_from: str = None,
                  state_to: str = None, queue_size: int = None,
                  no_show: bool = False, conflict_occurred: bool = False,
                  details: str = None):
        """Log system event"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO events 
                (event_type, user_code, duration_minutes, state_from, state_to,
                 queue_size, no_show, conflict_occurred, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (event_type, user_code, duration_minutes, state_from, state_to,
                  queue_size, no_show, conflict_occurred, details))
            conn.commit()
    
    def get_comprehensive_stats(self, date: datetime = None, period: str = 'day') -> Dict:
        """Get comprehensive statistics including no-shows, access types, etc."""
        if date is None:
            date = datetime.now()
        
        # Define time range based on period
        if period == 'day':
            start_date = date.strftime('%Y-%m-%d')
            end_date = (date + timedelta(days=1)).strftime('%Y-%m-%d')
        elif period == 'week':
            start_date = (date - timedelta(days=6)).strftime('%Y-%m-%d')
            end_date = (date + timedelta(days=1)).strftime('%Y-%m-%d')
        elif period == 'month':
            start_date = date.replace(day=1).strftime('%Y-%m-%d')
            next_month = (date.replace(day=28) + timedelta(days=4)).replace(day=1)
            end_date = next_month.strftime('%Y-%m-%d')
        else:
            raise ValueError("Period must be 'day', 'week', or 'month'")
        
        with self.get_connection() as conn:
            stats = {}
            
            # === OCCUPANCY STATISTICS ===
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_occupations,
                    AVG(duration_minutes) as avg_duration,
                    SUM(duration_minutes) as total_usage_minutes,
                    MAX(duration_minutes) as max_duration,
                    MIN(duration_minutes) as min_duration
                FROM occupancy_stats
                WHERE start_time >= ? AND start_time < ?
                AND duration_minutes IS NOT NULL
            """, (start_date, end_date))
            occupancy_stats = dict(cursor.fetchone())
            stats['occupancy'] = occupancy_stats
            
            # === ACCESS TYPE BREAKDOWN ===
            cursor = conn.execute("""
                SELECT 
                    access_type,
                    COUNT(*) as count,
                    AVG(duration_minutes) as avg_duration
                FROM occupancy_stats
                WHERE start_time >= ? AND start_time < ?
                GROUP BY access_type
            """, (start_date, end_date))
            access_types = {}
            for row in cursor.fetchall():
                access_types[row['access_type']] = {
                    'count': row['count'],
                    'avg_duration': round(row['avg_duration'], 1) if row['avg_duration'] else 0
                }
            stats['access_types'] = access_types
            
            # === NO-SHOW STATISTICS ===
            cursor = conn.execute("""
                SELECT COUNT(*) as no_show_count
                FROM events
                WHERE timestamp >= ? AND timestamp < ?
                AND event_type = 'NO_SHOW'
                AND no_show = 1
            """, (start_date, end_date))
            no_show_stats = dict(cursor.fetchone())
            
            # === BOOKING STATISTICS ===
            cursor = conn.execute("""
                SELECT COUNT(*) as total_bookings
                FROM events
                WHERE timestamp >= ? AND timestamp < ?
                AND event_type = 'BOOKING_CREATED'
            """, (start_date, end_date))
            booking_stats = dict(cursor.fetchone())
            
            # === QUEUE STATISTICS ===
            cursor = conn.execute("""
                SELECT 
                    MAX(queue_size) as max_queue_size,
                    AVG(queue_size) as avg_queue_size
                FROM events
                WHERE timestamp >= ? AND timestamp < ?
                AND queue_size IS NOT NULL
            """, (start_date, end_date))
            queue_stats = dict(cursor.fetchone())
            
            # === COMBINE STATISTICS ===
            stats.update({
                'no_shows': no_show_stats,
                'bookings': booking_stats,
                'queue': {
                    'max_size': int(queue_stats['max_queue_size'] or 0),
                    'avg_size': round(queue_stats['avg_queue_size'], 1) if queue_stats['avg_queue_size'] else 0
                },
                'summary': {
                    'total_bookings': booking_stats['total_bookings'] or 0,
                    'completed_sessions': occupancy_stats['total_occupations'] or 0,
                    'no_shows': no_show_stats['no_show_count'] or 0,
                    'success_rate': round((occupancy_stats['total_occupations'] or 0) / max(booking_stats['total_bookings'] or 1, 1) * 100, 1),
                    'no_show_rate': round((no_show_stats['no_show_count'] or 0) / max(booking_stats['total_bookings'] or 1, 1) * 100, 1)
                }
            })
            
            return stats
    
    def get_daily_stats(self, date: datetime = None) -> Dict:
        """Get statistics for a specific day"""
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime('%Y-%m-%d')
        
        with self.get_connection() as conn:
            # Total occupations
            cursor = conn.execute("""
                SELECT COUNT(*) as total_occupations,
                       AVG(duration_minutes) as avg_duration,
                       SUM(duration_minutes) as total_minutes
                FROM occupancy_stats
                WHERE DATE(start_time) = ?
            """, (date_str,))
            stats = dict(cursor.fetchone())
            
            # Access type breakdown
            cursor = conn.execute("""
                SELECT access_type, COUNT(*) as count
                FROM occupancy_stats
                WHERE DATE(start_time) = ?
                GROUP BY access_type
            """, (date_str,))
            stats['access_types'] = {row['access_type']: row['count'] 
                                   for row in cursor.fetchall()}
            
            # No-show count
            cursor = conn.execute("""
                SELECT COUNT(*) as no_shows
                FROM events
                WHERE DATE(timestamp) = ? AND no_show = 1
            """, (date_str,))
            stats['no_shows'] = cursor.fetchone()['no_shows']
            
            return stats
    
    def get_average_occupation_time(self) -> Optional[int]:
        """Get average occupation time in minutes from recent data"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT AVG(duration_minutes) as avg_duration
                FROM occupancy_stats
                WHERE end_time IS NOT NULL 
                AND start_time >= datetime('now', '-7 days')
            """)
            result = cursor.fetchone()
            if result and result['avg_duration']:
                return int(result['avg_duration'])
            return None
    
    def get_weekly_stats(self, start_date: datetime = None) -> List[Dict]:
        """Get weekly statistics"""
        if start_date is None:
            start_date = datetime.now() - timedelta(days=7)
        
        stats = []
        for i in range(7):
            date = start_date + timedelta(days=i)
            daily_stats = self.get_daily_stats(date)
            daily_stats['date'] = date.strftime('%Y-%m-%d')
            stats.append(daily_stats)
        
        return stats
    
    def get_peak_hours(self, days: int = 7) -> List[Dict]:
        """Get peak usage hours"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT strftime('%H', start_time) as hour,
                       COUNT(*) as occupations
                FROM occupancy_stats
                WHERE start_time >= datetime('now', '-{} days')
                GROUP BY strftime('%H', start_time)
                ORDER BY occupations DESC
            """.format(days))
            return [dict(row) for row in cursor.fetchall()]
    
    # Configuration management
    def get_config(self, key: str) -> Optional[str]:
        """Get configuration value"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT value FROM config WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row['value'] if row else None
    
    def set_config(self, key: str, value: str, description: str = None):
        """Set configuration value"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO config (key, value, description, updated_at)
                VALUES (?, ?, ?, ?)
            """, (key, value, description, datetime.now().isoformat()))
            conn.commit()
    
    def get_all_config(self) -> Dict[str, str]:
        """Get all configuration values"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT key, value FROM config")
            return {row['key']: row['value'] for row in cursor.fetchall()}
    
    # System maintenance
    def cleanup_old_data(self, days: int = 30):
        """Clean up old data"""
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        with self.get_connection() as conn:
            # Clean old completed/no-show queue entries
            conn.execute("""
                DELETE FROM queue 
                WHERE timestamp < ? AND status IN ('completed', 'no_show')
            """, (cutoff_date,))
            
            # Clean old events (keep occupancy stats longer)
            conn.execute("""
                DELETE FROM events 
                WHERE timestamp < ?
            """, (cutoff_date,))
            
            # Clean old login attempts
            conn.execute("""
                DELETE FROM login_attempts 
                WHERE attempt_time < ?
            """, (cutoff_date,))
            
            conn.commit()
    
    def backup_database(self, backup_path: str = None) -> str:
        """Create database backup"""
        if backup_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"{Config.DATABASE_BACKUP_PATH}/backup_{timestamp}.db"
        
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        
        with self.get_connection() as conn:
            backup_conn = sqlite3.connect(backup_path)
            conn.backup(backup_conn)
            backup_conn.close()
        
        return backup_path
    
    def get_system_info(self) -> Dict:
        """Get system information"""
        with self.get_connection() as conn:
            info = {}
            
            # Database size
            info['db_size_mb'] = round(os.path.getsize(self.db_path) / (1024 * 1024), 2)
            
            # Record counts
            for table in ['users', 'queue', 'occupancy_stats', 'events']:
                cursor = conn.execute(f"SELECT COUNT(*) as count FROM {table}")
                info[f'{table}_count'] = cursor.fetchone()['count']
            
            # Current queue size
            cursor = conn.execute("SELECT COUNT(*) as count FROM queue WHERE status = 'waiting'")
            info['current_queue_size'] = cursor.fetchone()['count']
            
            # Today's activity
            today = datetime.now().strftime('%Y-%m-%d')
            cursor = conn.execute("""
                SELECT COUNT(*) as count FROM occupancy_stats 
                WHERE DATE(start_time) = ?
            """, (today,))
            info['today_occupations'] = cursor.fetchone()['count']
            
            return info

    def get_config_value(self, key: str, default_value=None):
        """Get a configuration value from database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT value FROM config WHERE key = ?", (key,))
                row = cursor.fetchone()
                if row:
                    return row['value']
                return default_value
        except Exception as e:
            self.logger.error(f"Error getting config value {key}: {e}")
            return default_value
    
    def set_config_value(self, key: str, value, description: str = None):
        """Set a configuration value in database"""
        try:
            with self.get_connection() as conn:
                # Convert value to string for storage
                str_value = str(value)
                
                conn.execute("""
                    INSERT OR REPLACE INTO config (key, value, description, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (key, str_value, description))
                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error setting config value {key}: {e}")
            return False
    
    def init_default_config(self):
        """Initialize default configuration values"""
        from config.config import Config
        
        default_configs = [
            ('reservation_timeout_minutes', Config.RESERVATION_TIMEOUT_MINUTES, 'Timeout prenotazione in minuti'),
            ('max_occupancy_minutes', Config.MAX_OCCUPANCY_MINUTES, 'Durata massima occupazione in minuti'),
            ('max_queue_size', Config.MAX_QUEUE_SIZE, 'Dimensione massima della coda'),
            ('movement_timeout_minutes', Config.MOVEMENT_TIMEOUT_MINUTES, 'Timeout movimento in minuti'),
            ('auto_reset_time', Config.AUTO_RESET_TIME, 'Orario reset automatico'),
            ('conflict_priority', Config.CONFLICT_PRIORITY, 'Priorità in caso di conflitto'),
            ('use_pir_sensor', Config.USE_PIR_SENSOR, 'Usa sensore PIR'),
            ('use_ultrasonic_sensor', Config.USE_ULTRASONIC_SENSOR, 'Usa sensore ultrasonico'),
            ('presence_threshold_cm', Config.PRESENCE_THRESHOLD_CM, 'Soglia presenza in cm'),
            ('dual_sensor_mode', Config.DUAL_SENSOR_MODE, 'Modalità sensori multipli'),
            ('pir_absence_seconds', Config.PIR_ABSENCE_SECONDS, 'Secondi assenza PIR'),
            ('ultrasonic_polling_seconds', Config.ULTRASONIC_POLLING_SECONDS, 'Frequenza polling ultrasonico'),
            ('pushover_enabled', Config.PUSHOVER_ENABLED, 'Abilita notifiche Pushover'),
            ('pushover_user_key', Config.PUSHOVER_USER_KEY, 'Chiave utente Pushover'),
            ('pushover_api_token', Config.PUSHOVER_API_TOKEN, 'Token API Pushover'),
            ('session_timeout_minutes', Config.SESSION_TIMEOUT_MINUTES, 'Timeout sessione admin'),
            ('max_login_attempts', Config.MAX_LOGIN_ATTEMPTS, 'Tentativi massimi login'),
            ('lockout_duration_minutes', Config.LOCKOUT_DURATION_MINUTES, 'Durata blocco login'),
        ]
        
        try:
            with self.get_connection() as conn:
                for key, value, description in default_configs:
                    # Solo se non esiste già
                    cursor = conn.execute("SELECT COUNT(*) as count FROM config WHERE key = ?", (key,))
                    if cursor.fetchone()['count'] == 0:
                        conn.execute("""
                            INSERT INTO config (key, value, description)
                            VALUES (?, ?, ?)
                        """, (key, str(value), description))
                conn.commit()
                self.logger.info("Default configuration initialized")
                return True
        except Exception as e:
            self.logger.error(f"Error initializing default config: {e}")
            return False
    
    def get_recent_events(self, limit=50):
        """
        Ottiene gli eventi recenti dal database per la dashboard admin
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT timestamp, event_type, details 
                    FROM events 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (limit,))
                
                events = []
                for row in cursor.fetchall():
                    # Formatta il timestamp per la dashboard
                    dt = datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S')
                    formatted_time = dt.strftime('%d/%m %H:%M')
                    
                    # Crea descrizione user-friendly
                    description = self._format_event_description(row['event_type'], row['details'])
                    
                    events.append({
                        'timestamp': formatted_time,
                        'event_type': row['event_type'],
                        'details': description
                    })
                
                return events
                
        except Exception as e:
            self.logger.error(f"Error getting recent events: {e}")
            return []
    
    def _format_event_description(self, event_type, details):
        """
        Formatta la descrizione dell'evento per la dashboard
        """
        if event_type == 'BOOKING_CREATED':
            return f"Prenotazione creata - {details}"
        elif event_type == 'BOOKING_ACTIVATED':
            return f"Turno attivato - {details}"
        elif event_type == 'BOOKING_CANCELLED':
            return f"Prenotazione cancellata - {details}"
        elif event_type == 'OFFICE_OCCUPIED':
            return f"Ufficio occupato - {details}"
        elif event_type == 'OFFICE_FREE':
            return f"Ufficio liberato - {details}"
        elif event_type == 'NO_SHOW':
            return f"No-show rilevato - {details}"
        elif event_type == 'CONFIG_CHANGED':
            return f"Configurazione modificata - {details}"
        elif event_type == 'QUEUE_POSITION_CHANGED':
            return f"Posizione in coda cambiata - {details}"
        elif event_type == 'QUEUE_CLEARED':
            return f"Coda svuotata - {details}"
        elif event_type == 'SYSTEM_RESET':
            return f"Sistema resettato - {details}"
        elif event_type == 'USER_ENTERED_OFFICE':
            return f"Utente entrato in ufficio - {details}"
        elif event_type == 'USER_LEFT_OFFICE':
            return f"Utente uscito dall'ufficio - {details}"
        elif event_type == 'SYSTEM_RECOVERY':
            return f"Sistema ripristinato dopo riavvio - {details}"
        elif event_type == 'NO_SHOW_CLEANUP':
            return f"Pulizia no-show al riavvio - {details}"
        elif event_type == 'RESERVATION_EXPIRED':
            return f"Prenotazione scaduta - {details}"
        else:
            return details or event_type
    
    def get_system_recovery_stats(self):
        """Get statistics about system recoveries and restarts"""
        try:
            with self.get_connection() as conn:
                # Count recoveries in last 30 days
                cursor = conn.execute("""
                    SELECT COUNT(*) as recovery_count
                    FROM events
                    WHERE event_type = 'SYSTEM_RECOVERY'
                    AND timestamp >= datetime('now', '-30 days')
                """)
                recovery_stats = dict(cursor.fetchone())
                
                # Get last recovery time
                cursor = conn.execute("""
                    SELECT timestamp, details
                    FROM events
                    WHERE event_type = 'SYSTEM_RECOVERY'
                    ORDER BY timestamp DESC
                    LIMIT 1
                """)
                last_recovery = cursor.fetchone()
                
                if last_recovery:
                    recovery_stats['last_recovery_time'] = last_recovery['timestamp']
                    recovery_stats['last_recovery_details'] = last_recovery['details']
                else:
                    recovery_stats['last_recovery_time'] = None
                    recovery_stats['last_recovery_details'] = None
                
                # Count no-shows from recovery cleanup
                cursor = conn.execute("""
                    SELECT COUNT(*) as cleanup_no_shows
                    FROM events
                    WHERE event_type IN ('NO_SHOW_CLEANUP', 'RESERVATION_EXPIRED')
                    AND timestamp >= datetime('now', '-30 days')
                """)
                cleanup_stats = dict(cursor.fetchone())
                recovery_stats.update(cleanup_stats)
                
                return recovery_stats
                
        except Exception as e:
            self.logger.error(f"Error getting recovery stats: {e}")
            return {
                'recovery_count': 0,
                'last_recovery_time': None,
                'last_recovery_details': None,
                'cleanup_no_shows': 0
            }
