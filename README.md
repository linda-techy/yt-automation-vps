# YouTube Automation System - Production Grade

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: Private](https://img.shields.io/badge/license-Private-red.svg)](LICENSE)
[![Status: Production](https://img.shields.io/badge/status-Production-green.svg)]()

Enterprise-grade AI-powered automated YouTube content creation and upload system for Malayalam tech educational content. Built for reliability, scalability, and minimal human intervention.

---

## 🎯 System Overview

### What It Does

- **Autonomous Content Generation**: AI-generated scripts, voice, visuals, and SEO
- **Hybrid Video Ecosystem**: 1 Long-form (8-10 min) + 5 Shorts per topic
- **Smart Scheduling**: Kerala timezone-aware primetime uploads
- **Quality Assurance**: Multi-stage validation before upload
- **Self-Healing**: Automatic error recovery and health monitoring
- **Production-Ready**: Designed for 24/7 VPS operation with PM2

### Tech Stack

| Component | Technology |
|-----------|-----------|
| **AI/ML** | GPT-4o (scripts), DALL-E 3 (visuals), Whisper (transcription) |
| **TTS** | Edge-TTS (Malayalam Neural Voice) |
| **Video Processing** | FFmpeg, MoviePy, OpenCV |
| **Stock Assets** | Pixabay API (free tier) |
| **YouTube API** | OAuth 2.0, Data API v3 |
| **Database** | SQLite (quota tracking, lifecycle management) |
| **Scheduling** | Python schedule + PM2 daemon |
| **Deployment** | PM2, systemd, Ubuntu 20.04+ |

---

## 📊 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         PIPELINE ORCHESTRATOR                    │
│                      (pipeline.py + daemon.py)                   │
└────────────┬──────────────────────────────────────┬──────────────┘
             │                                      │
    ┌────────▼────────┐                    ┌───────▼────────┐
    │  Content Layer  │                    │  System Layer   │
    └────────┬────────┘                    └───────┬────────┘
             │                                      │
    ┌────────▼────────────────────┐        ┌───────▼──────────────────┐
    │ Topic Engine (News API)     │        │ Health Monitor           │
    │ Script Agent (GPT-4o)        │        │ Quota Manager (SQLite)   │
    │ TTS Engine (Edge-TTS)        │        │ Rate Limiter             │
    │ Visual Matcher (Semantic)    │        │ Error Recovery           │
    │ Video Builder (FFmpeg)       │        │ Lifecycle Tracker        │
    │ SEO Engine (Hashtags)        │        │ Upload Validator         │
    │ YouTube Uploader (OAuth)     │        │ File Manager             │
    └─────────────────────────────┘        └──────────────────────────┘
                  │                                      │
                  └──────────────┬───────────────────────┘
                                 │
                        ┌────────▼────────┐
                        │  Data Stores    │
                        ├─────────────────┤
                        │ quota_tracker.db│
                        │ video_lifecycle.│
                        │ upload_history. │
                        │ script_hashes.  │
                        │ topic_history.  │
                        └─────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Python | 3.10+ | Runtime environment |
| FFmpeg | Latest | Video processing |
| ImageMagick | Latest | Text overlays (optional) |
| OpenAI API Key | - | GPT-4, DALL-E, Whisper |
| YouTube OAuth | - | Upload credentials |
| VPS (optional) | 2GB+ RAM | Production deployment |

### Installation

```bash
# 1. Clone repository
git clone <your-repo> yt-automation
cd yt-automation

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install system dependencies (Ubuntu)
sudo apt update
sudo apt install -y ffmpeg imagemagick

# 4. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 5. Setup YouTube OAuth (one-time)
python -c "from services.youtube_uploader import generate_token_headless; generate_token_headless()"
# Follow browser authorization flow

# 6. Run health check
python -c "from services.health_monitor import get_health_monitor; get_health_monitor().run_full_health_check()"

# 7. Test pipeline (single run)
python pipeline.py
```

---

## 🏭 Production Deployment (VPS)

### Automated Setup

```bash
# Upload files to VPS
scp -r . user@vps:/home/user/yt-automation/

# SSH into VPS
ssh user@vps

# Run deployment script
cd yt-automation
chmod +x deploy.sh
./deploy.sh

# Copy OAuth credentials from local machine
# (Run this from your LOCAL machine after OAuth setup)
scp token.pickle user@vps:/home/user/yt-automation/
```

### PM2 Daemon Setup

```bash
# Install PM2 (if not installed)
npm install -g pm2

# Start daemon (runs 3x/week: Mon, Wed, Fri at 15:30 IST)
pm2 start daemon.py --name "yt-automation" --interpreter python3

# Save PM2 config
pm2 save

# Enable auto-restart on server reboot
pm2 startup

# Monitor logs
pm2 logs yt-automation

# Check status
pm2 status
```

### Monitoring & Maintenance

```bash
# View health status
cat channel/health_status.json | jq

# Check quota usage
sqlite3 channel/quota_tracker.db "SELECT * FROM quota_usage ORDER BY timestamp DESC LIMIT 10;"

# View error history
cat channel/error_history.json | jq '.[-5:]'

# Manual cleanup
python -c "from services.health_monitor import get_recovery_manager; get_recovery_manager().cleanup_stale_files()"
```

---

## ⚙️ Configuration

### Channel Settings (`channel_config.yaml`)

All channel-specific settings are centralized in `channel_config.yaml`:

- **Channel identity**: Name, handle, language
- **Content niche**: Topic focus, keywords, exclusions
- **Voice & audio**: TTS engine, voice ID, BGM settings
- **Visual style**: Themes, watermarks, thumbnail hooks
- **Video formats**: Long-form, Shorts settings
- **Upload schedule**: Timezone, upload times
- **SEO defaults**: Tags, description footer
- **Monetization**: Category, audience targeting

**To adapt for a different channel**: Edit `channel_config.yaml` only!

---

## 🔧 Troubleshooting

### Common Issues

#### FFmpeg Not Found
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
winget install ffmpeg
```

#### YouTube Quota Exceeded
- Daily quota: 10,000 units (resets midnight PT)
- Upload cost: 1,600 units (~6 videos/day max)
- Solution: System tracks quota automatically, waits for reset

#### Whisper Memory Error
```bash
# Edit services/subtitle_engine.py
# Change model size: base -> tiny
whisper.load_model("tiny")  # Uses less RAM
```

#### Upload Failures
```bash
# Check logs
tail -f logs/pipeline.log
tail -f logs/daemon.log

# Verify credentials
ls -la token.pickle client_secret.json

# Re-authenticate if needed
rm token.pickle
python -c "from services.youtube_uploader import generate_token_headless; generate_token_headless()"
```

#### Disk Space Issues
```bash
# System auto-cleans files >48hrs old
# Manual cleanup:
python -c "from services.health_monitor import get_recovery_manager; get_recovery_manager().cleanup_stale_files(max_age_hours=24)"
```

---

## 📈 Monetization (YouTube Partner Program)

### Requirements

| Requirement | Target | Status |
|-------------|--------|--------|
| Subscribers | 1,000 | Track in YouTube Studio |
| Watch Hours (Long) | 4,000 hours | OR |
| Shorts Views | 10M (90 days) | Faster path |

### System Features for YPP Compliance

✅ **100% Original Content** - AI-generated unique scripts  
✅ **Heavy Transformations** - Ken Burns effects, transitions, graphics  
✅ **Accurate Captions** - Whisper Malayalam transcription  
✅ **Consistent Schedule** - 3x/week automated uploads  
✅ **Cross-Promotion** - Shorts → Long video traffic  
✅ **Engagement** - Pinned comments, questions  

---

## 🏗️ Architecture Deep Dive

### Pipeline Flow

```
1. TOPIC GENERATION
   ├─ News API trending finance topics
   ├─ Topic history deduplication
   └─ Kerala-relevant filtering

2. SCRIPT CREATION (Long-form)
   ├─ GPT-4o generates 8-section script
   ├─ Semantic visual cues extraction
   ├─ Policy guard (safety check)
   └─ Uniqueness validation (MD5 + fuzzy)

3. REPURPOSING (5 Shorts)
   ├─ Extract 5 key subsections
   ├─ Rewrite for 45-60sec format
   └─ Generate short-specific thumbnails

4. ASSET GENERATION
   ├─ TTS: Edge-TTS Malayalam voice
   ├─ Audio mixing: BGM at 5% volume
   ├─ Visuals: Pixabay stock videos
   └─ Thumbnails: AI-generated (early stage)

5. VIDEO PRODUCTION
   ├─ Chunked rendering (prevents OOM)
   ├─ Ken Burns effects (anti-static)
   ├─ Validates: duration, format, size
   └─ Lifecycle tracking (SQLite)

6. SEO & METADATA
   ├─ Bilingual (Malayalam + English)
   ├─ Hashtag generation (trending)
   ├─ Description templates
   └─ Validation (length, format)

7. UPLOAD & SCHEDULE
   ├─ Quota check (persistent tracking)
   ├─ Upload validation (prevents duplicates)
   ├─ Kerala primetime scheduling
   ├─ Cross-promotion comments (pinned)
   └─ Archive content for analytics

8. CLEANUP & RECOVERY
   ├─ Conditional cleanup (success-based)
   ├─ Health monitoring
   ├─ Error pattern detection
   └─ Auto-recovery mechanisms
```

### Database Schema (SQLite)

**quota_tracker.db**
```sql
CREATE TABLE quota_usage (
    id INTEGER PRIMARY KEY,
    operation TEXT,        -- 'upload', 'comment', etc.
    cost INTEGER,          -- Quota units consumed
    timestamp DATETIME,
    reset_at DATETIME,
    metadata TEXT
);
```

**video_lifecycle.json**
```json
{
  "video_id": "xyz123",
  "type": "long",
  "topic": "EMI Trap Malayalam",
  "status": "uploaded",
  "scheduled_time": "2025-01-11T19:00:00+05:30",
  "created_at": "2025-01-11T15:30:00+05:30",
  "metadata": {...}
}
```

---

## 🔒 Security Best Practices

1. **Never commit secrets** - Already configured in `.gitignore`
2. **Use environment variables** - All credentials in `.env`
3. **Rotate API keys** - Every 90 days minimum
4. **Separate dev/prod** - Different API keys per environment
5. **Monitor quota** - Automated with persistent tracking
6. **Regular backups** - SQLite databases + config files

---

## 📊 System Metrics & Monitoring

### Health Indicators

```bash
# Current health status
cat channel/health_status.json | jq '{
  healthy: .overall_healthy,
  disk: .disk.free_gb,
  memory: .memory.available_gb,
  dependencies: .dependencies.healthy
}'
```

### Quota Dashboard

```bash
# Weekly quota usage
sqlite3 channel/quota_tracker.db "
SELECT DATE(timestamp) as date, SUM(cost) as total_units
FROM quota_usage
WHERE timestamp >= datetime('now', '-7 days')
GROUP BY DATE(timestamp)
ORDER BY date DESC;
"
```

---

## 🛠️ Development

### Running Tests

```bash
# Test health monitoring
python services/health_monitor.py

# Test quota manager
python services/quota_manager.py

# Test rate limiter
python services/rate_limiter.py
```

### Adding New Services

1. Create service in `services/your_service.py`
2. Follow existing patterns (logging, error handling)
3. Add to imports in `pipeline.py`
4. Update `channel_config.yaml` if needed
5. Document in README

---

## 📝 Changelog & Version History

### v2.0.0 - Production Hardening (2026-01-11)
- ✅ Fixed critical `short_time` undefined variable bug
- ✅ Added persistent quota tracking (SQLite)
- ✅ Implemented health monitoring system
- ✅ Added error recovery mechanisms
- ✅ Created comprehensive documentation
- ✅ Improved daemon with health checks

### v1.0.0 - Initial Release
- Basic pipeline with GPT-4 + Edge-TTS
- YouTube upload via OAuth
- Simple scheduling

---

## 📧 Support & Contact

- **Issues**: Check `logs/pipeline.log` and `logs/daemon.log`
- **Health Status**: `channel/health_status.json`
- **Error History**: `channel/error_history.json`

---

## ⚖️ License

**Private Project** - Not for public distribution

## © Copyright

© 2026 FinMindMalayalam  
All rights reserved.

