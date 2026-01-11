"""
Semantic Audio Search - Intent-Aware Search with Re-ranking
The magic happens here - returns RELEVANT results, not just keyword matches
"""

import logging
from services.audio_embedder import _create_embedding, cosine_similarity
from services.audio_vector_store import load_all_indexes, load_audio_index
from typing import List, Dict, Optional


def search_audio(query, top_k=5, video_filter=None, min_similarity=0.5):
    """
    Semantic search across all indexed audio.
    
    THIS IS THE KEY FUNCTION - Returns topic-relevant, intent-aware results.
    
    Args:
        query: Search query (Malayalam or English)
            Examples:
            - "എവിടെയാണ് ആളുകൾ പിഴവ് ചെയ്യുന്നത്?"
            - "technology mistakes explanation"
        top_k: Number of results to return
        video_filter: Optional video_id to search within specific video
        min_similarity: Minimum similarity score (0.0-1.0)
    
    Returns:
        [
            {
                "video_id": "abc123",
                "chunk_text": "ഇവിടെ ആളുകൾ...",
                "start_time": "00:02:15",
                "end_time": "00:02:42",
                "timestamp_link": "?t=135",
                "relevance_score": 0.87,
                "topic": "mistakes",
                "intent": "explanation"
            }
        ]
    """
    
    logging.info(f"🔍 Searching audio: '{query}' (top {top_k})")
    
    # Generate query embedding
    query_embedding = _create_embedding(query)
    
    # Load all indexes (or specific video)
    if video_filter:
        indexes = [load_audio_index(video_filter)]
        indexes = [idx for idx in indexes if idx is not None]
    else:
        indexes = load_all_indexes()
    
    if not indexes:
        logging.warning("No audio indexes found")
        return []
    
    # Search all chunks
    all_results = []
    
    for index in indexes:
        video_id = index["video_id"]
        chunks = index.get("chunks", [])
        
        for chunk in chunks:
            # Dual embedding search - check both raw and intent
            raw_score = 0.0
            intent_score = 0.0
            
            if "embedding_raw" in chunk:
                raw_score = cosine_similarity(query_embedding, chunk["embedding_raw"])
            
            if "embedding_intent" in chunk:
                intent_score = cosine_similarity(query_embedding, chunk["embedding_intent"])
            
            # Use max score (best match from either embedding)
            similarity = max(raw_score, intent_score)
            
            if similarity >= min_similarity:
                # Format result
                start_seconds = int(chunk.get("start", 0))
                end_seconds = int(chunk.get("end", 0))
                
                all_results.append({
                    "video_id": video_id,
                    "chunk_text": chunk.get("text", ""),
                    "start_time": _format_timestamp(start_seconds),
                    "end_time": _format_timestamp(end_seconds),
                    "timestamp_link": f"?t={start_seconds}",
                    "relevance_score": similarity,
                    "topic": chunk.get("topic", ""),
                    "intent": chunk.get("intent", ""),
                    "duration": chunk.get("duration", 0),
                    "raw_score": raw_score,
                    "intent_score": intent_score
                })
    
    # Re-rank results
    ranked_results = _rerank_results(all_results, query)
    
    # Return top K
    top_results = ranked_results[:top_k]
    
    logging.info(f"✅ Found {len(top_results)} results (from {len(all_results)} candidates)")
    
    return top_results


def _rerank_results(results, query):
    """
    Re-ranks results by multiple criteria for better relevance.
    
    Ranking factors:
    1. Similarity score (primary)
    2. Topic alignment (boost if query contains topic keyword)
    3. Chunk duration (prefer 20-30s chunks)
    4. Intent match (boost explanations for "how/why" queries)
    """
    
    query_lower = query.lower()
    
    for result in results:
        score = result["relevance_score"]
        
        # Topic boost (if query mentions the topic)
        topic = result.get("topic", "").lower()
        if topic and topic in query_lower:
            score += 0.1
        
        # Duration preference (prefer medium-length chunks)
        duration = result.get("duration", 0)
        if 20 <= duration <= 35:
            score += 0.05
        elif duration < 10 or duration > 50:
            score -= 0.05
        
        # Intent boost
        intent = result.get("intent", "")
        if "explanation" in query_lower and intent == "explanation":
            score += 0.08
        if "example" in query_lower and intent == "example":
            score += 0.08
        
        # Update score
        result["final_score"] = score
    
    # Sort by final score
    results.sort(key=lambda x: x.get("final_score", 0), reverse=True)
    
    return results


def _format_timestamp(seconds):
    """
    Formats seconds as MM:SS or HH:MM:SS.
    """
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def find_shorts_candidates(min_duration=20, max_duration=45, energy_topics=None):
    """
    Finds chunks suitable for repurposing as Shorts.
    
    Criteria:
    - 20-45 second duration
    - Complete idea (intent = explanation/example/conclusion)
    - High-energy topics (shock, curiosity, mistakes)
    - No dependencies on prior context
    
    Args:
        min_duration: Minimum chunk duration
        max_duration: Maximum chunk duration
        energy_topics: List of topics to prioritize (e.g., ["mistakes", "shock"])
    
    Returns:
        List of candidate chunks sorted by suitability
    """
    
    if energy_topics is None:
        energy_topics = ["mistakes", "shock", "surprising", "secret", "warning"]
    
    indexes = load_all_indexes()
    candidates = []
    
    for index in indexes:
        chunks = index.get("chunks", [])
        
        for chunk in chunks:
            duration = chunk.get("duration", 0)
            topic = chunk.get("topic", "").lower()
            intent = chunk.get("intent", "")
            
            # Check criteria
            if min_duration <= duration <= max_duration:
                # Check if self-contained
                if intent in ["explanation", "example", "conclusion"]:
                    suitability_score = 0.5
                    
                    # Boost for energy topics
                    if any(t in topic for t in energy_topics):
                        suitability_score += 0.3
                    
                    # Boost for ideal duration
                    if 25 <= duration <= 35:
                        suitability_score += 0.2
                    
                    candidates.append({
                        **chunk,
                        "video_id": index["video_id"],
                        "suitability_score": suitability_score
                    })
    
    # Sort by suitability
    candidates.sort(key=lambda x: x["suitability_score"], reverse=True)
    
    return candidates


if __name__ == "__main__":
    # Test search
    test_query = "എവിടെയാണ് ആളുകൾ പിഴവ് ചെയ്യുന്നത്?"
    
    results = search_audio(test_query, top_k=3)
    
    print("\n" + "="*60)
    print(f"SEARCH RESULTS: '{test_query}'")
    print("="*60)
    
    for i, result in enumerate(results):
        print(f"\n{i+1}. [{result['video_id']}] {result['start_time']} - {result['end_time']}")
        print(f"   Score: {result['relevance_score']:.3f} | Topic: {result['topic']} | Intent: {result['intent']}")
        print(f"   Text: {result['chunk_text'][:100]}...")
