"""
File Locking Utilities for Thread-Safe JSON Database Operations

Provides cross-platform file locking for JSON-based databases to prevent
race conditions when multiple processes access the same files.
"""

import os
import logging
import json
from contextlib import contextmanager
from typing import Dict, Any

try:
    import fcntl  # Unix/Linux
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False
    try:
        import msvcrt  # Windows
        HAS_MSVCRT = True
    except ImportError:
        HAS_MSVCRT = False


@contextmanager
def locked_file(filepath: str, mode: str = 'r+'):
    """
    Context manager for file locking (cross-platform).
    
    Args:
        filepath: Path to file to lock
        mode: File mode ('r', 'r+', 'w', etc.)
    
    Usage:
        with locked_file('data.json', 'r+') as f:
            data = json.load(f)
            data['key'] = 'value'
            f.seek(0)
            json.dump(data, f)
            f.truncate()
    """
    if not os.path.exists(filepath) and 'r' in mode:
        # Create empty file if reading and doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump({}, f)
    
    with open(filepath, mode) as f:
        try:
            if HAS_FCNTL:
                # Unix/Linux locking
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            elif HAS_MSVCRT:
                # Windows locking
                msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
            else:
                # No locking available - log warning
                logging.warning(f"[FileLock] No file locking available on this platform. Race conditions possible.")
            
            yield f
            
        finally:
            try:
                if HAS_FCNTL:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                elif HAS_MSVCRT:
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            except Exception as e:
                logging.warning(f"[FileLock] Failed to unlock file {filepath}: {e}")


def load_json_safe(filepath: str, default: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Load JSON file with file locking.
    
    Args:
        filepath: Path to JSON file
        default: Default value if file doesn't exist or is corrupted
    
    Returns:
        Loaded JSON data or default value
    """
    if default is None:
        default = {}
    
    if not os.path.exists(filepath):
        return default
    
    try:
        with locked_file(filepath, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logging.error(f"[FileLock] Failed to parse JSON file {filepath}: {e}")
        # Backup corrupted file
        backup_path = f"{filepath}.corrupted.{os.path.getmtime(filepath)}"
        try:
            import shutil
            shutil.copy2(filepath, backup_path)
            logging.warning(f"[FileLock] Backed up corrupted file to {backup_path}")
        except Exception as backup_error:
            logging.error(f"[FileLock] Failed to backup corrupted file: {backup_error}")
        return default
    except Exception as e:
        logging.error(f"[FileLock] Failed to load JSON file {filepath}: {e}", exc_info=True)
        return default


def save_json_safe(filepath: str, data: Dict[str, Any]) -> bool:
    """
    Save JSON file with file locking.
    
    Args:
        filepath: Path to JSON file
        data: Data to save
    
    Returns:
        True if successful, False otherwise
    """
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Write to temp file first, then rename (atomic on most filesystems)
        temp_path = f"{filepath}.tmp"
        with locked_file(temp_path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Atomic rename
        if os.path.exists(filepath):
            os.replace(temp_path, filepath)
        else:
            os.rename(temp_path, filepath)
        
        return True
    except Exception as e:
        logging.error(f"[FileLock] Failed to save JSON file {filepath}: {e}", exc_info=True)
        # Clean up temp file if it exists
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except:
            pass
        return False
