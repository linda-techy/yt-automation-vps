"""
YouTube Automation Daemon - Stay-Alive Mode for VPS

Runs continuously with PM2, executing the pipeline daily at configured time.
This is the production deployment script for VPS.

Usage:
    pm2 start daemon.py --name "yt-automation"
    pm2 save
    pm2 startup
"""

import time
import datetime
import logging
import schedule
import signal
import sys
import pytz
from pipeline import run_unified_pipeline, validate_environment

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/daemon.log'),
        logging.StreamHandler()
    ]
)

def run_pipeline_job():
    """Execute the pipeline with error handling"""
    logging.info("="*60)
    logging.info("DAEMON: Starting scheduled pipeline run")
    logging.info("============================================================")
    
    try:
        run_unified_pipeline()
        logging.info("DAEMON: Pipeline completed successfully")
    except Exception as e:
        logging.error(f"DAEMON: Pipeline failed: {e}")
        # Don't crash the daemon - log and continue

def graceful_shutdown(signum, frame):
    """Handle shutdown signals gracefully"""
    logging.info(f"Shutdown signal received ({signal.Signals(signum).name}). Exiting...")
    sys.exit(0)

def main():
    """Main daemon loop"""
    # Register signal handlers
    signal.signal(signal.SIGINT, graceful_shutdown)
    signal.signal(signal.SIGTERM, graceful_shutdown)
    print("\n" + "="*60)
    print("YOUTUBE AUTOMATION DAEMON - FinMindMalayalam")
    print("="*60)
    
    # Validate environment on startup
    validate_environment()
    
    # Run health check
    try:
        from services.health_monitor import get_health_monitor
        health = get_health_monitor()
        results = health.run_full_health_check()
        
        if results['overall_healthy']:
            logging.info("✅ Health check passed - all systems operational")
        else:
            logging.warning("⚠️ Health check found issues - check logs/daemon.log")
            
            # Log specific issues
            if not results['disk']['healthy']:
                logging.error(f"Disk space low: {results['disk']['free_gb']}GB free")
            if not results['memory']['healthy']:
                logging.error(f"Memory low: {results['memory']['available_gb']}GB available")
            if not results['dependencies']['healthy']:
                missing_deps = [k for k, v in results['dependencies']['dependencies'].items() if not v]
                logging.error(f"Missing dependencies: {missing_deps}")
                
            print("\n⚠️  WARNING: System health check found issues. Check logs for details.\n")
    except Exception as e:
        logging.warning(f"Health check failed: {e}")
    
    # Get schedule from config (use channel_config for consistency)
    try:
        from config.channel import channel_config
        run_time = channel_config.upload_time
        timezone = channel_config.timezone
        logging.info(f"Loaded schedule config: {run_time} ({timezone})")
    except Exception as e:
        logging.warning(f"Config load failed: {e}, using defaults")
        run_time = "15:30"  # Default IST time from channel_config.yaml
        timezone = "Asia/Kolkata"
    
    logging.info(f"Scheduled runs: Monday, Wednesday, Friday at {run_time} ({timezone})")
    logging.info(f"Pipeline will generate content and schedule uploads")
    logging.info(f"Daemon will stay alive and run 3x/week")
    print("="*60 + "\n")
    
    # Schedule 3x per week (Mon, Wed, Fri) - optimal for YPP and algorithm
    # Using timezone explicitly to ensure IST 19:00 trigger checks
    schedule.every().monday.at(run_time, timezone).do(run_pipeline_job)
    schedule.every().wednesday.at(run_time, timezone).do(run_pipeline_job)
    schedule.every().friday.at(run_time, timezone).do(run_pipeline_job)
    
    # Also run immediately on first start (optional - comment out if not needed)
    # run_pipeline_job()
    
    logging.info(f"⏰ Next run scheduled for: {schedule.next_run()}")
    
    # Keep alive loop
    last_cleanup_time = datetime.datetime.now(datetime.timezone.utc)
    cleanup_interval_hours = 6  # Run cleanup every 6 hours
    last_health_check_time = datetime.datetime.now(datetime.timezone.utc)
    health_check_interval_hours = 1  # Run health check every hour
    
    while True:
        # Check for scheduled uploads first (runs every minute)
        try:
            from services.upload_worker import check_and_upload_pending
            upload_results = check_and_upload_pending()
            if upload_results["uploaded"] > 0 or upload_results["failed"] > 0:
                logging.info(f"📤 Upload worker: {upload_results['uploaded']} uploaded, {upload_results['failed']} failed, {upload_results['pending']} pending")
        except Exception as e:
            logging.warning(f"Upload worker error: {e}")
        
        # Periodic health check (every hour)
        now = datetime.datetime.now(datetime.timezone.utc)
        if (now - last_health_check_time).total_seconds() >= health_check_interval_hours * 3600:
            try:
                from services.health_monitor import get_health_monitor, get_recovery_manager
                health = get_health_monitor()
                results = health.run_full_health_check()
                
                if not results['overall_healthy']:
                    logging.warning("⚠️ Periodic health check found issues")
                    # Log specific issues
                    if not results['disk']['healthy']:
                        logging.error(f"Disk space low: {results['disk']['free_gb']}GB free")
                    if not results['memory']['healthy']:
                        logging.error(f"Memory low: {results['memory']['available_gb']}GB available")
                    if not results['dependencies']['healthy']:
                        missing_deps = [k for k, v in results['dependencies']['dependencies'].items() if not v]
                        logging.error(f"Missing dependencies: {missing_deps}")
                    
                    # Attempt recovery
                    recovery = get_recovery_manager()
                    recovery.cleanup_stale_files(max_age_hours=24)
                
                last_health_check_time = now
            except Exception as e:
                logging.warning(f"Periodic health check error: {e}")
        
        # Periodic cleanup (every 6 hours)
        if (now - last_cleanup_time).total_seconds() >= cleanup_interval_hours * 3600:
            try:
                from services.video_lifecycle_manager import cleanup_uploaded_videos, cleanup_temp_files
                deleted_count = cleanup_uploaded_videos(max_age_hours=48)
                if deleted_count > 0:
                    logging.info(f"🗑️ Periodic cleanup: Deleted {deleted_count} old videos")
                cleanup_temp_files()
                last_cleanup_time = now
            except Exception as e:
                logging.warning(f"Periodic cleanup error: {e}")
        
        # Then check for pipeline jobs
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main()
