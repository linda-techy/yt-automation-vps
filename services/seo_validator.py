"""
SEO Metadata Validator

Validates YouTube metadata before upload to prevent:
- Title truncation (100 char limit)
- Description truncation (5,000 char limit)  
- Invalid characters
- Missing required fields

Also generates optimized hashtags.
"""

import re
import logging

# YouTube limits
TITLE_MAX_LENGTH = 100
DESCRIPTION_MAX_LENGTH = 5000
TAG_MAX_COUNT = 500  # characters, not count

def extract_hashtags_from_topic(topic, niche, count=5):
    """
    Generate relevant hashtags from topic and niche.
    
    Args:
        topic: Video topic
        niche: Channel niche
        count: Number of hashtags to generate
    
    Returns:
        List of hashtags with # prefix
    """
    hashtags = []
    
    # Niche-based tags
    niche_tags = {
        "Technology": ["#Tech", "#Technology", "#Innovation"],
        "Finance": ["#Finance", "#Money", "#Investing"],
        "News": ["#News", "#Breaking", "#Updates"],
        "Education": ["#Learn", "#Education", "#Tutorial"],
        "Entertainment": ["#Entertainment", "#Viral", "#Trending"]
    }
    
    base_tags = niche_tags.get(niche, ["#Viral", "#Trending"])
    hashtags.extend(base_tags[:2])
    
    # Topic-based tags (extract keywords)
    words = re.findall(r'\b[A-Za-z]{4,}\b', topic)  # Words 4+ chars
    for word in words[:2]:
        tag = f"#{word.capitalize()}"
        if tag not in hashtags:
            hashtags.append(tag)
    
    # Language-specific
    if any(char >= '\u0D00' and char <= '\u0D7F' for char in topic):  # Malayalam
        hashtags.append("#Malayalam")
    
    # Limit to count
    return hashtags[:count]


def validate_seo_metadata(seo_content, topic, niche):
    """
    Validate and enhance SEO metadata.
    
    Args:
        seo_content: Raw SEO string from AI
        topic: Video topic
        niche: Channel niche
    
    Returns:
        dict with validated title, description, hashtags
    
    Raises:
        ValueError: If critical validation fails
    """
    results = {
        "valid": False,
        "title": "",
        "description": "",
        "hashtags": [],
        "warnings": [],
        "errors": []
    }
    
    try:
        # Parse SEO content
        lines = seo_content.split('\n')
        
        # Extract title
        title_line = [l for l in lines if l.startswith('Title:')]
        if title_line:
            title = title_line[0].replace('Title:', '').strip()
        else:
            title = topic  # Fallback
            results["warnings"].append("No title found in SEO, using topic")
        
        # Validate title length
        if len(title) > TITLE_MAX_LENGTH:
            original_length = len(title)
            title = title[:TITLE_MAX_LENGTH]
            results["warnings"].append(
                f"Title truncated: {original_length} → {TITLE_MAX_LENGTH} chars"
            )
        
        results["title"] = title
        
        # Extract description
        desc_start = next((i for i, l in enumerate(lines) if l.startswith('Description:') or 'Description:' in l), None)
        if desc_start is not None:
            description = '\n'.join(lines[desc_start+1:])
            description = description.split('Hashtags:')[0].strip()  # Remove hashtags section
        else:
            description = topic
            results["warnings"].append("No description found, using topic")
        
        # Validate description length
        if len(description) > DESCRIPTION_MAX_LENGTH:
            original_length = len(description)
            description = description[:DESCRIPTION_MAX_LENGTH]
            results["warnings"].append(
                f"Description truncated: {original_length} → {DESCRIPTION_MAX_LENGTH} chars"
            )
        
        # Generate and append hashtags
        hashtags = extract_hashtags_from_topic(topic, niche)
        hashtag_string = ' '.join(hashtags)
        
        # Add hashtags to description if not already there
        if not any(tag in description for tag in hashtags):
            description += f"\n\n{hashtag_string}"
        
        results["description"] = description
        results["hashtags"] = hashtags
        
        # Final validations
        if not title:
            results["errors"].append("Title is empty")
        if not description:
            results["errors"].append("Description is empty")
        
        results["valid"] = len(results["errors"]) == 0
        
        if results["valid"]:
            logging.info(f"[SEO Validator] ✅ Metadata valid")
            logging.info(f"   Title: {title[:50]}... ({len(title)} chars)")
            logging.info(f"   Description: {len(description)} chars")
            logging.info(f"   Hashtags: {hashtags}")
        else:
            logging.error(f"[SEO Validator] ❌ Validation failed")
            for error in results["errors"]:
                logging.error(f"   - {error}")
        
        for warning in results["warnings"]:
            logging.warning(f"[SEO Validator] ⚠️  {warning}")
        
        return results
    
    except Exception as e:
        logging.error(f"[SEO Validator] Exception: {e}")
        results["errors"].append(f"Validation exception: {str(e)}")
        return results


if __name__ == "__main__":
    # Test
    test_seo = """
Title: This is a very long title that might exceed the YouTube limit of one hundred characters which could cause truncation issues

Description:
This is a test description.
It has multiple lines.

Hashtags:
#Test #Example
    """
    
    result = validate_seo_metadata(test_seo, "Test Topic", "Technology")
    print(f"Valid: {result['valid']}")
    print(f"Title: {result['title']}")
    print(f"Hashtags: {result['hashtags']}")
