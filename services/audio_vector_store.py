"""
Audio Vector Store - JSON-based (Simple, No Dependencies)
Stores and retrieves audio embeddings for semantic search
"""

import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Optional


AUDIO_INDEX_DIR = "channel/audio_indexes"


def store_audio_index(video_id, chunks, metadata=None):
    """
    Stores audio index for a video.
    
    Args:
        video_id: Unique video identifier
        chunks: List of semantic chunks with embeddings
        metadata: Optional video metadata (title, topic, etc.)
    
    Returns:
        Path to saved index file
    """
    
    os.makedirs(AUDIO_INDEX_DIR, exist_ok=True)
    
    index_data = {
        "video_id": video_id,
        "indexed_at": datetime.now().isoformat(),
        "chunk_count": len(chunks),
        "metadata": metadata or {},
        "chunks": chunks
    }
    
    # Save individual video index
    index_path = os.path.join(AUDIO_INDEX_DIR, f"{video_id}.json")
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
    
    logging.info(f"💾 Stored audio index: {index_path} ({len(chunks)} chunks)")
    
    # Update master index
    _update_master_index(video_id, metadata, len(chunks))
    
    return index_path


def load_audio_index(video_id):
    """
    Loads audio index for a specific video.
    
    Returns:
        Index data dict or None if not found
    """
    
    index_path = os.path.join(AUDIO_INDEX_DIR, f"{video_id}.json")
    
    if not os.path.exists(index_path):
        logging.warning(f"Audio index not found: {video_id}")
        return None
    
    with open(index_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_all_indexes():
    """
    Loads all audio indexes for cross-video search.
    
    Returns:
        List of all index data
    """
    
    if not os.path.exists(AUDIO_INDEX_DIR):
        return []
    
    all_indexes = []
    
    for filename in os.listdir(AUDIO_INDEX_DIR):
        if filename.endswith('.json') and filename != 'master_index.json':
            video_id = filename.replace('.json', '')
            index_data = load_audio_index(video_id)
            if index_data:
                all_indexes.append(index_data)
    
    return all_indexes


def _update_master_index(video_id, metadata, chunk_count):
    """
    Updates master index with new video entry.
    
    Master index is a quick lookup for all indexed videos.
    """
    
    master_path = os.path.join(AUDIO_INDEX_DIR, "master_index.json")
    
    # Load existing
    master_data = {"videos": []}
    if os.path.exists(master_path):
        with open(master_path, 'r', encoding='utf-8') as f:
            master_data = json.load(f)
    
    # Remove old entry if exists
    master_data["videos"] = [v for v in master_data["videos"] if v.get("video_id") != video_id]
    
    # Add new entry
    master_data["videos"].append({
        "video_id": video_id,
        "indexed_at": datetime.now().isoformat(),
        "chunk_count": chunk_count,
        "title": metadata.get("title", "") if metadata else "",
        "topic": metadata.get("topic", "") if metadata else ""
    })
    
    # Save
    with open(master_path, 'w', encoding='utf-8') as f:
        json.dump(master_data, f, ensure_ascii=False, indent=2)


def get_indexed_videos():
    """
    Returns list of all indexed videos.
    
    Returns:
        [
            {
                "video_id": "abc123",
                "indexed_at": "2025-12-29T...",
                "chunk_count": 15,
                "title": "Malayalam Tech News",
                "topic": "technology"
            }
        ]
    """
    
    master_path = os.path.join(AUDIO_INDEX_DIR, "master_index.json")
    
    if not os.path.exists(master_path):
        return []
    
    with open(master_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data.get("videos", [])


if __name__ == "__main__":
    # Test storage
    test_chunks = [
        {
            "text": "Test Malayalam chunk 1",
            "start": 10.0,
            "end": 25.0,
            "topic": "test",
            "embedding_raw": [0.1] * 1536,
            "embedding_intent": [0.2] * 1536
        },
        {
            "text": "Test Malayalam chunk 2",
            "start": 25.0,
            "end": 40.0,
            "topic": "test",
            "embedding_raw": [0.3] * 1536,
            "embedding_intent": [0.4] * 1536
        }
    ]
    
    test_metadata = {
        "title": "Test Video",
        "topic": "Technology",
        "duration": 120.0
    }
    
    # Store
    path = store_audio_index("test_video_123", test_chunks, test_metadata)
    print(f"Stored: {path}")
    
    # Load
    loaded = load_audio_index("test_video_123")
    print(f"\nLoaded: {loaded['chunk_count']} chunks")
    
    # List all
    all_videos = get_indexed_videos()
    print(f"\nIndexed videos: {len(all_videos)}")
