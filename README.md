# YouTube Automation System

AI-powered YouTube content automation that generates, produces, and uploads Malayalam tech videos automatically.

## Features

- 🤖 **AI Script Generation** - GPT-4o writes engaging Malayalam scripts
- 🎬 **Hybrid Visuals** - DALL-E 3 for key scenes + Pixabay for B-roll
- 🎙️ **Natural TTS** - Edge TTS with Malayalam voice (Midhun)
- 📝 **Whisper Captions** - Accurate Malayalam subtitles
- 📺 **Auto Upload** - Scheduled YouTube uploads with SEO
- 🔄 **Format Ecosystem** - 1 Long (10min) + 5 Shorts per topic

---

## Quick Start

### Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python 3.10+ | Required |
| FFmpeg | Video processing |
| ImageMagick | Text overlays |
| OpenAI API Key | GPT-4o, DALL-E 3, Whisper |
| Pixabay API Key | Stock videos (free) |
| YouTube OAuth | Upload credentials |

### 1. Clone & Install

```bash
git clone <your-repo> yt-automation
cd yt-automation
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file:
```env
OPENAI_API_KEY=sk-your-key-here
PIXABAY_API_KEY=your-pixabay-key
YOUTUBE_CLIENT_SECRET_FILE=client_secret.json
YOUTUBE_TOKEN_FILE=token.pickle
```

### 3. Setup YouTube OAuth

```bash
# Generate OAuth token (one-time, requires browser)
python -c "from services.youtube_uploader import generate_token_headless; generate_token_headless()"
```

### 4. Run Pipeline

```bash
python pipeline.py
```

---

## VPS Deployment (Ubuntu)

### Step 1: Upload Files to VPS
```bash
scp -r . user@your-vps:/home/user/yt-automation/
```

### Step 2: Run Deploy Script
```bash
chmod +x deploy.sh
./deploy.sh
```

This installs: FFmpeg, ImageMagick, Malayalam fonts, Python deps

### Step 3: Copy OAuth Token
```bash
# From local machine (where you ran OAuth)
scp token.pickle user@your-vps:/home/user/yt-automation/
```

### Step 4: Setup Cron (Daily Automation)
```bash
crontab -e
# Add:
0 20 * * * cd /home/user/yt-automation && python3 pipeline.py >> logs/cron.log 2>&1
```

---

## Project Structure

```
yt-automation/
├── pipeline.py           # Main entry point
├── services/
│   ├── topic_engine.py   # Trending topic discovery
│   ├── script_agent.py   # AI script generation
│   ├── tts_engine.py     # Malayalam voice synthesis
│   ├── bg_generator.py   # Hybrid visuals (AI + Pixabay)
│   ├── video_builder.py  # Video composition
│   ├── subtitle_engine.py # Whisper captions
│   ├── youtube_uploader.py # Upload with OAuth
│   └── file_manager.py   # Auto cleanup
├── config/
│   └── platform.py       # Cross-platform paths
├── deploy.sh             # Ubuntu setup script
├── requirements.txt      # Python dependencies
└── .env                  # API keys (create this)
```

---

## Monetization Requirements (YPP)

### YouTube Partner Program Thresholds

| Requirement | Target |
|-------------|--------|
| Subscribers | 1,000 |
| Watch Hours (Long) | 4,000 hours |
| OR Shorts Views | 10M views (90 days) |

### How This System Helps

✅ **Original Content** - AI-generated unique scripts  
✅ **Not Reused** - Heavy visual transformations  
✅ **Accurate Captions** - Whisper Malayalam transcription  
✅ **Dual Format** - Long videos for watch time + Shorts for reach  
✅ **Daily Automation** - Consistent upload schedule  

### Tips for Faster Monetization

1. **Post Daily** - Use cron job for consistency
2. **Optimize Thumbnails** - AI generates eye-catching thumbnails
3. **Cross-Promote** - Shorts link to Long videos
4. **Engage Comments** - Auto-posts pinned comment with links

---

## Troubleshooting

### FFmpeg Not Found
```bash
# Ubuntu
sudo apt install ffmpeg

# Windows
winget install ffmpeg
```

### ImageMagick Error
```bash
# Ubuntu - fix policy
sudo sed -i 's/<policy domain="path" rights="none" pattern="@\*"\/>//g' /etc/ImageMagick-6/policy.xml
```

### YouTube Quota Exceeded
- Quota resets at midnight Pacific Time
- Max 10,000 units/day (6 video uploads)

### Whisper Memory Error
- Use smaller Whisper model: `whisper.load_model("base")`
- Or increase VPS RAM

---

## API Keys Setup

### OpenAI
1. Go to [platform.openai.com](https://platform.openai.com)
2. Create API key
3. Add to `.env`: `OPENAI_API_KEY=sk-...`

### Pixabay (Free)
1. Go to [pixabay.com/api/docs](https://pixabay.com/api/docs/)
2. Sign up and get free API key
3. Add to `.env`: `PIXABAY_API_KEY=...`

### YouTube OAuth
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create project → Enable YouTube Data API v3
3. Create OAuth 2.0 credentials (Desktop App)
4. Download `client_secret.json`
5. Run token generation (see Quick Start)

---

## License

Private project. Not for distribution.
