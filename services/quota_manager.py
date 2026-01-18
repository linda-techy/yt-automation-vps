"""
Persistent Quota Manager with SQLite Backend

Survives daemon restarts and provides accurate quota tracking.
Essential for production VPS deployments.

IMPORTANT: YouTube API quota resets at midnight Pacific Time (PT), NOT IST.
This is a YouTube API requirement and cannot be changed.
Quota resets at 00:00:00 PT = 12:30:00 IST (next day) or 13:30:00 IST (next day during DST).
"""

import sqlite3
import logging
import os
import pytz
from datetime import datetime, timedelta
from contextlib import contextmanager
from pathlib import Path

class PersistentQuotaManager:
    """Thread-safe persistent quota tracker using SQLite"""
    
    def __init__(self, db_path="channel/quota_tracker.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
        
    def _init_database(self):
        """Create database schema if not exists"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS quota_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation TEXT NOT NULL,
                    cost INTEGER NOT NULL,
                    timestamp DATETIME NOT NULL,
                    reset_at DATETIME NOT NULL,
                    metadata TEXT
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON quota_usage(timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_reset_at 
                ON quota_usage(reset_at)
            """)
            
            conn.commit()
            
    @contextmanager
    def _get_connection(self):
        """Thread-safe database connection context manager"""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
            
    def get_reset_time(self):
        """Get next quota reset time (midnight Pacific Time)"""
        import pytz
        pacific = pytz.timezone('America/Los_Angeles')
        now = datetime.now(pacific)
        
        # Next reset is at midnight PT (00:00:00)
        # Calculate today's midnight PT
        today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # If we're past midnight today, reset is tomorrow's midnight
        if now >= today_midnight:
            reset_at = today_midnight + timedelta(days=1)
        else:
            # Shouldn't happen, but handle edge case
            reset_at = today_midnight
            
        return reset_at
        
    def get_current_usage(self, daily_quota=10000):
        """Get current quota usage, auto-reset if new day"""
        reset_time = self.get_reset_time()
        
        with self._get_connection() as conn:
            # Cleanup old records beyond reset time (use UTC for consistency)
            now_utc = datetime.now(pytz.UTC)
            conn.execute("DELETE FROM quota_usage WHERE reset_at < ?", (now_utc,))
            conn.commit()
            
            # Sum current period usage
            result = conn.execute("""
                SELECT COALESCE(SUM(cost), 0) as total
                FROM quota_usage
                WHERE timestamp >= datetime('now', '-1 day')
                AND reset_at > datetime('now')
            """).fetchone()
            
            used = result['total'] if result else 0
            remaining = daily_quota - used
            
            return {
                'used': used,
                'remaining': remaining,
                'limit': daily_quota,
                'reset_at': reset_time.isoformat(),
                'percentage': (used / daily_quota * 100) if daily_quota > 0 else 0
            }
            
    def record_usage(self, operation, cost, metadata=None):
        """Record quota usage"""
        reset_time = self.get_reset_time()
        
        with self._get_connection() as conn:
            # Use UTC for timestamp consistency
            now_utc = datetime.now(pytz.UTC)
            conn.execute("""
                INSERT INTO quota_usage (operation, cost, timestamp, reset_at, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (operation, cost, now_utc, reset_time, metadata))
            conn.commit()
            
        logging.info(f"[QuotaManager] Recorded {operation}: {cost} units")
        
    def check_available(self, operation='upload', daily_quota=10000):
        """Check if quota is available for operation"""
        quota_costs = {
            'upload': 1600,
            'comment': 50,
            'update': 50,
            'list': 1,
            'thumbnail': 0  # Free operation
        }
        
        cost = quota_costs.get(operation, 1)
        status = self.get_current_usage(daily_quota)
        
        if status['remaining'] < cost:
            raise QuotaExceededError(
                f"Insufficient quota for {operation}. "
                f"Need {cost}, have {status['remaining']}. "
                f"Resets at {status['reset_at']}"
            )
            
        return True
        
    def get_usage_history(self, days=7):
        """Get quota usage history for analytics"""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT operation, cost, timestamp
                FROM quota_usage
                WHERE timestamp >= datetime('now', '-{} days')
                ORDER BY timestamp DESC
            """.format(days)).fetchall()
            
            return [dict(row) for row in rows]


class QuotaExceededError(Exception):
    """Raised when quota limit is reached"""
    # Exception class definition - pass is standard here
    pass


# Global instance
_quota_manager = None

def get_quota_manager():
    """Get or create global quota manager instance"""
    global _quota_manager
    if _quota_manager is None:
        _quota_manager = PersistentQuotaManager()
    return _quota_manager


if __name__ == "__main__":
    # Test the manager
    manager = PersistentQuotaManager("test_quota.db")
    
    print("Testing quota manager...")
    
    # Simulate uploads
    for i in range(3):
        try:
            manager.check_available('upload')
            manager.record_usage('upload', 1600, f"test_video_{i}")
            status = manager.get_current_usage()
            print(f"Upload {i+1}: Success. Used {status['used']}/{status['limit']} ({status['percentage']:.1f}%)")
        except QuotaExceededError as e:
            print(f"Upload {i+1}: Blocked - {e}")
            
    # Cleanup
    os.remove("test_quota.db")
