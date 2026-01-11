"""
Semantic Chunking for Malayalam Audio
Chunks audio by MEANING, not time - critical for search relevance
"""

import logging
from openai import OpenAI
import json
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def chunk_by_semantics(transcript_segments, min_duration=15, max_duration=40, topic_hint=None):
    """
    Chunks transcript by semantic boundaries using GPT-4.
    
    This is THE KEY to good search - chunks represent complete ideas.
    
    Args:
        transcript_segments: Whisper segments with timestamps
        min_duration: Minimum chunk duration (seconds)
        max_duration: Maximum chunk duration (seconds)
        topic_hint: Optional topic for context
    
    Returns:
        [
            {
                "text": "complete semantic chunk",
                "start": 15.2,
                "end": 42.8,
                "duration": 27.6,
                "topic": "auto-detected topic",
                "intent": "explanation/example/conclusion/question"
            }
        ]
    """
    
    if not transcript_segments:
        logging.warning("No segments to chunk")
        return []
    
    logging.info(f"🧠 Semantic chunking {len(transcript_segments)} segments...")
    
    # Combine all segments into full text with timestamps
    full_transcript = []
    for seg in transcript_segments:
        full_transcript.append({
            "text": seg["text"],
            "start": seg["start"],
            "end": seg["end"]
        })
    
    # Ask GPT-4 to identify semantic boundaries
    boundaries = identify_semantic_boundaries(full_transcript, topic_hint)
    
    # Create chunks based on boundaries
    chunks = create_chunks_from_boundaries(full_transcript, boundaries, min_duration, max_duration)
    
    # Detect topic and intent for each chunk
    for chunk in chunks:
        analysis = analyze_chunk_intent(chunk["text"])
        chunk["topic"] = analysis.get("topic", "general")
        chunk["intent"] = analysis.get("intent", "explanation")
    
    logging.info(f"✅ Created {len(chunks)} semantic chunks (avg {sum(c['duration'] for c in chunks)/len(chunks):.1f}s)")
    
    return chunks


def identify_semantic_boundaries(segments, topic_hint=None):
    """
    Uses GPT-4 to identify where semantic topic shifts occur.
    
    Returns:
        List of timestamps where boundaries should be placed
    """
    
    # Build timeline representation
    timeline = []
    for i, seg in enumerate(segments):
        timeline.append(f"[{seg['start']:.1f}s] {seg['text']}")
    
    timeline_text = "\n".join(timeline[:50])  # Limit to avoid token limits
    
    prompt = f"""You are analyzing a Malayalam audio transcript to find SEMANTIC BOUNDARIES.

{f"Topic: {topic_hint}" if topic_hint else ""}

Transcript with timestamps:
{timeline_text}

Identify timestamps where the speaker:
1. Changes topic or subject
2. Starts a new example or explanation
3. Shifts from explanation to conclusion
4. Asks a question then answers it
5. Moves to a completely new concept

Return ONLY a JSON array of boundary timestamps (in seconds):
["15.2", "42.8", "68.3"]

If no clear boundaries, return empty array: []
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200
        )
        
        content = response.choices[0].message.content.strip()
        
        # Parse JSON
        if "```" in content:
            content = content.split("```")[1].replace("json", "").strip()
        
        boundaries = json.loads(content)
        boundaries = [float(b) for b in boundaries]
        
        logging.info(f"   Found {len(boundaries)} semantic boundaries")
        return boundaries
        
    except Exception as e:
        logging.warning(f"GPT-4 boundary detection failed: {e}, using heuristic")
        return []


def create_chunks_from_boundaries(segments, boundaries, min_duration, max_duration):
    """
    Creates chunks based on identified boundaries.
    
    Enforces min/max duration constraints.
    """
    
    chunks = []
    current_chunk = []
    current_start = segments[0]["start"] if segments else 0
    
    for seg in segments:
        current_chunk.append(seg)
        
        # Check if we've hit a boundary
        is_boundary = any(abs(seg["end"] - b) < 2.0 for b in boundaries)
        
        if current_chunk:
            chunk_duration = seg["end"] - current_start
            
            # Create chunk if:
            # - Hit a boundary AND duration is acceptable
            # - OR duration exceeds max
            if (is_boundary and chunk_duration >= min_duration) or chunk_duration >= max_duration:
                chunk_text = " ".join([s["text"] for s in current_chunk])
                chunks.append({
                    "text": chunk_text,
                    "start": current_start,
                    "end": seg["end"],
                    "duration": chunk_duration
                })
                
                # Reset
                current_chunk = []
                if segments.index(seg) < len(segments) - 1:
                    current_start = segments[segments.index(seg) + 1]["start"]
    
    # Add remaining as final chunk
    if current_chunk:
        chunk_text = " ".join([s["text"] for s in current_chunk])
        chunks.append({
            "text": chunk_text,
            "start": current_start,
            "end": current_chunk[-1]["end"],
            "duration": current_chunk[-1]["end"] - current_start
        })
    
    return chunks


def analyze_chunk_intent(text):
    """
    Detects the topic and intent of a chunk.
    
    Returns:
        {
            "topic": "mistakes/technology/explanation",
            "intent": "explanation/example/conclusion/question"
        }
    """
    
    prompt = f"""Analyze this Malayalam text and identify:
1. TOPIC (one word): What is being discussed?
2. INTENT (one word): Is this an explanation, example, conclusion, or question?

Text: {text[:300]}

Return ONLY JSON:
{{"topic": "...", "intent": "..."}}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=50
        )
        
        content = response.choices[0].message.content.strip()
        
        if "```" in content:
            content = content.split("```")[1].replace("json", "").strip()
        
        analysis = json.loads(content)
        return analysis
        
    except Exception as e:
        logging.warning(f"Intent analysis failed: {e}")
        return {"topic": "general", "intent": "explanation"}


if __name__ == "__main__":
    # Test semantic chunking
    test_segments = [
        {"text": "ഇവിടെ ആളുകൾ സാധാരണയായി ചെയ്യുന്ന പിഴവ് ഇതാണ്", "start": 10.0, "end": 15.5},
        {"text": "അവർ തുടക്കത്തിൽ തന്നെ ഈ കാര്യം മനസ്സിലാക്കുന്നില്ല", "start": 15.5, "end": 20.2},
        {"text": "ഇതിന് ഒരു ഉദാഹരണം പറയാം", "start": 20.2, "end": 22.8},
        {"text": "സോഫ്റ്റ്‌വെയർ എഞ്ചിനീയറിംഗിൽ ഈ പിശക് വളരെ സാധാരണമാണ്", "start": 22.8, "end": 28.5},
        {"text": "അതുകൊണ്ട് നിങ്ങൾ ഇത് ഓർത്തുവെക്കണം", "start": 28.5, "end": 32.0},
    ]
    
    chunks = chunk_by_semantics(test_segments, topic_hint="technology mistakes")
    
    print("\n" + "="*60)
    print("SEMANTIC CHUNKS")
    print("="*60)
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i+1}:")
        print(f"  Time: {chunk['start']:.1f}s - {chunk['end']:.1f}s ({chunk['duration']:.1f}s)")
        print(f"  Topic: {chunk['topic']}, Intent: {chunk['intent']}")
        print(f"  Text: {chunk['text'][:100]}...")
