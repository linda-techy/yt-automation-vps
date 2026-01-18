"""
Upload Locking Utilities

Prevents concurrent uploads of the same video file using file-based locks.
"""

import os
import logging
import time
from contextlib import contextmanager
from pathlib import Path

LOCK_DIR = "channel/upload_locks"


def _get_lock_path(file_path: str) -> str:
    """Get lock file path for a video file"""
    os.makedirs(LOCK_DIR, exist_ok=True)
    # Use hash of file path to create unique lock filename
    import hashlib
    file_hash = hashlib.md5(file_path.encode()).hexdigest()[:12]
    return os.path.join(LOCK_DIR, f"upload_{file_hash}.lock")


@contextmanager
def upload_lock(file_path: str, timeout: int = 300):
    """
    Context manager for upload locking.
    
    Prevents concurrent uploads of the same video file.
    
    Args:
        file_path: Path to video file being uploaded
        timeout: Maximum time to wait for lock (seconds)
    
    Usage:
        with upload_lock(video_path):
            # Upload video
            upload_short(video_path, ...)
    """
    lock_path = _get_lock_path(file_path)
    lock_acquired = False
    start_time = time.time()
    
    try:
        # Try to acquire lock
        while not lock_acquired and (time.time() - start_time) < timeout:
            try:
                # Create lock file atomically
                if not os.path.exists(lock_path):
                    # Try to create lock file
                    with open(lock_path, 'x') as f:
                        f.write(f"{os.getpid()}\n{time.time()}\n{file_path}\n")
                    lock_acquired = True
                    logging.debug(f"[UploadLock] Acquired lock for {os.path.basename(file_path)}")
                    break
                else:
                    # Check if lock is stale (older than 1 hour)
                    lock_age = time.time() - os.path.getmtime(lock_path)
                    if lock_age > 3600:  # 1 hour
                        logging.warning(f"[UploadLock] Removing stale lock: {lock_path} (age: {lock_age:.0f}s)")
                        try:
                            os.remove(lock_path)
                        except Exception as e:
                            logging.warning(f"[UploadLock] Failed to remove stale lock: {e}")
                    else:
                        # Lock exists and is fresh - wait
                        time.sleep(1)
            except FileExistsError:
                # Lock file created by another process - wait
                time.sleep(1)
            except Exception as e:
                logging.warning(f"[UploadLock] Error acquiring lock: {e}")
                time.sleep(1)
        
        if not lock_acquired:
            raise TimeoutError(f"Failed to acquire upload lock for {file_path} within {timeout}s")
        
        yield
        
    finally:
        # Release lock
        if lock_acquired and os.path.exists(lock_path):
            try:
                os.remove(lock_path)
                logging.debug(f"[UploadLock] Released lock for {os.path.basename(file_path)}")
            except Exception as e:
                logging.warning(f"[UploadLock] Failed to release lock: {e}")
