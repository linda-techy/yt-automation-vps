"""
Policy Guard - Content Compliance & Safety Engine

Ensures all generated content adheres to YouTube Partner Program (YPP) policies.
Acts as a "Safety Gate" before any expensive rendering occurs.

Checks for:
1. Hate Speech & Harassment
2. Self-Harm or Dangerous Content
3. Graphic Violence
4. Copyright Risks (Lyrics, protected phrases)
5. Misinformation (Medical, Civic)
"""

import logging
import json
from langchain_core.messages import SystemMessage, HumanMessage

# Use wrapped LLM adapter with error handling
from adapters.openai.llm_wrapper import get_llm_fast
from utils.logging.tracer import tracer

llm_safety = get_llm_fast()

POLICY_SYSTEM_PROMPT = """You are the 'Policy Guard' AI for a YouTube automation channel.
Your job is to strictly enforce YouTube's Community Guidelines and Ad-Friendly Guidelines.
You must flag any content that is risky for monetization or channel safety.

RISK CATEGORIES TO FLAGGED:
1. HATE SPEECH: targeting protected groups.
2. HARASSMENT: targeting specific individuals.
3. SELF-HARM: promotion or detailed instructions.
4. VIOLENCE: graphic or gratuitous violence.
5. SHOCKING: disgusting or repulsive content.
6. MISINFORMATION: harmful medical or civic lies.
7. COPYRIGHT: song lyrics, famous book texts (Harry Potter, etc).
8. SEXUAL: nudity or sexually explicit themes.

If the content is purely educational, documentary, or fictional (and safe), it passes.
Be strict on "Ad-Suitability" (no swearing, no controversial topics).
"""

def check_script_safety(script_text: str, topic: str) -> dict:
    """
    Analyzes a script for YPP compliance validation.
    Returns a dict with 'safe' (bool) and 'flags' (list).
    """
    prompt = f"""
    Please analyze this script for YouTube policy violations.

    TOPIC: {topic}
    SCRIPT:
    {script_text}

    Return JSON:
    {{
        "safe": true/false,
        "rating": "G/PG/PG-13/R",
        "flags": ["list", "of", "issues"],
        "reason": "explanation",
        "score": 0-10 (10 is perfectly safe)
    }}
    """

    try:
        response = llm_safety.invoke(
            [
                SystemMessage(content=POLICY_SYSTEM_PROMPT),
                HumanMessage(content=prompt)
            ],
            trace_id=tracer.get_trace_id(),
            compress_context=True
        )
        
        content = response.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
            
        result = json.loads(content)
        
        # Log findings
        if result.get("safe", False):
            logging.info(f"[PolicyGuard] ✅ Script Safe (Score: {result.get('score')})")
        else:
            logging.warning(f"[PolicyGuard] ⚠️ Safety Flags: {result.get('flags')}")
            
        return result

    except Exception as e:
        logging.error(f"[PolicyGuard] Analysis failed: {e}")
        # Fail open or closed? Better to fail closed for safety, but let's warn for now.
        return {"safe": False, "flags": ["Analysis Failed"], "error": str(e)}

if __name__ == "__main__":
    # Test
    test_script = "Today we talk about how to hack your neighbor's wifi and steal their data."
    print(check_script_safety(test_script, "Wifi Hacking"))
