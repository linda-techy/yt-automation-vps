"""
YouTube Automation Integration - Audio Intelligence
Uses semantic audio search for automated descriptions, script reuse, and more
"""

import logging
from services.audio_search import search_audio, find_shorts_candidates
from services.audio_vector_store import load_audio_index


def generate_auto_description(video_id, max_length=3000):
    """
    Generates YouTube description using semantic audio chunks.
    
    Process:
    1. Load audio index for video
    2. Select top 5 most important chunks
    3. Convert to bullet points with timestamps
    4. Add hashtags from topics
    
    Args:
        video_id: Video identifier
        max_length: Max description length (YouTube limit: 5000)
    
    Returns:
        YouTube-ready description string
    """
    
    logging.info(f"📝 Generating auto-description for {video_id}")
    
    # Load audio index
    index = load_audio_index(video_id)
    
    if not index:
        logging.warning(f"No audio index found for {video_id}")
        return ""
    
    chunks = index.get("chunks", [])
    metadata = index.get("metadata", {})
    
    if not chunks:
        return ""
    
    # Select key chunks (prefer explanations and examples)
    key_chunks = _select_key_chunks(chunks, top_n=5)
    
    # Build description
    description_parts = []
    
    # Title/intro
    title = metadata.get("title", "")
    if title:
        description_parts.append(f"📺 {title}\n")
    
    # Timestamps with summaries
    description_parts.append("⏱️ Key Timestamps:\n")
    for chunk in key_chunks:
        start_time = _format_timestamp(int(chunk.get("start", 0)))
        # Truncate text to ~80 chars
        chunk_text = chunk.get("text_intent", chunk.get("text", ""))[:80]
        description_parts.append(f"{start_time} - {chunk_text}...")
    
    # Collect topics for hashtags
    topics = set()
    for chunk in chunks:
        topic = chunk.get("topic", "")
        if topic and topic != "general":
            topics.add(topic)
    
    # Add hashtags
    if topics:
        description_parts.append("\n🏷️ Topics:")
        hashtags = [f"#{topic.replace(' ', '')}" for topic in list(topics)[:5]]
        description_parts.append(" ".join(hashtags))
    
    description = "\n".join(description_parts)
    
    # Truncate if needed
    if len(description) > max_length:
        description = description[:max_length-3] + "..."
    
    logging.info(f"✅ Generated description ({len(description)} chars)")
    
    return description


def _select_key_chunks(chunks, top_n=5):
    """
    Selects most important chunks for description.
    
    Prioritizes:
    - Explanations and examples
    - Chunks from different parts of video
    - Medium-length chunks (20-35s)
    """
    
    scored_chunks = []
    
    for i, chunk in enumerate(chunks):
        score = 0
        
        # Intent priority
        intent = chunk.get("intent", "")
        if intent == "explanation":
            score += 3
        elif intent == "example":
            score += 2
        elif intent == "conclusion":
            score += 1
        
        # Duration preference
        duration = chunk.get("duration", 0)
        if 20 <= duration <= 35:
            score += 2
        
        # Position diversity (prefer spread across video)
        position_ratio = i / len(chunks) if chunks else 0
        if 0.2 < position_ratio < 0.8:  # Middle chunks
            score += 1
        
        scored_chunks.append((score, chunk))
    
    # Sort by score
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    
    # Return top N
    return [chunk for score, chunk in scored_chunks[:top_n]]


def _format_timestamp(seconds):
    """Formats seconds as MM:SS."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"


def extract_shorts_from_long_video(video_id, min_count=3, max_count=5):
    """
    Identifies chunks from a long video suitable for Shorts.
    
    Args:
        video_id: Long video identifier
        min_count: Minimum number of candidates
        max_count: Maximum number to return
    
    Returns:
        List of chunk dicts suitable for Shorts
    """
    
    logging.info(f"✂️ Finding Shorts candidates in {video_id}")
    
    index = load_audio_index(video_id)
    
    if not index:
        logging.warning(f"No audio index for {video_id}")
        return []
    
    chunks = index.get("chunks", [])
    
    # Filter for Shorts criteria
    candidates = []
    
    for chunk in chunks:
        duration = chunk.get("duration", 0)
        intent = chunk.get("intent", "")
        topic = chunk.get("topic", "").lower()
        
        # Shorts-suitable criteria
        if 20 <= duration <= 45:  # Right duration
            if intent in ["explanation", "example", "conclusion"]:  # Self-contained
                # Boost high-energy topics
                suitability = 5
                if any(keyword in topic for keyword in ["mistake", "shock", "secret", "warning"]):
                    suitability += 3
                
                candidates.append({
                    **chunk,
                    "suitability": suitability
                })
    
    # Sort by suitability
    candidates.sort(key=lambda x: x["suitability"], reverse=True)
    
    # Return between min and max count
    result_count = max(min_count, min(max_count, len(candidates)))
    results = candidates[:result_count]
    
    logging.info(f"✅ Found {len(results)} Shorts candidates")
    
    return results


def analyze_retention_weak_spots(video_id):
    """
    Identifies segments with potential retention issues.
    
    Looks for:
    - Very long chunks (> 50s, may lose attention)
    - Repetitive topics
    - Low-energy segments
    
    Returns:
        List of chunks that may need improvement
    """
    
    index = load_audio_index(video_id)
    
    if not index:
        return []
    
    chunks = index.get("chunks", [])
    weak_spots = []
    
    # Track topic frequency
    topic_counts = {}
    for chunk in chunks:
        topic = chunk.get("topic", "")
        topic_counts[topic] = topic_counts.get(topic, 0) + 1
    
    for chunk in chunks:
        issues = []
        
        # Too long
        duration = chunk.get("duration", 0)
        if duration > 50:
            issues.append(f"Long duration ({duration:.0f}s)")
        
        # Repetitive topic
        topic = chunk.get("topic", "")
        if topic_counts.get(topic, 0) > 3:
            issues.append(f"Repetitive topic ({topic})")
        
        # Generic content
        if topic == "general":
            issues.append("Generic topic")
        
        if issues:
            weak_spots.append({
                **chunk,
                "issues": issues
            })
    
    return weak_spots


if __name__ == "__main__":
    # Test auto-description
    test_video_id = "test_video_123"
    
    description = generate_auto_description(test_video_id)
    print("\n" + "="*60)
    print("AUTO-GENERATED DESCRIPTION")
    print("="*60)
    print(description)
    
    # Test Shorts extraction
    shorts = extract_shorts_from_long_video(test_video_id, max_count=3)
    print(f"\n\nShorts candidates: {len(shorts)}")
    for i, short in enumerate(shorts):
        print(f"{i+1}. {short['start']:.1f}s - {short['end']:.1f}s ({short['duration']:.1f}s)")
        print(f"   Topic: {short['topic']}, Intent: {short['intent']}")
        print(f"   Text: {short['text'][:80]}...")
