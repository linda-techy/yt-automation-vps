# YouTube Automation - Quick Reference Guide

## 🚀 Running the System

### Full Pipeline (Long Video + 5 Shorts)
```powershell
cd "N:\Projects\yt - automation"
python pipeline.py
```

This will automatically:
1. Generate trending topic
2. Create long-form script (5-6 min)
3. Repurpose into 5 Shorts
4. Generate Malayalam thumbnails (CTR-optimized)
5. Build all videos (no burned-in subtitles)
6. Index audio for semantic search
7. Upload and schedule to YouTube
8. Generate descriptions with timestamps

---

## 🎨 Test Thumbnail Generation

### Generate Shorts Thumbnail
```powershell
python -c "from services.thumbnail_generator import generate_thumbnail; print(generate_thumbnail('Tech News', 'ടെക് വാർത്ത', 'short'))"
```

### Generate Long Video Thumbnail
```powershell
python -c "from services.thumbnail_generator import generate_thumbnail; print(generate_thumbnail('Tech Explained', 'പൂർണ്ണ വിശദീകരണം', 'long'))"
```

---

## 🔍 Search Audio Content

### Search Across All Videos
```python
from services.audio_search import search_audio

results = search_audio("പിഴവ് എവിടെ", top_k=5)
for r in results:
    print(f"{r['start_time']}: {r['chunk_text'][:80]}")
```

### Find Shorts Candidates
```python
from services.audio_search import find_shorts_candidates

candidates = find_shorts_candidates(min_duration=20, max_duration=45)
for c in candidates[:5]:
    print(f"{c['text'][:80]} ({c['duration']:.0f}s)")
```

---

## 📝 Auto-Generate YouTube Description

```python
from services.audio_automation import generate_auto_description

description = generate_auto_description("video_id_here")
print(description)
```

---

## 🎬 Apply FFmpeg Zoom (Production)

```python
from services.zoom_effects_ffmpeg import apply_ffmpeg_zoom

# Shorts zoom
apply_ffmpeg_zoom(
    "input.mp4",
    "output.mp4",
    video_type="short",
    zoom_direction="in"  # or "out"
)
```

---

## ✅ Test Audio Transcription

```powershell
python services/audio_transcriber.py "path/to/audio.mp3"
```

---

## 📊 Check Indexed Videos

```python
from services.audio_vector_store import get_indexed_videos

videos = get_indexed_videos()
for v in videos:
    print(f"{v['video_id']}: {v['title']} ({v['chunk_count']} chunks)")
```

---

## 🔧 Troubleshooting

### Thumbnails Not Generating
- Check: `OPENAI_API_KEY` environment variable
- Fallback: Uses proven Malayalam hooks automatically

### Audio Indexing Fails
- Check: Whisper is installed (`pip install openai-whisper`)
- Check: FFmpeg is in PATH
- Non-critical: Pipeline continues without indexing

### Black Borders in Videos
- Use: `zoom_effects_ffmpeg.py` for production
- Or: Verify `visual_effects.py` has pre-scaling fix

---

## 📁 Important Files

| File | Purpose |
|------|---------|
| `pipeline.py` | Main automation pipeline |
| `services/thumbnail_generator.py` | CTR-optimized thumbnails |
| `services/audio_transcriber.py` | Malayalam STT |
| `services/audio_search.py` | Semantic search |
| `channel/audio_indexes/` | Indexed audio data |

---

## 🎯 Success Metrics

Monitor:
- Thumbnail CTR (target: 8-12%)
- Avg view duration (50%+ shorts, 40%+ long)
- Audio search relevance (manual validation)
- YouTube auto-CC accuracy for Malayalam

---

**Quick Help**: See `IMPLEMENTATION_SUMMARY.md` for full documentation
