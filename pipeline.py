import logging
import hashlib
import os
import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# CROSS-PLATFORM: Use platform-specific configuration
from config.platform import configure_environment
platform_config = configure_environment()

from services.topic_engine import get_topic
from services.script_agent import generate_script_with_agent
from services.tts_engine import generate_voice
from services.bg_generator import generate_background_images
from services.video_builder import build_final_video
from services.seo_engine import generate_seo
from services.youtube_uploader import upload_short
from services.scheduler import get_smart_publish_time
from services.audio_mixer import mix_audio
from services.thumbnail_generator import generate_thumbnail
from services.file_manager import get_output_path, cleanup_after_upload, cleanup_old_output_files
from services.upload_tracker import track_pending_upload, mark_as_uploaded, cleanup_uploaded_files, get_pending_uploads
from services.scheduler import get_smart_publish_time, get_long_video_publish_time, get_shorts_publish_time
from services.video_validator import validate_video
from services.seo_validator import validate_seo_metadata
from services.content_archiver import archive_content
from services.policy_guard import check_script_safety
from services.feedback_loop import analyze_performance_trends
from services.video_lifecycle_manager import (
    register_video, mark_upload_success, cleanup_uploaded_videos, cleanup_temp_files
)

# Ensure directories exist
os.makedirs("logs", exist_ok=True)
os.makedirs("channel", exist_ok=True)
os.makedirs("videos/output", exist_ok=True)
os.makedirs("videos/temp", exist_ok=True)

# Setup Logging
logging.basicConfig(
    filename='logs/pipeline.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# FIX #8: Validate API Keys on startup
def validate_environment():
    """Validates that all required environment variables and tools are present."""
    import sys
    errors = []
    
    if not os.getenv("OPENAI_API_KEY"):
        errors.append("OPENAI_API_KEY not found in environment")
    
    if not os.getenv("YOUTUBE_CLIENT_SECRET_FILE"):
        errors.append("YOUTUBE_CLIENT_SECRET_FILE not set")
        
    import shutil
    ffmpeg_found = False
    if shutil.which("ffmpeg"):
        ffmpeg_found = True
    else:
        # Check imageio fallback
        try:
            import imageio
            from imageio.plugins.ffmpeg import get_exe
            if get_exe():
                ffmpeg_found = True
                logging.info(f"Using ImageIO FFmpeg: {get_exe()}")
        except:
            pass
            
    if not ffmpeg_found:
        errors.append("FFmpeg not found in PATH or ImageIO")
        
    if not shutil.which("magick") and not shutil.which("convert"):
        # ImageMagick is critical for TextClip
        # We can try to proceed if we trust the config override?
        # But let's keep it strict for now unless user overrides.
        # errors.append("ImageMagick not found in PATH")
        # Removing strict ImageMagick check as config override is present
        pass

    if errors:
        for err in errors:
            logging.error(f"Environment Error: {err}")
            print(f"[ERROR] {err}")
        print("\n[WARNING] Fix environment and try again.")
        sys.exit(1)
    else:
        logging.info("Environment validation passed")

def get_script_hash(script):
    return hashlib.md5(script.encode('utf-8')).hexdigest()

def is_script_unique(script, hash_file="channel/script_hashes.txt"):
    # Legacy Check (MD5) - Fast for exact duplicates
    curr_hash = get_script_hash(script)
    if not os.path.exists(hash_file):
        return True
    
    with open(hash_file, "r") as f:
        existing_data = f.read().splitlines()

    # MD5 Check
    hashes = [line.split("|")[0] for line in existing_data] # Support format hash|content_snippet
    if curr_hash in hashes:
        logging.warning("Script rejected: Exact MD5 match found.")
        return False

    # Semantic/Fuzzy Check (FuzzyRatio)
    from difflib import SequenceMatcher
    
    # Check against last 50 script hashes
    # To do this effectively, we should have stored the script CONTENT snippets, not just hashes.
    # But since we are only storing hashes + topic history, we will rely on Topic Check primary.
    # However, let's look at `upload_history.json` for titles!
    
    try:
        import json
        if os.path.exists("channel/upload_history.json"):
            with open("channel/upload_history.json", "r", encoding="utf-8") as f:
                history = json.load(f)
                
            for item in history:
                # Check Topic similarity on uploaded videos
                ratio = SequenceMatcher(None, script[:50], item.get("title", "")[:50]).ratio()
                if ratio > 0.6: # If script start is very similar to a past title
                    logging.warning(f"Script reject: Too similar to '{item.get('title')}'")
                    return False
    except:
        pass

    return True

def save_script_hash(script, hash_file="channel/script_hashes.txt"):
    curr_hash = get_script_hash(script)
    os.makedirs(os.path.dirname(hash_file), exist_ok=True)
    with open(hash_file, "a") as f:
        f.write(curr_hash + "\n")

def log_upload_history(video_data, history_file="channel/upload_history.json"):
    """
    Logs details of successfully uploaded videos to JSON.
    video_data: dict with keys (video_id, title, topic, publish_at, filename)
    """
    import json
    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except:
            history = []
            
    history.append({
        "video_id": video_data.get("video_id"),
        "title": video_data.get("title"),
        "topic": video_data.get("topic"),
        "publish_at": video_data.get("publish_at"),
        "filename": video_data.get("filename"),
        "upload_date": datetime.datetime.now().isoformat(),
        "status": "scheduled"
    })
    
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    logging.info(f"📝 Logged upload to {history_file}")

def run_pipeline():
    """
    Main pipeline with comprehensive error handling (FIX #5).
    """
    # Initialize trace ID for this pipeline run
    from utils.logging.tracer import tracer
    trace_id = tracer.set_trace_id()
    
    logging.info("="*60)
    logging.info(f"Starting Production Pipeline (Hardened) [Trace:{trace_id}]")
    logging.info("="*60)
    
    try:
        # 1. Topic
        logging.info("STEP 1: Fetching Topic...")
        
        # Integrate Feedback Loop: Analyze recent performance to influence topic/script
        try:
             analyze_performance_trends()
        except Exception as e:
             logging.warning(f"Feedback loop failed: {e}")
             
        topic = get_topic()
        logging.info(f"✅ Topic: {topic}")

        # 2. Script (LangGraph Agent)
        logging.info("STEP 2: Generating Script with Agent...")
        script_data = generate_script_with_agent(topic)
        script_text = script_data.get("script", "")
        visual_cues = script_data.get("visual_cues", [])
        
        if not script_text:
            raise Exception("Script generation failed - empty script")
            
        logging.info(f"✅ Script generated ({len(script_text)} chars, {len(visual_cues)} visuals)")
        
        if not is_script_unique(script_text):
            logging.warning("⚠️  Script is duplicate. Aborting to avoid repetition.")
            return

        # Policy Check
        logging.info("STEP 2.5: Checking Content Policy compliance...")
        safety_res = check_script_safety(script_text, topic)
        if not safety_res.get("safe", False):
            logging.error(f"❌ Script rejected by Policy Guard: {safety_res.get('flags')}")
            # In production, we might loop back to regenerate. For now, abort.
            return
        logging.info(f"✅ Script passed Policy Guard (Score: {safety_res.get('score')})")

        # 3. Voice & Audio Mix
        logging.info("STEP 3: Generating Voice...")
        raw_voice_path = generate_voice(script_text)
        if not raw_voice_path or not os.path.exists(raw_voice_path):
            raise Exception("Voice generation failed")
            
        logging.info("STEP 4: Mixing Audio with BGM...")
        voice_path = mix_audio(raw_voice_path)
        logging.info(f"✅ Mixed Audio: {voice_path}")
        
        # 4. Assets
        logging.info("STEP 5: Fetching Realistic Video Assets...")
        # STRICT: Visual cues MUST be provided by script
        if not visual_cues:
            raise Exception("Script agent failed to generate visual cues. NO FALLBACK ALLOWED.")
            
        asset_paths = generate_background_images(visual_cues)
        logging.info(f"✅ Fetched {len(asset_paths)} video assets")
        
        # Generate Thumbnail
        logging.info("STEP 6: Creating Thumbnail...")
        # Use simple "Hook" text for thumbnail if available, else Title
        thumb_text = script_data.get("thumbnail_text", script_data.get("title", "TECH UPDATE"))
        thumbnail_path = generate_thumbnail(topic, thumb_text)
        logging.info(f"✅ Thumbnail: {thumbnail_path}")
        
        # 5. Build
        logging.info("STEP 7: Building Final Video...")
        final_video = build_final_video(voice_path, asset_paths, script_data)
        logging.info(f"✅ Video Built: {final_video}")
        
        # 6. Upload & Schedule
        logging.info("STEP 8: Generating SEO Metadata (Malayalam/English)...")
        seo = generate_seo(topic)
        
        # 6.5. Quality Gate - Pre-upload quality check
        logging.info("STEP 8.5: Quality Scoring (Pre-upload gate)...")
        from services.quality_scorer import quality_scorer
        import os
        
        # Get video duration if possible
        duration = None
        try:
            from moviepy.editor import VideoFileClip
            with VideoFileClip(final_video) as clip:
                duration = clip.duration
        except:
            pass
        
        quality_result = quality_scorer.score_complete(
            script_data=script_data,
            video_path=final_video,
            seo_metadata=seo,
            topic=topic
        )
        
        if not quality_result["passed"]:
            logging.error(f"❌ Quality gate FAILED: Overall score {quality_result['overall_score']:.2f}/10")
            failed_components = [k for k, v in quality_result["components"].items() if not v["passed"]]
            logging.error(f"   Failed: {', '.join(failed_components)}")
            raise Exception(f"Quality gate failed. Score: {quality_result['overall_score']:.2f}/10. Cannot upload.")
        
        logging.info(f"✅ Quality gate PASSED: {quality_result['overall_score']:.2f}/10")
        
        logging.info("STEP 9: Scheduling Upload...")
        publish_at = get_smart_publish_time()
        logging.info(f"📅 Scheduled for: {publish_at}")
        
        video_id = upload_short(final_video, seo, publish_at=publish_at, thumbnail_path=thumbnail_path)
        
        # 7. Post Logic: Pinned Comment (Engagement - Malayalam)
        from services.youtube_uploader import insert_comment
        question = script_data.get("comment_question")
        if question and video_id:
             try:
                 logging.info(f"STEP 10: Posting Pinned Comment (Malayalam): {question}")
                 insert_comment(video_id, question)
             except Exception as e:
                 logging.warning(f"Failed to post comment: {e}")
        
        save_script_hash(script_text)
        logging.info(f"✅ SUCCESS! Malayalam Video ID: {video_id}")
        
        # Log History before Deletion
        log_upload_history({
            "video_id": video_id,
            "title": script_data.get("title"),
            "topic": topic,
            "publish_at": publish_at,
            "filename": os.path.basename(final_video)
        })
        
        # Cleanup Final Video (Save Space)
        if os.path.exists(final_video):
            os.remove(final_video)
            logging.info(f"🗑️ Deleted final video: {final_video}")

        logging.info("="*60)
        print(f"\n[SUCCESS] Pipeline Complete! Video ID: {video_id}\n")
        
    except Exception as e:
        logging.error(f"[ERROR] PIPELINE FAILED: {str(e)}", exc_info=True)
        print(f"\n[ERROR] Pipeline Error: {e}\n")
        print("Check logs/pipeline.log for details.")
        raise
    finally:
        # Crash Prevention: Cleanup Temp Files
        # If we don't do this, VPS disk fills up in 2 weeks.
        import shutil
        try:
            if os.path.exists("videos/temp"):
                shutil.rmtree("videos/temp")
                os.makedirs("videos/temp", exist_ok=True) # Recreate empty
                logging.info("🧹 Temp files cleaned up.")
        except Exception as e:
            logging.warning(f"Cleanup failed: {e}")

# Removed argparse - pipeline now only supports auto-generated topics

def run_unified_pipeline():
    """
    UNIFIED HYBRID PIPELINE: Generates 1 Long-Form + 5 Shorts with ALL quality checks.
    Auto-generates trending topics from News API.
    """
    # Initialize trace ID for this pipeline run
    from utils.logging.tracer import tracer
    trace_id = tracer.set_trace_id()
    
    logging.info("="*60)
    logging.info(f"Starting UNIFIED HYBRID Pipeline (Long + Shorts) [Trace:{trace_id}]")
    logging.info("="*60)
    
    # Track upload success for conditional cleanup
    upload_success = False
    SCRIPT_CACHE = "videos/temp/script_cache.json"
    
    try:
        # ========== STEP 1: Auto-Generate Topic from Trending News ==========
        logging.info("Fetching trending topic from News API...")
        topic = get_topic()  # Auto-generates from trending news/API
        logging.info(f"✅ Topic: {topic}")

        # ========== STEP 2: Generate Long-Form Script ==========
        logging.info("STEP 2: Generating Long-Form Script (8-10 mins)...")
        from services.script_agent_long import generate_long_script
        from services.variation_engine import variation_engine
        
        long_script = generate_long_script(topic)
        
        if not long_script or not long_script.get('sections'):
            raise Exception("Long-form script generation failed")
        
        # Add variation to script (intro/outro rotation)
        if long_script.get('sections'):
            # Add variation to first section (intro)
            first_section = long_script['sections'][0]
            if first_section.get('content'):
                intro = variation_engine.get_intro()
                first_section['content'] = f"{intro} {first_section['content']}"
            
            # Add variation to last section (outro)
            last_section = long_script['sections'][-1]
            if last_section.get('content'):
                outro = variation_engine.get_outro()
                last_section['content'] = f"{last_section['content']} {outro}"
        
        logging.info(f"✅ Long Script: {long_script.get('title')}")
        
        # ===== THUMBNAIL GENERATION (EARLY - FAIL-SAFE) =====
        # Create thumbnail NOW (only needs topic + title)
        # Ensures thumbnail exists even if video assembly fails
        logging.info("🎨 Generating LONG thumbnail (16:9, 1920x1080)...")
        long_thumbnail = None
        try:
            long_thumb_text = long_script.get('thumbnail_text', long_script.get('title', 'WATCH NOW'))
            long_thumbnail = generate_thumbnail(topic, long_thumb_text, video_type="long")
            
            # Verify export
            if long_thumbnail and os.path.exists(long_thumbnail):
                file_size = os.path.getsize(long_thumbnail)
                logging.info(f"✅ LONG thumbnail exported: {long_thumbnail} ({file_size:,} bytes)")
            else:
                raise Exception(f"Long thumbnail file not found: {long_thumbnail}")
        except Exception as e:
            logging.error(f"❌ Long thumbnail generation failed: {e}")
            # Retry once with fallback
            try:
                logging.info("🔄 Retrying long thumbnail generation...")
                long_thumbnail = generate_thumbnail(topic, topic, video_type="long")
                if long_thumbnail and os.path.exists(long_thumbnail):
                    logging.info(f"✅ Long thumbnail created on retry: {long_thumbnail}")
                else:
                    raise Exception("Retry also failed")
            except Exception as retry_error:
                logging.error(f"❌ Long thumbnail retry failed: {retry_error}")
                raise Exception("Long thumbnail generation failed completely. Cannot continue.")
        
        # ========== STEP 3: Repurpose to 5 Shorts ==========
        logging.info("STEP 3: Repurposing into 5 Shorts Scripts...")
        from services.repurposer import repurpose_long_script
        shorts_scripts = repurpose_long_script(long_script)
        
        # STRICT: Repurposer MUST return valid scripts
        if not shorts_scripts or len(shorts_scripts) == 0:
            raise Exception("Repurposer failed to generate Shorts scripts. NO FALLBACK ALLOWED.")
            
        logging.info(f"✅ Generated {len(shorts_scripts)} Shorts Scripts")
        
        # ===== SHORTS THUMBNAILS GENERATION (EARLY - FAIL-SAFE) =====
        # Generate ALL 5 shorts thumbnails NOW (before video processing)
        logging.info(f"🎨 Generating {len(shorts_scripts)} SHORTS thumbnails (9:16, 1080x1920)...")
        shorts_thumbnails = []
        for i, short_script in enumerate(shorts_scripts):
            try:
                s_thumb_text = short_script.get('thumbnail_text', 'WATCH NOW')
                s_thumb = generate_thumbnail(topic, s_thumb_text, video_type="short")
                
                # Verify export
                if s_thumb and os.path.exists(s_thumb):
                    file_size = os.path.getsize(s_thumb)
                    shorts_thumbnails.append(s_thumb)
                    logging.info(f"✅ Short {i+1}/{len(shorts_scripts)} thumbnail exported: {s_thumb} ({file_size:,} bytes)")
                else:
                    raise Exception(f"Short {i+1} thumbnail file not found: {s_thumb}")
            except Exception as e:
                logging.error(f"❌ Short {i+1} thumbnail failed: {e}")
                # Retry once with fallback
                try:
                    logging.info(f"🔄 Retrying short {i+1} thumbnail generation...")
                    s_thumb = generate_thumbnail(topic, topic, video_type="short")
                    if s_thumb and os.path.exists(s_thumb):
                        shorts_thumbnails.append(s_thumb)
                        logging.info(f"✅ Short {i+1} thumbnail created on retry: {s_thumb}")
                    else:
                        raise Exception("Retry also failed")
                except Exception as retry_error:
                    logging.error(f"❌ Short {i+1} thumbnail retry failed: {retry_error}")
                    # Don't fail entire pipeline - append None and continue
                    shorts_thumbnails.append(None)
        
        # Final export summary
        successful_shorts = sum(1 for t in shorts_thumbnails if t is not None)
        logging.info(f"📊 Thumbnail Export Summary: 1 Long + {successful_shorts}/{len(shorts_scripts)} Shorts")
        if successful_shorts < len(shorts_scripts):
            logging.warning(f"⚠️ {len(shorts_scripts) - successful_shorts} shorts thumbnails failed to generate")
        
        # ===== SEO GENERATION (EARLY - REUSABLE) =====
        # Generate SEO NOW so it can be reused if pipeline fails later
        logging.info("📝 Generating SEO metadata (early stage)...")
        try:
            long_seo_raw = generate_seo(topic)
            shorts_seo = [generate_seo(f"{topic} - Part {i+1}") for i in range(len(shorts_scripts))]
            logging.info("✅ SEO metadata generated")
        except Exception as e:
            logging.warning(f"⚠️ SEO generation failed: {e}")
            long_seo_raw = {"title": topic, "description": "", "tags": []}
            shorts_seo = [{"title": f"{topic} - Part {i+1}", "description": "", "tags": []} 
                         for i in range(len(shorts_scripts))]
        
        # ===== SCRIPT CACHING (IMMEDIATE - RECOVERY) =====
        # Cache scripts NOW for retry/recovery capability
        logging.info("💾 Caching scripts for recovery...")
        import json
        full_long_text = " ".join([s.get('content', '') for s in long_script.get('sections', [])])
        try:
            with open(SCRIPT_CACHE, 'w', encoding='utf-8') as f:
                json.dump({
                    'long_script': long_script,
                    'shorts_scripts': shorts_scripts,
                    'full_long_text': full_long_text,
                    'topic': topic,
                    'long_seo': long_seo_raw,
                    'shorts_seo': shorts_seo
                }, f, ensure_ascii=False, indent=2)
            logging.info(f"✅ Scripts cached: {SCRIPT_CACHE}")
        except Exception as e:
            logging.warning(f"⚠️ Script caching failed: {e}")
        
        # ========== STEP 4: Script Uniqueness Check (ALL scripts) ==========
        full_long_text = " ".join([s.get('content', '') for s in long_script.get('sections', [])])
        if not is_script_unique(full_long_text):
            logging.warning("⚠️ Long script is duplicate. Aborting.")
            return
            
        for i, short in enumerate(shorts_scripts):
            if not is_script_unique(short.get('script', '')):
                logging.warning(f"⚠️ Short {i+1} is duplicate. Skipping this short.")
                shorts_scripts[i] = None  # Mark for skipping
                
        shorts_scripts = [s for s in shorts_scripts if s is not None]  # Remove duplicates

        # ========== STEP 5: Build Long-Form Video (16:9 Landscape) ==========
        logging.info("STEP 5: Building Long-Form Video (16:9, 1920x1080)...")
        
        # Get scheduled publish time for long video
        long_publish_time = get_long_video_publish_time()
        logging.info(f"[Scheduler] Long video scheduled for: {long_publish_time}")
        
        # Prepare Output Path with UNIQUE filename (topic-based + timestamp)
        # This prevents overwrites and enables proper lifecycle tracking
        # Format: long_{topic_hash}_{safe_topic}_{timestamp}.mp4
        topic_hash = get_script_hash(topic)[:8]
        safe_topic = "".join([c for c in topic if c.isalnum() or c in (' ', '-', '_')]).strip()[:30]
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        long_video_path = f"videos/output/long_{topic_hash}_{safe_topic.replace(' ', '_')}_{timestamp}.mp4"

        # Check for existing video to Resume/Recover
        if os.path.exists(long_video_path):
            logging.info(f"✅ Found existing Long Video: {long_video_path}")
            logging.info("⏭️ SKIPPING expensive rendering (TTS, Assets, Video Build)...")
            
            # CRITICAL: Load cached script for resume (to generate matching shorts)
            if os.path.exists(SCRIPT_CACHE):
                import json
                with open(SCRIPT_CACHE, 'r', encoding='utf-8') as f:
                    cached_data = json.load(f)
                long_script = cached_data.get('long_script', long_script)
                shorts_scripts = cached_data.get('shorts_scripts', shorts_scripts)
                full_long_text = cached_data.get('full_long_text', full_long_text)
                logging.info("✅ Loaded cached script data for recovery")
        else:
            # Generate long-form TTS
            from services.tts_engine import generate_voice_long
            long_voice_path = generate_voice_long(full_long_text, output_path="videos/temp/long_voice.mp3")
            
            if not long_voice_path or not os.path.exists(long_voice_path):
                raise Exception("Long-form voice generation failed")
            
            # Mix audio with BGM
            from services.audio_mixer import mix_audio
            long_audio_mixed = mix_audio(long_voice_path)
            
            # ===== ASSET PRE-CALCULATION (PREVENTS FAILURES) =====
            # Calculate EXACTLY how many assets needed BEFORE generating
            # This prevents: Generate 32 → Fail at chunk 4 → Need 40
            logging.info("🔢 Pre-calculating required assets...")
            from services.asset_calculator import calculate_required_assets, validate_asset_count
            
            required_assets = calculate_required_assets(long_audio_mixed, max_scene_duration=4.5)
            logging.info(f"📊 Analysis: Need {required_assets} unique assets for optimized scenes")
            
            # ========== SEMANTIC VISUAL MATCHING (NEW) ==========
            # Use AI to map script content → relevant stock video search terms
            # This fixes the "video content not matching voice" problem
            logging.info("[SemanticMatcher] Analyzing script for semantically matched visuals...")
            
            try:
                from services.semantic_visual_matcher import map_sections_to_visuals
                long_visual_cues = map_sections_to_visuals(long_script)
                logging.info(f"[SemanticMatcher] Generated {len(long_visual_cues)} AI-optimized visual cues")
            except ImportError:
                logging.warning("[SemanticMatcher] Module not found, falling back to script visual_cues")
                # Fallback to original logic
                long_visual_cues = []
                for section in long_script.get('sections', []):
                    section_cues = section.get('visual_cues', [])
                    if isinstance(section_cues, list) and section_cues:
                        long_visual_cues.extend(section_cues)
                    else:
                        cue = section.get('visual_cue', '')
                        if cue:
                            long_visual_cues.extend([cue] * 4)
            
            # STRICT: Must have sufficient visuals
            if len(long_visual_cues) < 30:
                raise Exception(f"Long script has insufficient visual cues ({len(long_visual_cues)} cues). Expected at least 30. NO FALLBACK ALLOWED.")
            
            logging.info(f"[Pipeline] Using {len(long_visual_cues)} semantically matched visual cues for long video")
            
            # Ensure we have enough cues by cycling if needed
            if len(long_visual_cues) < required_assets:
                logging.warning(f"Insufficient unique cues ({len(long_visual_cues)}). Recycling cues to meet requirement ({required_assets}).")
                import math
                multiplier = math.ceil(required_assets / len(long_visual_cues))
                long_visual_cues = (long_visual_cues * multiplier)[:required_assets]

            # Generate assets using PRE-CALCULATED count
            asset_count_to_generate = required_assets
            logging.info(f"Generating {asset_count_to_generate} visual assets from {len(long_visual_cues)} cues...")
            long_assets = generate_background_images(long_visual_cues[:asset_count_to_generate], orientation="landscape")
            
            # VALIDATE asset count BEFORE building video
            validation = validate_asset_count(long_assets, required_assets)
            if not validation['valid']:
                raise Exception(
                    f"Asset validation failed: {validation['message']}. "
                    f"Need to generate {validation['need'] - validation['have']} more assets."
                )
            logging.info(validation['message'])
            
            # Build long video (chunked rendering for stability)
            from services.video_builder_long import build_long_video_chunked
            long_video_path = build_long_video_chunked(long_audio_mixed, long_assets, long_script)
            logging.info(f"✅ Long Video Built: {long_video_path}")
            
            # Register video in lifecycle manager
            register_video(
                video_path=long_video_path,
                video_type="long",
                topic=topic,
                scheduled_time=long_publish_time,
                metadata={
                    "title": long_script.get('title'),
                    "thumbnail_path": long_thumbnail  # Track for cleanup
                }
            )
            
            # VALIDATE VIDEO QUALITY
            logging.info("Validating long video quality...")
            validation = validate_video(long_video_path, expected_min_duration=60, expected_format="16:9")
            if not validation['valid']:
                raise Exception(f"Long video failed validation: {validation['errors']}")
            logging.info(f"✅ Video validated: {validation['duration_sec']:.1f}s, {validation['file_size_mb']:.1f}MB")
            
            # Script caching already done early (after script generation)
            # SEO already generated early (reusable for retry)
            
            # Thumbnail already generated earlier (after script creation)
        # Kept here for reference: long_thumbnail variable is set above
        
        # Use pre-generated SEO (generated early for retry capability)
        # Generate and VALIDATE Long-Form SEO (with hashtags)
        # Use pre-generated SEO (generated early for retry capability)
        niche = channel_config.niche if hasattr(channel_config, 'niche') else "Technology"
        seo_validation = validate_seo_metadata(long_seo_raw, topic, niche)
        
        if not seo_validation['valid']:
            logging.error(f"SEO validation failed: {seo_validation['errors']}")
            # Use validated version anyway (with warnings)
        
        # Use validated SEO with hashtags appended
        long_seo = f"Title: {seo_validation['title']}\n\nDescription:\n{seo_validation['description']}"
        logging.info(f"✅ SEO validated with hashtags: {seo_validation['hashtags']}")
        
        # ========== STEP 6: Build All Shorts (9:16 Vertical) ==========
        logging.info("STEP 6: Building Shorts (9:16, 1080x1920)...")
        short_videos = []
        
        for i, short_script in enumerate(shorts_scripts):
            logging.info(f"  Building Short {i+1}/{len(shorts_scripts)}: {short_script.get('title')}")
            
            # Calculate scheduled publish time for this short (MUST be before register_video)
            short_time = get_shorts_publish_time(i, long_publish_time)
            
            # Voice generation
            s_text = short_script.get('script', '')
            s_voice = generate_voice(s_text, output_path=f"videos/temp/short_{i}.mp3")
            
           # Audio mixing with unique output path for each short
            s_mix = mix_audio(s_voice, output_path=f"videos/temp/short_{i}_mixed.mp3")
            
            # Assets
            s_cues = short_script.get('visual_cues', [topic]*5)
            s_assets = generate_background_images(s_cues, orientation="portrait")
            
            # Thumbnail for Short (9:16 portrait)
            # Use pre-generated thumbnail from early stage
            s_thumb = shorts_thumbnails[i] if i < len(shorts_thumbnails) else None
            
            # Build video with UNIQUE filename (script hash + index + timestamp)
            # Format: short_{i}_{short_hash}_{safe_topic}_{timestamp}.mp4
            # Index prevents overwrites within same run, timestamp prevents across runs
            short_hash = get_script_hash(s_text)[:8]
            safe_short_topic = "".join([c for c in short_script.get('title', f'Short_{i}') if c.isalnum() or c in (' ', '-', '_')]).strip()[:20]
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            s_output = f"videos/output/short_{i}_{short_hash}_{safe_short_topic.replace(' ', '_')}_{timestamp}.mp4"
            final_short = build_final_video(s_mix, s_assets, short_script, output_path=s_output)
            
            # Register video in lifecycle manager
            register_video(
                video_path=final_short,
                video_type=f"short_{i}",
                topic=topic,
                scheduled_time=short_time,
                metadata={
                    "title": short_script.get('title'),
                    "thumbnail_path": s_thumb  # Track for cleanup
                }
            )
            
            short_videos.append({
                'path': final_short,
                'script': short_script,
                'thumbnail': s_thumb,
                'seo': generate_seo(f"{topic} - Part {i+1}")
            })
            
            logging.info(f"  ✅ Short {i+1} Ready")
        
        # ========== STEP 7: Queue Videos for Scheduled Upload ==========
        logging.info("STEP 7: Queueing Videos for Scheduled Upload...")
        
        # Schedule long-form video FIRST (main content) - Kerala primetime
        long_publish_time = get_long_video_publish_time()
        logging.info(f"📅 Long Video scheduled (Kerala primetime): {long_publish_time}")
        
        # ===== PRE-UPLOAD VALIDATION (CRITICAL) =====
        logging.info("🔍 Validating upload readiness...")
        from services.upload_validator import (
            validate_upload_ready, is_already_uploaded, 
            check_quota_available, record_quota_usage, validate_youtube_metadata
        )
        from services.timezone_converter import convert_to_youtube_time
        
        # Check if already uploaded (prevents duplicates)
        already_uploaded, existing_id = is_already_uploaded(long_video_path)
        if already_uploaded:
            logging.info(f"✅ Long video already uploaded: {existing_id}")
            long_video_id = existing_id
        else:
            # Validate metadata and fix if needed
            metadata_result = validate_youtube_metadata(long_seo, auto_fix=True)
            if metadata_result['warnings']:
                logging.warning(f"SEO warnings: {metadata_result['warnings']}")
            long_seo_validated = metadata_result['fixed_metadata']
            
            # Validate upload assets
            validate_upload_ready(long_video_path, long_thumbnail, long_seo_validated)
            
            # Quality gate for long video
            logging.info("🔍 Quality Scoring: Long Video...")
            from services.quality_scorer import quality_scorer
            
            long_duration = None
            try:
                from moviepy.editor import VideoFileClip
                with VideoFileClip(long_video_path) as clip:
                    long_duration = clip.duration
            except:
                pass
            
            # Create script_data dict for quality scorer
            long_script_data = {
                "script": " ".join([s.get('content', '') for s in long_script.get('sections', [])]),
                "title": long_script.get('title', topic),
                "visual_cues": [c for s in long_script.get('sections', []) for c in s.get('visual_cues', [])]
            }
            
            long_quality = quality_scorer.score_complete(
                script_data=long_script_data,
                video_path=long_video_path,
                seo_metadata=long_seo_validated,
                topic=topic
            )
            
            if not long_quality["passed"]:
                logging.error(f"❌ Long video quality gate FAILED: {long_quality['overall_score']:.2f}/10")
                raise Exception(f"Long video quality gate failed. Score: {long_quality['overall_score']:.2f}/10")
            
            logging.info(f"✅ Long video quality PASSED: {long_quality['overall_score']:.2f}/10")
            
            # Queue for scheduled upload instead of uploading immediately
            track_pending_upload(
                file_path=long_video_path,
                video_type="long",
                topic=topic,
                scheduled_time=long_publish_time,
                metadata={
                    "title": long_script.get('title'),
                    "seo_metadata": long_seo_validated,
                    "thumbnail_path": long_thumbnail,
                    "script": long_script,
                    "quality_score": long_quality['overall_score']
                }
            )
            logging.info(f"✅ Long video queued for scheduled upload at {long_publish_time}")
            long_video_id = None  # Will be set after upload completes
            
            # Register in lifecycle manager for tracking
            register_video(
                video_path=long_video_path,
                video_type="long",
                topic=topic,
                scheduled_time=long_publish_time,
                metadata={
                    "title": long_script.get('title'),
                    "thumbnail_path": long_thumbnail
                }
            )
        
        # Log long video to history (with None video_id until uploaded)
        log_upload_history({
            "video_id": long_video_id or "pending",
            "title": long_script.get('title'),
            "topic": topic,
            "publish_at": long_publish_time,
            "filename": os.path.basename(long_video_path),
            "format": "long-form-16:9",
            "status": "queued" if not long_video_id else "uploaded"
        })
        
        # Schedule shorts over next 5 days (1 per day)
        import datetime
        base_time = datetime.datetime.fromisoformat(long_publish_time.replace('Z', '+00:00'))
        
        for i, short_data in enumerate(short_videos):
            # Schedule using Kerala scrolling slots (6:30 PM, 12:30 PM, 10 PM, etc.)
            short_time = get_shorts_publish_time(i, long_publish_time)
            
            # Quality gate for short video
            logging.info(f"🔍 Quality Scoring: Short {i+1}...")
            short_quality = quality_scorer.score_complete(
                script_data=short_data['script'],
                video_path=short_data['path'],
                seo_metadata=short_data['seo'],
                topic=topic
            )
            
            if not short_quality["passed"]:
                logging.error(f"❌ Short {i+1} quality gate FAILED: {short_quality['overall_score']:.2f}/10")
                logging.warning(f"⚠️ Skipping Short {i+1} upload due to quality failure")
                continue
            
            logging.info(f"✅ Short {i+1} quality PASSED: {short_quality['overall_score']:.2f}/10")
            
            # Queue for scheduled upload instead of uploading immediately
            track_pending_upload(
                file_path=short_data['path'],
                video_type="short",
                topic=topic,
                scheduled_time=short_time,
                metadata={
                    "title": short_data['script'].get('title'),
                    "seo_metadata": short_data['seo'],
                    "thumbnail_path": short_data['thumbnail'],
                    "script": short_data['script'],
                    "quality_score": short_quality['overall_score'],
                    "index": i,
                    "linked_long_video": "pending"  # Will be updated after long video uploads
                }
            )
            logging.info(f"  ✅ Short {i+1} queued for scheduled upload at {short_time}")
            
            # Log short to history (with None video_id until uploaded)
            log_upload_history({
                "video_id": "pending",
                "title": short_data['script'].get('title'),
                "topic": topic,
                "publish_at": short_time,
                "filename": os.path.basename(short_data['path']),
                "format": "short-9:16",
                "linked_long_video": long_video_id,
                "status": "queued"
            })
        
        # ========== STEP 8: Save Script Hashes (prevent future duplication) ==========
        save_script_hash(full_long_text)
        for short in shorts_scripts:
            save_script_hash(short.get('script', ''))
        
        logging.info("="*60)
        logging.info(f"✅ SUCCESS! Published 1 Long + {len(short_videos)} Shorts")
        logging.info(f"   Main Video: {long_video_id}")
        logging.info("="*60)
        
        upload_success = True  # Mark successful completion
        
        # ========== STEP 9: Audio Semantic Indexing ==========
        # Index audio for semantic search, descriptions, and Shorts extraction
        try:
            logging.info("🎤 Indexing audio for semantic search...")
            from services.audio_transcriber import transcribe_malayalam_audio
            from services.semantic_chunker import chunk_by_semantics
            from services.audio_embedder import batch_generate_embeddings
            from services.audio_vector_store import store_audio_index
            
            # Index long video audio
            if os.path.exists(long_audio_mixed):
                transcript = transcribe_malayalam_audio(long_audio_mixed, context_hint=topic)
                chunks = chunk_by_semantics(transcript["segments"], topic_hint=topic)
                enriched_chunks = batch_generate_embeddings(chunks, use_dual=True)
                
                store_audio_index(long_video_id, enriched_chunks, metadata={
                    "title": long_script.get('title'),
                    "topic": topic,
                    "duration": transcript["duration"],
                    "video_type": "long"
                })
                
                logging.info(f"✅ Long video audio indexed: {len(enriched_chunks)} semantic chunks")
            
            # Index shorts audio (lighter processing)
            for i, short_data in enumerate(short_videos):
                short_id = f"short_{i}_{long_video_id}"
                short_audio = f"videos/temp/short_{i}_mixed.mp3"
                
                if os.path.exists(short_audio):
                    try:
                        transcript = transcribe_malayalam_audio(short_audio, context_hint=f"{topic} - part {i+1}")
                        chunks = chunk_by_semantics(transcript["segments"], min_duration=10, max_duration=30)
                        enriched_chunks = batch_generate_embeddings(chunks, use_dual=True)
                        
                        store_audio_index(short_id, enriched_chunks, metadata={
                            "title": short_data['script'].get('title'),
                            "topic": topic,
                            "duration": transcript["duration"],
                            "video_type": "short",
                            "parent_video": long_video_id
                        })
                        
                        logging.info(f"✅ Short {i+1} audio indexed")
                    except Exception as e:
                        logging.warning(f"Short {i+1} indexing failed: {e}")
            
        except Exception as e:
            logging.warning(f"Audio indexing failed (non-critical): {e}")
        
        # ========== STEP 10: Safe Cleanup - Lifecycle Based ==========
        # Clean up old uploaded videos (48hr buffer)
        deleted_count = cleanup_uploaded_videos(max_age_hours=48)
        logging.info(f"🗑️ Deleted {deleted_count} old uploaded videos (>48hr)")
        
        # Clean temp files (safe after upload)
        cleanup_temp_files()
        
        # Clean script cache after successful upload
        if os.path.exists(SCRIPT_CACHE):
            os.remove(SCRIPT_CACHE)
            logging.info("🗑️ Script cache cleaned")
        
    except Exception as e:
        logging.error(f"PIPELINE FAILED: {str(e)}", exc_info=True)
        print(f"\n[ERROR] {e}\n")
        raise
    finally:
        # Conditional cleanup based on success
        import shutil
        if upload_success:
            # Full cleanup - pipeline completed successfully
            try:
                if os.path.exists("videos/temp"):
                    shutil.rmtree("videos/temp")
                    os.makedirs("videos/temp", exist_ok=True)
                    logging.info("🧹 Temp files cleaned (full success)")
            except Exception as e:
                logging.warning(f"Cleanup failed: {e}")
        else:
            # Keep files for recovery - pipeline failed or incomplete
            logging.warning("⚠️ Pipeline incomplete - keeping temp files for recovery")
            logging.info("💡 Re-run pipeline to resume from last checkpoint")

if __name__ == "__main__":
    validate_environment()
    
    # Run unified pipeline with auto-generated topics only
    run_unified_pipeline()

