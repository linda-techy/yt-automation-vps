"""
Smart Scheduler - Config-Driven Timezone Aware Uploads

Calculates optimal publish time based on channel_config.yaml:
- Respects configured Timezone (e.g. Asia/Kolkata)
- Respects configured Upload Time (e.g. 19:00)
- Adds human-like jitter (+/- 15 mins)
- Returns ISO format for YouTube API
"""

import datetime
import random
import pytz
import logging

# Import channel configuration
try:
    from config.channel import channel_config
    CONFIG_LOADED = True
except ImportError:
    CONFIG_LOADED = False
    print("[Scheduler] WARNING: channel_config not found, using defaults")


def get_smart_publish_time():
    """
    Calculates the next optimal publish time based on config.
    Returns: ISO 8601 string (YYYY-MM-DDThh:mm:ss.sZ)
    """
    if CONFIG_LOADED:
        tz_name = channel_config.timezone
        upload_time_str = channel_config.upload_time
    else:
        tz_name = "UTC"
        upload_time_str = "12:00"

    try:
        # Get current time in target timezone
        target_tz = pytz.timezone(tz_name)
        now_local = datetime.datetime.now(target_tz)
        
        # KERALA-OPTIMIZED: Day-aware scheduling for maximum engagement
        weekday = now_local.weekday()  # 0=Mon, 6=Sun
        
        # Get weekday times from config
        scheduler_config = channel_config.get("scheduler", {})
        weekday_times = scheduler_config.get("weekday_times", {})
        buffer_hours = scheduler_config.get("buffer_hours", 2)
        jitter_range = scheduler_config.get("jitter_minutes", [-10, 10])
        
        # Map weekday to day name
        day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        day_name = day_names[weekday]
        
        # Get time for this weekday from config, fallback to defaults
        if day_name in weekday_times:
            hour, minute = weekday_times[day_name]
        else:
            # Fallback defaults
            if weekday == 4:  # Friday
                hour, minute = 20, 0
            elif weekday == 5:  # Saturday
                hour, minute = 19, 0
            elif weekday == 6:  # Sunday
                hour, minute = 18, 30
            elif weekday == 0:  # Monday
                hour, minute = 20, 30
            else:  # Tue-Thu
                hour, minute = 21, 0
        
        # Create candidate time for TODAY
        target_today = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # If today's slot is passed (or too close), schedule for TOMORROW
        # Buffer: allow upload if at least buffer_hours before slot
        if now_local > (target_today - datetime.timedelta(hours=buffer_hours)):
            publish_time = target_today + datetime.timedelta(days=1)
        else:
            publish_time = target_today
            
        # Add natural jitter (from config) to look organic
        jitter = random.randint(jitter_range[0], jitter_range[1])
        publish_time += datetime.timedelta(minutes=jitter)
        
        # Convert back to UTC for YouTube API
        utc_time = publish_time.astimezone(pytz.UTC)
        
        # Format: 2024-12-25T19:00:00.000Z
        iso_time = utc_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        
        print(f"[Scheduler] Timezone: {tz_name}")
        print(f"[Scheduler] Day: {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][weekday]}")
        print(f"[Scheduler] Optimal Time: {hour}:{minute:02d} (Kerala audience peak)")
        print(f"[Scheduler] Local Target: {publish_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[Scheduler] Upload Time (UTC): {iso_time}")
        
        return iso_time

    except Exception as e:
        logging.error(f"[Scheduler] Error calculating time: {e}")
        # Fallback: Tomorrow at IST primetime (20:00 IST = 14:30 UTC)
        try:
            ist_tz = pytz.timezone("Asia/Kolkata")
            now_ist = datetime.datetime.now(ist_tz)
            tomorrow_ist = (now_ist + datetime.timedelta(days=1)).replace(hour=20, minute=0, second=0, microsecond=0)
            fallback_utc = tomorrow_ist.astimezone(pytz.UTC)
            return fallback_utc.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        except Exception as fallback_error:
            logging.error(f"[Scheduler] Fallback also failed: {fallback_error}")
            # Last resort: UTC tomorrow at 14:30 (8 PM IST)
            fallback = datetime.datetime.now(pytz.UTC) + datetime.timedelta(days=1)
            return fallback.replace(hour=14, minute=30, second=0, microsecond=0).strftime('%Y-%m-%dT%H:%M:%S.%fZ')


def get_long_video_publish_time():
    """
    Kerala-optimized scheduler for LONG-FORM videos (8-10 mins).
    Targets primetime slots for deep engagement.
    Returns: ISO 8601 string (YYYY-MM-DDThh:mm:ss.sZ)
    """
    if CONFIG_LOADED:
        tz_name = channel_config.timezone
    else:
        tz_name = "UTC"
    
    try:
        # Get current time in target timezone
        target_tz = pytz.timezone(tz_name)
        now_local = datetime.datetime.now(target_tz)
        
        # LONG VIDEO: Primetime engagement focus
        weekday = now_local.weekday()
        
        if weekday == 4:  # Friday - GOLDEN PRIMETIME
            hour, minute = 19, 30  # 7:30 PM - weekend unwind peak
        elif weekday == 6:  # Sunday - educational mindset
            hour, minute = 20, 0   # 8:00 PM - prepare for week
        elif weekday == 2:  # Wednesday - mid-week motivation
            hour, minute = 21, 0   # 9:00 PM - mid-week peak
        else:  # Mon, Tue, Thu, Sat
            hour, minute = 20, 30  # 8:30 PM - standard primetime
        
        # Create target time
        target_today = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # If too close or passed, schedule for tomorrow
        if now_local > (target_today - datetime.timedelta(hours=2)):
            publish_time = target_today + datetime.timedelta(days=1)
        else:
            publish_time = target_today
        
        # Small jitter for natural posting
        jitter = random.randint(-8, 8)
        publish_time += datetime.timedelta(minutes=jitter)
        
        # Convert to UTC
        utc_time = publish_time.astimezone(pytz.UTC)
        
        # VALIDATION: Ensure scheduled time is in the future
        now_utc = datetime.datetime.now(pytz.UTC)
        if utc_time <= now_utc:
            logging.warning(f"[Long Scheduler] Calculated time is in the past, adjusting to future")
            # Add 1 day to ensure future time
            # CRITICAL: hour/minute are IST values, must convert to IST datetime first
            tomorrow_ist = (now_utc.astimezone(target_tz) + datetime.timedelta(days=1)).replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
            utc_time = tomorrow_ist.astimezone(pytz.UTC)
            publish_time = tomorrow_ist
        
        iso_time = utc_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        
        print(f"[Long Scheduler] Day: {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][weekday]}")
        print(f"[Long Scheduler] Primetime: {hour}:{minute:02d}")
        print(f"[Long Scheduler] Scheduled: {publish_time.strftime('%Y-%m-%d %H:%M:%S')} IST")
        
        return iso_time
    
    except Exception as e:
        logging.error(f"[Long Scheduler] Error: {e}")
        # Fallback: Tomorrow at IST primetime (20:30 IST = 15:00 UTC)
        try:
            ist_tz = pytz.timezone("Asia/Kolkata")
            now_ist = datetime.datetime.now(ist_tz)
            tomorrow_ist = (now_ist + datetime.timedelta(days=1)).replace(hour=20, minute=30, second=0, microsecond=0)
            fallback_utc = tomorrow_ist.astimezone(pytz.UTC)
            return fallback_utc.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        except Exception as fallback_error:
            logging.error(f"[Long Scheduler] Fallback also failed: {fallback_error}")
            # Last resort: UTC tomorrow at 15:00 (8:30 PM IST)
            fallback = datetime.datetime.now(pytz.UTC) + datetime.timedelta(days=1)
            return fallback.replace(hour=15, minute=0, second=0, microsecond=0).strftime('%Y-%m-%dT%H:%M:%S.%fZ')


def get_shorts_publish_time(short_index, base_publish_time):
    """
    Kerala-optimized scheduler for SHORTS (60s vertical).
    Distributes across scrolling behavior slots.
    
    Args:
        short_index: Index of the short (0-4)
        base_publish_time: ISO string of long video publish time
    
    Returns: ISO 8601 string for this short
    """
    if CONFIG_LOADED:
        tz_name = channel_config.timezone
    else:
        tz_name = "UTC"
    
    try:
        # Parse base time
        target_tz = pytz.timezone(tz_name)
        base_dt = datetime.datetime.fromisoformat(base_publish_time.replace('Z', '+00:00'))
        base_local = base_dt.astimezone(target_tz)
        
        # SHORTS: Multi-slot scrolling pattern
        # Different times to catch different user behaviors
        scrolling_slots = [
            (18, 30),  # 6:30 PM - commute home scrolling
            (12, 30),  # 12:30 PM - lunch break scrolling  
            (22, 0),   # 10:00 PM - before-bed scrolling
            (19, 0),   # 7:00 PM - evening leisure scrolling
            (13, 0)    # 1:00 PM - post-lunch scrolling
        ]
        
        # Get slot for this short
        hour, minute = scrolling_slots[short_index % len(scrolling_slots)]
        
        # Schedule on Day N after long video
        publish_date = base_local.date() + datetime.timedelta(days=short_index + 1)
        publish_time = target_tz.localize(datetime.datetime.combine(publish_date, datetime.time(hour, minute)))
        
        # Small jitter
        jitter = random.randint(-5, 5)
        publish_time += datetime.timedelta(minutes=jitter)
        
        # Convert to UTC
        utc_time = publish_time.astimezone(pytz.UTC)
        
        # VALIDATION: Ensure scheduled time is in the future
        now_utc = datetime.datetime.now(pytz.UTC)
        if utc_time <= now_utc:
            logging.warning(f"[Shorts Scheduler] Calculated time is in the past, adjusting to future")
            # Add days to ensure future time
            # CRITICAL: hour/minute are IST values, must convert to IST datetime first
            future_ist = (now_utc.astimezone(target_tz) + datetime.timedelta(days=short_index + 2)).replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
            utc_time = future_ist.astimezone(pytz.UTC)
            publish_time = future_ist
        
        iso_time = utc_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        
        print(f"[Shorts Scheduler] Short {short_index+1}: {publish_time.strftime('%a %H:%M')} (scroll slot)")
        
        return iso_time
    
    except Exception as e:
        print(f"[Shorts Scheduler] Error: {e}")
        # Fallback: base + N days + 12 hours
        fallback = datetime.datetime.fromisoformat(base_publish_time.replace('Z', '+00:00'))
        fallback += datetime.timedelta(days=short_index + 1, hours=12)
        return fallback.isoformat().replace('+00:00', 'Z')


if __name__ == "__main__":
    print(f"Long Video: {get_long_video_publish_time()}")
    print(f"Smart Publish: {get_smart_publish_time()}")
