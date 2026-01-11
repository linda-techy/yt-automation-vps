"""
Production Health Monitor and Error Recovery System

Monitors system health, tracks failures, and implements self-healing mechanisms.
Essential for production VPS deployments with minimal human intervention.
"""

import os
import json
import logging
import traceback
import psutil
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

class HealthMonitor:
    """System health monitoring and diagnostics"""
    
    def __init__(self, config_path="channel/health_status.json"):
        self.config_path = config_path
        Path(config_path).parent.mkdir(parents=True, exist_ok=True)
        
    def check_disk_space(self, min_gb=5):
        """Check available disk space"""
        try:
            usage = shutil.disk_usage("/")
            free_gb = usage.free / (1024**3)
            
            status = {
                'free_gb': round(free_gb, 2),
                'total_gb': round(usage.total / (1024**3), 2),
                'used_percent': round((usage.used / usage.total) * 100, 1),
                'healthy': free_gb >= min_gb
            }
            
            if not status['healthy']:
                logging.warning(f"[Health] Low disk space: {free_gb:.1f}GB free (min: {min_gb}GB)")
                
            return status
        except Exception as e:
            logging.error(f"[Health] Disk check failed: {e}")
            return {'healthy': False, 'error': str(e)}
            
    def check_memory(self, min_available_percent=20):
        """Check available RAM"""
        try:
            mem = psutil.virtual_memory()
            
            status = {
                'available_gb': round(mem.available / (1024**3), 2),
                'total_gb': round(mem.total / (1024**3), 2),
                'used_percent': mem.percent,
                'healthy': mem.available / mem.total * 100 >= min_available_percent
            }
            
            if not status['healthy']:
                logging.warning(f"[Health] Low memory: {status['available_gb']}GB available ({100-mem.percent:.1f}% free)")
                
            return status
        except Exception as e:
            logging.error(f"[Health] Memory check failed: {e}")
            return {'healthy': False, 'error': str(e)}
            
    def check_dependencies(self):
        """Verify critical dependencies are available"""
        dependencies = {
            'ffmpeg': shutil.which('ffmpeg'),
            'openai_key': bool(os.getenv('OPENAI_API_KEY')),
            'youtube_credentials': os.path.exists('token.pickle'),
            'python_packages': True  # Assume OK if we're running
        }
        
        all_healthy = all(dependencies.values())
        
        if not all_healthy:
            missing = [k for k, v in dependencies.items() if not v]
            logging.error(f"[Health] Missing dependencies: {missing}")
            
        return {
            'dependencies': dependencies,
            'healthy': all_healthy
        }
        
    def check_file_permissions(self):
        """Check write permissions for critical directories"""
        critical_dirs = ['videos/output', 'videos/temp', 'logs', 'channel']
        issues = []
        
        for dir_path in critical_dirs:
            if not os.path.exists(dir_path):
                try:
                    os.makedirs(dir_path, exist_ok=True)
                except Exception as e:
                    issues.append(f"{dir_path}: cannot create - {e}")
            elif not os.access(dir_path, os.W_OK):
                issues.append(f"{dir_path}: no write permission")
                
        return {
            'healthy': len(issues) == 0,
            'issues': issues
        }
        
    def run_full_health_check(self):
        """Run comprehensive health check"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'disk': self.check_disk_space(),
            'memory': self.check_memory(),
            'dependencies': self.check_dependencies(),
            'permissions': self.check_file_permissions()
        }
        
        overall_health = all([
            results['disk'].get('healthy', False),
            results['memory'].get('healthy', False),
            results['dependencies'].get('healthy', False),
            results['permissions'].get('healthy', False)
        ])
        
        results['overall_healthy'] = overall_health
        
        # Save status
        try:
            with open(self.config_path, 'w') as f:
                json.dump(results, f, indent=2)
        except Exception as e:
            logging.error(f"[Health] Failed to save status: {e}")
            
        return results


class ErrorRecoveryManager:
    """Automatic error recovery and retry coordination"""
    
    def __init__(self, history_path="channel/error_history.json"):
        self.history_path = history_path
        Path(history_path).parent.mkdir(parents=True, exist_ok=True)
        
    def record_error(self, error_type: str, error_message: str, context: Dict = None):
        """Record error for pattern analysis"""
        error_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': error_type,
            'message': error_message,
            'context': context or {},
            'traceback': traceback.format_exc()
        }
        
        history = []
        if os.path.exists(self.history_path):
            try:
                with open(self.history_path, 'r') as f:
                    history = json.load(f)
            except:
                history = []
                
        history.append(error_entry)
        
        # Keep last 100 errors only
        history = history[-100:]
        
        with open(self.history_path, 'w') as f:
            json.dump(history, f, indent=2)
            
        logging.error(f"[Recovery] Recorded error: {error_type} - {error_message}")
        
    def get_recent_errors(self, hours=24) -> List[Dict]:
        """Get errors from last N hours"""
        if not os.path.exists(self.history_path):
            return []
            
        cutoff = datetime.now() - timedelta(hours=hours)
        
        try:
            with open(self.history_path, 'r') as f:
                history = json.load(f)
                
            return [
                e for e in history
                if datetime.fromisoformat(e['timestamp']) > cutoff
            ]
        except:
            return []
            
    def detect_error_patterns(self) -> Dict:
        """Detect recurring error patterns"""
        recent = self.get_recent_errors(hours=24)
        
        if not recent:
            return {'has_pattern': False}
            
        error_types = {}
        for error in recent:
            err_type = error.get('type', 'unknown')
            error_types[err_type] = error_types.get(err_type, 0) + 1
            
        # Detect if same error happens >= 3 times in 24h
        recurring = {k: v for k, v in error_types.items() if v >= 3}
        
        return {
            'has_pattern': len(recurring) > 0,
            'recurring_errors': recurring,
            'total_errors_24h': len(recent)
        }
        
    def should_retry(self, operation: str, max_retries=3) -> bool:
        """Determine if operation should be retried based on history"""
        recent = self.get_recent_errors(hours=1)
        operation_failures = [e for e in recent if e.get('context', {}).get('operation') == operation]
        
        return len(operation_failures) < max_retries
        
    def cleanup_stale_files(self, max_age_hours=48):
        """Clean up old temporary files to prevent disk filling"""
        cleaned = {'count': 0, 'bytes_freed': 0}
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        
        temp_dirs = ['videos/temp', 'videos/output']
        
        for temp_dir in temp_dirs:
            if not os.path.exists(temp_dir):
                continue
                
            for item in Path(temp_dir).glob('*'):
                try:
                    if item.is_file():
                        mtime = datetime.fromtimestamp(item.stat().st_mtime)
                        if mtime < cutoff:
                            size = item.stat().st_size
                            item.unlink()
                            cleaned['count'] += 1
                            cleaned['bytes_freed'] += size
                except Exception as e:
                    logging.warning(f"[Recovery] Failed to clean {item}: {e}")
                    
        if cleaned['count'] > 0:
            mb_freed = cleaned['bytes_freed'] / (1024**2)
            logging.info(f"[Recovery] Cleaned {cleaned['count']} stale files ({mb_freed:.1f}MB freed)")
            
        return cleaned


# Global instances
_health_monitor = None
_recovery_manager = None

def get_health_monitor():
    """Get global health monitor instance"""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor

def get_recovery_manager():
    """Get global recovery manager instance"""
    global _recovery_manager
    if _recovery_manager is None:
        _recovery_manager = ErrorRecoveryManager()
    return _recovery_manager


if __name__ == "__main__":
    # Test health monitoring
    print("Running health check...")
    monitor = HealthMonitor("test_health.json")
    results = monitor.run_full_health_check()
    
    print(f"\nHealth Status: {'✅ HEALTHY' if results['overall_healthy'] else '❌ ISSUES FOUND'}")
    print(f"Disk: {results['disk']['free_gb']}GB free")
    print(f"Memory: {results['memory']['available_gb']}GB available")
    print(f"Dependencies: {results['dependencies']['healthy']}")
    
    # Test error recovery
    print("\nTesting error recovery...")
    recovery = ErrorRecoveryManager("test_errors.json")
    recovery.record_error("TestError", "This is a test", {"operation": "test"})
    
    patterns = recovery.detect_error_patterns()
    print(f"Error patterns: {patterns}")
    
    # Cleanup
    os.remove("test_health.json")
    os.remove("test_errors.json")
