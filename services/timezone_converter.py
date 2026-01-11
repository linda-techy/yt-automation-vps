"""
Timezone Converter for YouTube Uploads
Handles IST to UTC conversion for scheduled uploads
"""

from datetime import datetime
import pytz
import logging


def convert_to_youtube_time(local_time, local_tz='Asia/Kolkata'):
    """
    Convert local time to YouTube-compatible UTC format.
    
    YouTube API requires:
    - UTC timezone
    - RFC 3339 format: "2025-12-30T14:30:00Z"
    
    Args:
        local_time: datetime object or ISO string (e.g., "2025-12-30 20:00:00")
        local_tz: Local timezone (default: 'Asia/Kolkata' for IST)
    
    Returns:
        str: UTC time in YouTube RFC 3339 format
    
    Example:
        >>> ist_time = "2025-12-30 20:00:00"  # 8 PM IST
        >>> youtube_time = convert_to_youtube_time(ist_time)
        >>> # Returns: "2025-12-30T14:30:00Z" (2:30 PM UTC)
    """
    
    try:
        local = pytz.timezone(local_tz)
        
        # Parse string to datetime if needed
        if isinstance(local_time, str):
            # Handle various formats
            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M']:
                try:
                    local_time = datetime.strptime(local_time, fmt)
                    break
                except ValueError:
                    continue
            else:
                # Try ISO format with timezone
                local_time = datetime.fromisoformat(local_time.replace('Z', '+00:00'))
        
        # Localize to local timezone if naive
        if local_time.tzinfo is None:
            local_time = local.localize(local_time)
        
        # Convert to UTC
        utc_time = local_time.astimezone(pytz.UTC)
        
        # Format for YouTube (RFC 3339)
        youtube_format = utc_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        logging.info(f"Timezone conversion: {local_time} ({local_tz}) → {youtube_format} (UTC)")
        
        return youtube_format
        
    except Exception as e:
        logging.error(f"Timezone conversion failed: {e}")
        raise Exception(f"Invalid time format: {local_time}")


def youtube_time_to_local(youtube_time, local_tz='Asia/Kolkata'):
    """
    Convert YouTube UTC time back to local timezone.
    
    Args:
        youtube_time: UTC time string ("2025-12-30T14:30:00Z")
        local_tz: Target timezone
    
    Returns:
        datetime: Localized datetime object
    """
    
    # Parse YouTube time
    utc = pytz.UTC
    youtube_dt = datetime.strptime(youtube_time.rstrip('Z'), '%Y-%m-%dT%H:%M:%S')
    youtube_dt = utc.localize(youtube_dt)
    
    # Convert to local
    local = pytz.timezone(local_tz)
    local_dt = youtube_dt.astimezone(local)
    
    return local_dt


if __name__ == "__main__":
    # Test conversions
    test_times = [
        "2025-12-30 20:00:00",  # 8 PM IST
        "2025-12-31 06:00:00",  # 6 AM IST
        datetime(2025, 12, 30, 12, 0, 0)  # Noon IST
    ]
    
    for t in test_times:
        youtube_t = convert_to_youtube_time(t)
        print(f"{t} → {youtube_t}")
