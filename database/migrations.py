"""
Database migration utilities
Handles schema updates and data migrations
"""

import sqlite3
from datetime import datetime
from typing import List, Callable
import logging

class Migration:
    """Represents a single database migration"""
    
    def __init__(self, version: int, description: str, up_func: Callable, down_func: Callable = None):
        self.version = version
        self.description = description
        self.up_func = up_func
        self.down_func = down_func
        self.timestamp = datetime.now()

class MigrationManager:
    """Manages database migrations"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self.migrations: List[Migration] = []
        
        # Register migrations
        self._register_migrations()
    
    def _register_migrations(self):
        """Register all migrations"""
        
        # Migration 1: Initial schema (already handled by db_manager)
        self.migrations.append(Migration(
            version=1,
            description="Initial database schema",
            up_func=self._migration_001_initial_schema
        ))
        
        # Migration 2: Add indexes for performance
        self.migrations.append(Migration(
            version=2,
            description="Add database indexes",
            up_func=self._migration_002_add_indexes
        ))
        
        # Migration 3: Add user management enhancements
        self.migrations.append(Migration(
            version=3,
            description="User management enhancements",
            up_func=self._migration_003_user_enhancements
        ))
    
    def _ensure_migrations_table(self, conn: sqlite3.Connection):
        """Ensure migrations table exists"""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS migrations (
                version INTEGER PRIMARY KEY,
                description TEXT NOT NULL,
                applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    def get_current_version(self) -> int:
        """Get current database version"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                self._ensure_migrations_table(conn)
                cursor = conn.execute("SELECT MAX(version) as version FROM migrations")
                row = cursor.fetchone()
                return row[0] if row[0] is not None else 0
        except Exception as e:
            self.logger.error(f"Error getting current version: {e}")
            return 0
    
    def apply_migrations(self) -> bool:
        """Apply all pending migrations"""
        try:
            current_version = self.get_current_version()
            pending_migrations = [m for m in self.migrations if m.version > current_version]
            
            if not pending_migrations:
                self.logger.info("No pending migrations")
                return True
            
            with sqlite3.connect(self.db_path) as conn:
                self._ensure_migrations_table(conn)
                
                for migration in pending_migrations:
                    self.logger.info(f"Applying migration {migration.version}: {migration.description}")
                    
                    try:
                        # Apply migration
                        migration.up_func(conn)
                        
                        # Record migration
                        conn.execute(
                            "INSERT INTO migrations (version, description) VALUES (?, ?)",
                            (migration.version, migration.description)
                        )
                        
                        conn.commit()
                        self.logger.info(f"Migration {migration.version} applied successfully")
                        
                    except Exception as e:
                        conn.rollback()
                        self.logger.error(f"Failed to apply migration {migration.version}: {e}")
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error applying migrations: {e}")
            return False
    
    # Migration functions
    def _migration_001_initial_schema(self, conn: sqlite3.Connection):
        """Migration 1: Initial schema (no-op, handled by db_manager)"""
        pass
    
    def _migration_002_add_indexes(self, conn: sqlite3.Connection):
        """Migration 2: Add performance indexes"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_queue_user_status ON queue(user_code, status)",
            "CREATE INDEX IF NOT EXISTS idx_occupancy_user ON occupancy_stats(user_code)",
            "CREATE INDEX IF NOT EXISTS idx_occupancy_type ON occupancy_stats(access_type)",
            "CREATE INDEX IF NOT EXISTS idx_events_user ON events(user_code)",
            "CREATE INDEX IF NOT EXISTS idx_events_date ON events(DATE(timestamp))",
        ]
        
        for index_sql in indexes:
            conn.execute(index_sql)
    
    def _migration_003_user_enhancements(self, conn: sqlite3.Connection):
        """Migration 3: User management enhancements"""
        # Add email and active status to users table
        try:
            conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            conn.execute("ALTER TABLE users ADD COLUMN active BOOLEAN DEFAULT TRUE")
        except sqlite3.OperationalError:
            pass  # Column already exists
        
        try:
            conn.execute("ALTER TABLE users ADD COLUMN last_used DATETIME")
        except sqlite3.OperationalError:
            pass  # Column already exists
