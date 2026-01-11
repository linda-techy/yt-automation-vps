"""
Dual Embedding System for Malayalam Audio
Creates two embeddings per chunk for better search accuracy
"""

import logging
from openai import OpenAI
import os
import numpy as np

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_embeddings(chunk, use_dual=True):
    """
    Generates embeddings for a semantic chunk.
    
    Dual embedding strategy:
    1. Raw Malayalam: Natural spoken text (preserves exact phrasing)
    2. Intent-focused: Core concept extraction (improves search relevance)
    
    Args:
        chunk: Semantic chunk dict with 'text' field
        use_dual: If True, generate both raw and intent embeddings
    
    Returns:
        {
            "embedding_raw": [0.12, -0.34, ...],  # 1536 dims
            "embedding_intent": [0.45, 0.12, ...],  # 1536 dims (if dual)
            "text_raw": "original Malayalam",
            "text_intent": "concept-focused version" (if dual)
        }
    """
    
    text = chunk.get("text", "")
    
    if not text:
        logging.warning("Empty chunk text, skipping embedding")
        return None
    
    # Generate raw embedding
    raw_embedding = _create_embedding(text)
    
    result = {
        "embedding_raw": raw_embedding,
        "text_raw": text
    }
    
    # Generate intent embedding if dual mode
    if use_dual:
        intent_text = extract_core_concept(text)
        intent_embedding = _create_embedding(intent_text)
        
        result["embedding_intent"] = intent_embedding
        result["text_intent"] = intent_text
    
    return result


def _create_embedding(text):
    """
    Creates embedding using OpenAI API.
    
    Model: text-embedding-3-small (supports Malayalam, 1536 dims)
    """
    
    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
            encoding_format="float"
        )
        
        embedding = response.data[0].embedding
        return embedding
        
    except Exception as e:
        logging.error(f"Embedding creation failed: {e}")
        # Return zero vector as fallback
        return [0.0] * 1536


def extract_core_concept(malayalam_text):
    """
    Extracts core concept from Malayalam text for intent embedding.
    
    Uses GPT-4 to create a concise, concept-focused version.
    
    Args:
        malayalam_text: Original Malayalam text
    
    Returns:
        Concept-focused Malayalam phrase (10-15 words max)
    """
    
    prompt = f"""Extract the CORE CONCEPT from this Malayalam text in simple, clear terms.

Original: {malayalam_text}

Return a concise Malayalam phrase capturing the main idea (10-15 words maximum).
Focus on the KEY CONCEPT, not exact phrasing.

Example:
Original: "ഇവിടെ ആളുകൾ സാധാരണയായി ചെയ്യുന്ന വലിയ പിഴവ് ഇതാണ് - അവർ തുടക്കത്തിൽ തന്നെ പ്ലാനിംഗ് ചെയ്യുന്നില്ല"
Concept: "ആളുകൾ പ്ലാനിംഗില്ലാതെ തുടങ്ങുന്ന സാധാരണ പിഴവ്"

Return ONLY the Malayalam concept phrase:"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=100
        )
        
        concept = response.choices[0].message.content.strip()
        
        # Remove quotes if present
        concept = concept.strip('"').strip("'")
        
        return concept
        
    except Exception as e:
        logging.warning(f"Concept extraction failed: {e}, using original text")
        # Fallback: use first 15 words
        words = malayalam_text.split()[:15]
        return " ".join(words)


def batch_generate_embeddings(chunks, use_dual=True, batch_size=10):
    """
    Generates embeddings for multiple chunks in batches.
    
    More efficient than individual calls.
    
    Args:
        chunks: List of semantic chunks
        use_dual: Use dual embedding strategy
        batch_size: Number of chunks to process at once
    
    Returns:
        List of chunks with embeddings added
    """
    
    logging.info(f"🔢 Generating embeddings for {len(chunks)} chunks...")
    
    enriched_chunks = []
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        
        for chunk in batch:
            embeddings = generate_embeddings(chunk, use_dual=use_dual)
            
            if embeddings:
                # Merge embeddings into chunk
                chunk.update(embeddings)
                enriched_chunks.append(chunk)
    
    logging.info(f"✅ Generated embeddings for {len(enriched_chunks)} chunks")
    
    return enriched_chunks


def cosine_similarity(vec1, vec2):
    """
    Calculates cosine similarity between two vectors.
    
    Returns:
        Float between -1 and 1 (1 = identical, 0 = orthogonal, -1 = opposite)
    """
    
    # Convert to numpy arrays
    a = np.array(vec1)
    b = np.array(vec2)
    
    # Cosine similarity
    similarity = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    return float(similarity)


if __name__ == "__main__":
    # Test embedding generation
    test_chunk = {
        "text": "ഇവിടെ ആളുകൾ സാധാരണയായി ചെയ്യുന്ന വലിയ പിഴവ് ഇതാണ് - അവർ തുടക്കത്തിൽ തന്നെ പ്ലാനിംഗ് ചെയ്യുന്നില്ല. സോഫ്റ്റ്‌വെയർ എഞ്ചിനീയറിംഗിൽ ഇത് വളരെ സാധാരണമാണ്.",
        "start": 10.0,
        "end": 25.5,
        "topic": "mistakes",
        "intent": "explanation"
    }
    
    result = generate_embeddings(test_chunk, use_dual=True)
    
    print("\n" + "="*60)
    print("EMBEDDING RESULT")
    print("="*60)
    print(f"\nRaw text: {result['text_raw'][:100]}...")
    print(f"Intent text: {result['text_intent']}")
    print(f"\nRaw embedding dims: {len(result['embedding_raw'])}")
    print(f"Intent embedding dims: {len(result['embedding_intent'])}")
    print(f"\nFirst 5 dims (raw): {result['embedding_raw'][:5]}")
    print(f"First 5 dims (intent): {result['embedding_intent'][:5]}")
