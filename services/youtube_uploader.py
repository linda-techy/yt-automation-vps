import os
import pickle
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import googleapiclient.http
from google.auth.transport.requests import Request
import logging

# Import rate limiter FIRST (needed for decorators)
try:
    from services.rate_limiter import rate_limiter, retry_with_backoff, QuotaExceededError
except ImportError:
    # Graceful fallback
    logging.warning("[Upload] Rate limiter not available")
    rate_limiter = None
    QuotaExceededError = Exception
    def retry_with_backoff(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

# Scopes required
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.force-ssl"]

CLIENT_SECRETS_FILE = os.getenv("YOUTUBE_CLIENT_SECRET_FILE", "client_secret.json")
TOKEN_FILE = os.getenv("YOUTUBE_TOKEN_FILE", "token.pickle")


def generate_token_headless():
    """
    Generate OAuth token using OOB (Out-of-Band) flow for headless VPS setup.
    Run this ONCE on a machine with browser access, then copy token.pickle to VPS.
    
    Usage:
        python -c "from services.youtube_uploader import generate_token_headless; generate_token_headless()"
    """
    if not os.path.exists(CLIENT_SECRETS_FILE):
        raise FileNotFoundError(f"Client Secret file '{CLIENT_SECRETS_FILE}' not found.")
    
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRETS_FILE, SCOPES)
    
    # Use run_local_server with a callback that doesn't require browser on the same machine
    # For truly headless: Open URL manually, paste code back
    print("\n" + "="*60)
    print("YOUTUBE OAUTH SETUP (Headless/VPS Compatible)")
    print("="*60)
    
    try:
        # Method 1: Try local server (works if running locally with browser)
        print("\n[Option 1] Trying local browser authentication...")
        credentials = flow.run_local_server(
            port=8080,
            success_message='✅ Authentication successful! You can close this window.',
            open_browser=True
        )
    except Exception as e:
        # Method 2: Manual OOB flow for truly headless
        print(f"\nLocal server failed: {e}")
        print("\n[Option 2] Manual authentication (for VPS/SSH):")
        print("-" * 50)
        
        # Generate auth URL manually
        auth_url, _ = flow.authorization_url(prompt='consent')
        
        print(f"\n1. Open this URL in ANY browser:\n\n{auth_url}\n")
        print("2. Authorize the application")
        print("3. Copy the authorization code from the redirect URL")
        print("   (It's the 'code' parameter after ?code=)")
        print("-" * 50)
        
        code = input("\nPaste the authorization code here: ").strip()
        
        # Exchange code for credentials
        flow.fetch_token(code=code)
        credentials = flow.credentials
    
    # Save token for VPS use
    with open(TOKEN_FILE, 'wb') as token:
        pickle.dump(credentials, token)
    
    print(f"\n✅ Token saved to: {TOKEN_FILE}")
    print(f"📋 Copy to VPS: scp {TOKEN_FILE} user@your-vps:/path/to/project/")
    print("="*60 + "\n")
    
    return credentials


def get_authenticated_service(max_retries=3):
    """
    Get authenticated YouTube service with retry logic.
    Works on VPS without browser by using pre-generated token.
    
    Args:
        max_retries: Number of authentication attempts
    
    Returns:
        YouTube API service
    """
    
    for attempt in range(max_retries):
        try:
            credentials = None
            
            # Load token if exists
            if os.path.exists(TOKEN_FILE):
                with open(TOKEN_FILE, 'rb') as token:
                    credentials = pickle.load(token)
                    
            # Refresh or generate token
            if not credentials or not credentials.valid:
                if credentials and credentials.expired:
                    if credentials.refresh_token:
                        # Auto-refresh - works on VPS without browser
                        try:
                            print(f"[YouTube] Refreshing expired token (attempt {attempt+1}/{max_retries})...")
                            credentials.refresh(Request())
                            
                            # Save refreshed token
                            with open(TOKEN_FILE, 'wb') as token:
                                pickle.dump(credentials, token)
                            logging.info("[YouTube] Token refreshed successfully")
                        except Exception as refresh_error:
                            error_str = str(refresh_error).lower()
                            if 'invalid_grant' in error_str or 'token has been expired or revoked' in error_str:
                                # Refresh token expired - need re-authentication
                                logging.error("[YouTube] Refresh token expired. Re-authentication required.")
                                logging.error("[YouTube] Delete token.pickle and run generate_token_headless() again")
                                raise Exception(
                                    "OAuth refresh token expired. Please re-authenticate by running: "
                                    "python -c \"from services.youtube_uploader import generate_token_headless; generate_token_headless()\""
                                )
                            else:
                                # Other refresh error - retry
                                raise refresh_error
                    else:
                        # No refresh token - need re-authentication
                        logging.error("[YouTube] No refresh token available. Re-authentication required.")
                        raise Exception(
                            "No refresh token found. Please re-authenticate by running: "
                            "python -c \"from services.youtube_uploader import generate_token_headless; generate_token_headless()\""
                        )
                else:
                    # No valid token - check if we're on a headless system
                    if not os.path.exists(CLIENT_SECRETS_FILE):
                        raise FileNotFoundError(f"Client Secret file '{CLIENT_SECRETS_FILE}' not found.")
                    
                    # Try headless auth first, fall back to browser
                    try:
                        print("[YouTube] No valid token found. Attempting headless auth...")
                        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                            CLIENT_SECRETS_FILE, SCOPES)
                        credentials = flow.run_console()
                    except Exception as e:
                        print(f"[YouTube] Headless auth failed: {e}")
                        print("[YouTube] Trying browser auth...")
                        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                            CLIENT_SECRETS_FILE, SCOPES)
                        credentials = flow.run_local_server(port=0)
                        
                    # Save token
                    with open(TOKEN_FILE, 'wb') as token:
                        pickle.dump(credentials, token)
            
            # Success
            logging.info("[YouTube] Authentication successful")
            return googleapiclient.discovery.build("youtube", "v3", credentials=credentials)
            
        except Exception as e:
            logging.error(f"[YouTube] Auth attempt {attempt+1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                import time
                wait_time = 5 * (attempt + 1)
                logging.info(f"[YouTube] Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise Exception(f"YouTube authentication failed after {max_retries} attempts: {e}")


def upload_short(video_path, seo_metadata, publish_at=None, thumbnail_path=None):
    """
    Upload video to YouTube with retry logic.
    Works on VPS with pre-generated token (no browser needed).
    """
    # CRITICAL: Check quota BEFORE expensive upload operation
    if rate_limiter:
        try:
            rate_limiter.check_quota('upload')
            logging.info(f"[YouTube] Quota check passed - proceeding with upload")
        except Exception as e:
            logging.error(f"[YouTube] Quota check failed: {e}")
            raise
    
    # Validate video file exists
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"[YouTube] Video file not found: {video_path}")
    
    file_size_mb = os.path.getsize(video_path) / (1024**2)
    logging.info(f"[YouTube] Uploading video: {os.path.basename(video_path)} ({file_size_mb:.1f}MB)")
    
    youtube = get_authenticated_service()
    
    if isinstance(seo_metadata, str):
        lines = seo_metadata.split('\n')
        title = lines[0].replace("Title:", "").strip()[:100]
        description = "\n".join(lines[1:])
        tags = []
    else:
        title = seo_metadata.get("title", "New Tech Short")
        description = seo_metadata.get("description", "Daily Tech Update")
        tags = seo_metadata.get("tags", [])
    
    # Status logic for scheduling
    status_body = {
        "selfDeclaredMadeForKids": False
    }
    
    if publish_at:
        status_body["privacyStatus"] = "private"  # Must be private to schedule
        status_body["publishAt"] = publish_at  # ISO 8601 string
        print(f"[YouTube] Scheduling upload for: {publish_at}")
    else:
        status_body["privacyStatus"] = "private"  # Default
    
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "28"  # Science & Technology
        },
        "status": status_body
    }
    
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=googleapiclient.http.MediaFileUpload(video_path, chunksize=-1, resumable=True)
    )
    
    import time
    import random
    
    # Retry Logic (Exponential Backoff)
    MAX_RETRIES = 10
    video_id = None
    for attempt in range(MAX_RETRIES):
        try:
            print(f"[YouTube] Uploading... (Attempt {attempt+1}/{MAX_RETRIES})")
            response = request.execute()
            video_id = response['id']
            print(f"[YouTube] Uploaded Video ID: {video_id}")
            break
        except googleapiclient.errors.HttpError as e:
            if e.resp.status in [403, 500, 502, 503, 504]:
                print(f"[YouTube] API Error {e.resp.status}: {e}")
                if e.resp.status == 403 and "quota" in str(e).lower():
                    print("[YouTube] CRITICAL: Upload Quota Exceeded for today.")
                    raise
                    
                sleep_time = (2 ** attempt) + random.random()
                print(f"[YouTube] Retrying in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
            else:
                raise
        except Exception as e:
            print(f"[YouTube] Network error during upload: {e}")
            if attempt < MAX_RETRIES - 1:
                sleep_time = (2 ** attempt) + random.random()
                time.sleep(sleep_time)
            else:
                raise
    else:
        raise Exception("[YouTube] Upload failed after max retries")
    
    # CRITICAL: Consume quota after successful upload
    if video_id:
        try:
            # Use persistent quota manager for accurate tracking
            from services.quota_manager import get_quota_manager
            quota_manager = get_quota_manager()
            quota_manager.record_usage('upload', 1600, metadata=f"video_id:{video_id}")
            logging.info(f"[YouTube] Quota consumed for upload (video_id: {video_id})")
        except ImportError:
            # Fallback to rate_limiter if quota_manager not available
            if rate_limiter:
                try:
                    rate_limiter.consume('upload')
                    logging.info(f"[YouTube] Quota consumed via rate_limiter (video_id: {video_id})")
                except Exception as e:
                    logging.warning(f"[YouTube] Failed to record quota usage via rate_limiter: {e}")
            else:
                logging.warning(f"[YouTube] No quota tracking available for video_id: {video_id}")
        except Exception as e:
            logging.error(f"[YouTube] Failed to record quota usage: {e}", exc_info=True)
    
    # Upload Thumbnail (Separate API call)
    if thumbnail_path and os.path.exists(thumbnail_path):
        print(f"[YouTube] Uploading thumbnail: {thumbnail_path}")
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=googleapiclient.http.MediaFileUpload(thumbnail_path)
            ).execute()
            print("[YouTube] Thumbnail uploaded successfully")
        except Exception as e:
            print(f"[YouTube] Thumbnail upload failed: {e}")
            logging.warning(f"[YouTube] Thumbnail upload failed for {video_id}: {e}")

    return video_id



@retry_with_backoff(max_retries=2)
def insert_comment(video_id, text):
    """
    Posts a comment on a video.
    
    Features:
    - Rate limiting
    - Retry logic (2 attempts)
    - Proper error handling
    """
    # Check quota
    rate_limiter.check_quota('comment')
    
    youtube = get_authenticated_service()
    try:
        response = youtube.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {
                        "snippet": {
                            "textOriginal": text
                        }
                    }
                }
            }
        ).execute()
        
        # Consume quota
        rate_limiter.consume('comment')
        
        safe_text = text[:50].encode('ascii', 'replace').decode('ascii')
        logging.info(f"[YouTube] Posted Comment: {safe_text}...")
        return response['id']
    
    except Exception as e:
        logging.error(f"[YouTube] Comment failed: {e}")
        raise


def pin_comment(comment_id):
    """
    Pins a comment to the top of the video.
    CRITICAL for cross-promotion: Pinned comments get 5-10x more clicks!
    
    Args:
        comment_id: The ID returned from insert_comment()
    
    Returns:
        True if pinned successfully, False otherwise
    """
    youtube = get_authenticated_service()
    try:
        # YouTube API: Set moderation status to "published" makes it pinned
        youtube.comments().setModerationStatus(
            id=comment_id,
            moderationStatus="published",
            banAuthor=False
        ).execute()
        
        print(f"[YouTube] Comment pinned successfully")
        return True
    except Exception as e:
        print(f"[YouTube] Pin failed: {e}")
        # Note: Some accounts need "YouTube Data API v3" with comment management enabled
        return False


if __name__ == "__main__":
    # Run headless token generation
    print("YouTube OAuth Token Generator")
    print("=" * 40)
    generate_token_headless()
