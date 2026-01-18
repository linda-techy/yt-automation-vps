import json
import logging
from langchain_core.messages import HumanMessage

# Use wrapped LLM with error handling
from adapters.openai.llm_wrapper import get_llm_creative
from utils.prompts.registry import registry
from utils.prompts.compressor import compressor
from utils.logging.tracer import tracer

llm = get_llm_creative()


def repurpose_long_script(long_script_json):
    """
    Takes the JSON output from generate_long_script and derives 5 Shorts.
    Uses prompt registry and context compression for token optimization.
    """
    # Compress long script before sending (reduce token usage)
    script_summary = compressor.compress_dict(long_script_json, max_length=500)
    
    # Use prompt registry
    prompt = registry.get_repurpose_prompt()
    # Add compressed script to prompt
    full_prompt = f"{prompt}\nSOURCE_SCRIPT:{script_summary}"
    
    try:
        msg = HumanMessage(content=full_prompt)
        response = llm.invoke(
            [msg],
            trace_id=tracer.get_trace_id(),
            compress_context=True
        )
        
        content = response.content.strip()
        if "```json" in content:
            content = content.replace("```json", "").replace("```", "")
            
        shorts_list = json.loads(content)
        
        if not isinstance(shorts_list, list):
            logging.warning("[Repurposer] Response not a list, attempting to fix")
            shorts_list = [shorts_list] if shorts_list else []
        
        return shorts_list
    except Exception as e:
        logging.error(f"[Repurposer] Repurposing failed: {e}")
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
