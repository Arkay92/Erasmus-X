import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from openai import OpenAI
from core import config, prompts
import re

def debug():
    client = OpenAI(base_url=config.API_BASE_URL, api_key=config.API_KEY)
    main_q = "What was the state of the universe during the Planck epoch?"
    
    print(f"[*] Calling LLM: {config.MODEL_NAME}")
    try:
        response = client.chat.completions.create(
            model=config.MODEL_NAME,
            messages=[{"role": "user", "content": "Tell me a joke about space."}],
            max_tokens=200,
            temperature=0.7
        )
        print(f"--- JOKE RAW ---\n{response.choices[0].message.content}\n")
        
        response = client.chat.completions.create(
            model=config.MODEL_NAME,
            messages=[{"role": "user", "content": prompts.META_GEN_PROMPT + main_q}],
            max_tokens=200,
            temperature=0
        )
        raw = response.choices[0].message.content
        print(f"--- META RAW ---\n{raw}\n--- END RAW ---")
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    debug()
