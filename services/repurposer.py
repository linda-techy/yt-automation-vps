import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

llm = ChatOpenAI(model="gpt-4o", temperature=0.7)

REPURPOSER_PROMPT = """You are a Viral Content Strategist.
I will provide you with a Long-Form Video Script (8-10 mins).
Your Goal: Extract 5 DISTINCT, SELF-CONTAINED YouTube Shorts scripts from this content.

SOURCE SCRIPT:
{long_script}

REQUIREMENTS:
1. **5 Independent Scripts**: Each must make sense alone.
2. **Standard Shorts Structure**: Hook (0-5s) -> Value (15-40s) -> CTA (45-50s).
3. **Curiosity Loop**: End each short with "Watch the full video to learn X".
4. **Malayalam Script**: Use the exact same style (Malayalam Unicode + "A.I." dots).
5. **No Duplicates**: Each short must cover a different angle (e.g., Short 1: The Problem, Short 2: The Solution, Short 3: The Case Study...).

FORMAT (JSON List):
[
  {{
    "title": "Shorts Title 1",
    "script": "Full Malayalam Script...",
    "visual_cues": ["..."],
    "thumbnail_text": "..."
  }},
  ... (5 times)
]
"""

def repurpose_long_script(long_script_json):
    """
    Takes the JSON output from generate_long_script and derives 5 Shorts.
    """
    # Convert long script json to string for context
    long_script_str = json.dumps(long_script_json, ensure_ascii=False)
    
    msg = HumanMessage(content=REPURPOSER_PROMPT.format(long_script=long_script_str))
    response = llm.invoke([msg])
    
    try:
        content = response.content.strip()
        if "```json" in content:
            content = content.replace("```json", "").replace("```", "")
            
        shorts_list = json.loads(content)
        return shorts_list
    except Exception as e:
        print(f"Repurposing failed: {e}")
        return []

if __name__ == "__main__":
    # Mock input for testing
    mock_script = {
        "title": "The Future of AI",
        "sections": [
            {"header": "Intro", "content": "AI is changing everything..."},
            {"header": "Medical AI", "content": "Doctors use AI to cure cancer..."}
        ]
    }
    res = repurpose_long_script(mock_script)
    print(json.dumps(res, indent=2, ensure_ascii=False))
