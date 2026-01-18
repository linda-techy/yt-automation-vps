"""
Daemon Status Checker

Quick script to check if daemon is running and view recent logs.
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

def check_daemon_log():
    """Check daemon log file for recent activity"""
    log_file = "logs/daemon.log"
    
    if not os.path.exists(log_file):
        print(f"[ERROR] Log file not found: {log_file}")
        return False
    
    # Read last 50 lines
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
        if not lines:
            print(f"[WARNING] Log file is empty: {log_file}")
            return False
        
        print(f"\n{'='*60}")
        print(f"DAEMON LOG (Last 30 lines from {log_file})")
        print(f"{'='*60}\n")
        
        # Show last 30 lines
        for line in lines[-30:]:
            print(line.rstrip())
        
        print(f"\n{'='*60}")
        print(f"Total log lines: {len(lines)}")
        
        # Check last log time
        if lines:
            last_line = lines[-1].strip()
            if last_line:
                print(f"Last log entry: {last_line[:80]}...")
        
        return True
    except Exception as e:
        print(f"[ERROR] Failed to read log file: {e}")
        return False

def check_health_status():
    """Check health status file"""
    health_file = "channel/health_status.json"
    
    if not os.path.exists(health_file):
        print(f"\n[INFO] Health status file not found: {health_file}")
        return
    
    try:
        with open(health_file, 'r', encoding='utf-8') as f:
            health = json.load(f)
        
        print(f"\n{'='*60}")
        print("HEALTH STATUS")
        print(f"{'='*60}\n")
        
        if 'timestamp' in health:
            print(f"Last check: {health['timestamp']}")
        
        if 'overall_healthy' in health:
            status = "HEALTHY" if health['overall_healthy'] else "ISSUES FOUND"
            print(f"Status: {status}")
        
        if 'disk' in health:
            disk = health['disk']
            print(f"Disk: {disk.get('free_gb', 'N/A')}GB free ({disk.get('used_percent', 'N/A')}% used)")
        
        if 'memory' in health:
            mem = health['memory']
            print(f"Memory: {mem.get('available_gb', 'N/A')}GB available ({mem.get('used_percent', 'N/A')}% used)")
        
        if 'dependencies' in health:
            deps = health['dependencies']
            print(f"Dependencies: {'OK' if deps.get('healthy') else 'MISSING'}")
            if not deps.get('healthy'):
                missing = [k for k, v in deps.get('dependencies', {}).items() if not v]
                if missing:
                    print(f"  Missing: {', '.join(missing)}")
        
    except Exception as e:
        print(f"\n[ERROR] Failed to read health status: {e}")

def check_upload_status():
    """Check pending uploads"""
    status_file = "channel/upload_status.json"
    
    if not os.path.exists(status_file):
        print(f"\n[INFO] Upload status file not found: {status_file}")
        return
    
    try:
        with open(status_file, 'r', encoding='utf-8') as f:
            status = json.load(f)
        
        pending = status.get('pending_uploads', [])
        
        print(f"\n{'='*60}")
        print("UPLOAD STATUS")
        print(f"{'='*60}\n")
        
        print(f"Pending uploads: {len(pending)}")
        
        if pending:
            for i, item in enumerate(pending[:10], 1):  # Show first 10
                file_path = os.path.basename(item.get('file_path', 'unknown'))
                scheduled = item.get('scheduled_time', 'unknown')
                vtype = item.get('video_type', 'unknown')
                attempts = item.get('attempts', 0)
                
                print(f"  {i}. {vtype}: {file_path[:40]}")
                print(f"     Scheduled: {scheduled}")
                if attempts > 0:
                    print(f"     Attempts: {attempts}")
        
        uploaded = status.get('uploaded_videos', [])
        if uploaded:
            print(f"\nUploaded videos: {len(uploaded)}")
        
    except Exception as e:
        print(f"\n[ERROR] Failed to read upload status: {e}")

def main():
    """Main status check"""
    print("="*60)
    print("DAEMON STATUS CHECKER")
    print("="*60)
    print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Check log file
    has_logs = check_daemon_log()
    
    # Check health
    check_health_status()
    
    # Check uploads
    check_upload_status()
    
    print(f"\n{'='*60}")
    print("QUICK COMMANDS:")
    print(f"{'='*60}")
    print("View full log:      type logs\\daemon.log | more")
    print("View last 50 lines: Get-Content logs\\daemon.log -Tail 50")
    print("Follow log (live):  Get-Content logs\\daemon.log -Wait -Tail 20")
    print("Check processes:    Get-Process python")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
