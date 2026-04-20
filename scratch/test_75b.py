import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from openai import OpenAI
from core import config, prompts
import re

def test():
    client = OpenAI(base_url=config.API_BASE_URL, api_key=config.API_KEY)
    main_q = "What was the state of the universe during the Planck epoch?"
    
    # We test the exact prompt used in seed.py
    prompt_content = prompts.META_GEN_PROMPT + main_q + "\nQ1:"
    
    print(f"[*] Testing 7.5B Model with Anchor: {config.MODEL_NAME}")
    print(f"[*] Prompt:\n{prompt_content}\n")
    
    try:
        response = client.chat.completions.create(
            model=config.MODEL_NAME,
            messages=[{"role": "user", "content": prompt_content}],
            max_tokens=100,
            temperature=0.7
        )
        raw = response.choices[0].message.content
        print(f"--- RAW RESPONSE ---\n{raw}\n--- END RAW ---")
        
        # Test the extraction prompt too
        extraction_prompt = f"Extract exactly 3-5 knowledge triplets from the text below.\nOutput ONLY in the format: [FACT] subject | relation | object\n\nText: Some test text about the universe."
        resp_ext = client.chat.completions.create(
            model=config.MODEL_NAME,
            messages=[{"role": "user", "content": extraction_prompt}],
            max_tokens=100,
            temperature=0
        )
        print(f"--- EXTRACTION RAW ---\n{resp_ext.choices[0].message.content}\n")
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    test()
