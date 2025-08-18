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
                "UPDATE queue SET status = 'no_show' WHERE user_code = ? AND status = 'waiting'",
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
    
    def get_average_occupation_time(self, days: int = 7) -> Optional[float]:
        """Get average occupation time in minutes"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT AVG(duration_minutes) as avg_duration
                FROM occupancy_stats
                WHERE start_time >= datetime('now', '-{} days')
                AND duration_minutes IS NOT NULL
            """.format(days))
            row = cursor.fetchone()
            return row['avg_duration'] if row and row['avg_duration'] else None
    
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
