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
    
    # Get schedule from config
    try:
        from services.config_loader import config
        run_time = config.get("schedule.upload_time", "19:00")
        timezone = config.get("schedule.timezone", "Asia/Kolkata")
    except Exception as e:
        logging.warning(f"Config load failed: {e}, using defaults")
        run_time = "19:00"
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
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main()
