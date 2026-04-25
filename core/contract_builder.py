import os
import json
import re
from core import config

class CapabilityContract:
    def __init__(self, client):
        self.client = client
        self.contract_data = {}

    def build(self, user_input):
        """Generates the machine-readable build contract."""
        print("[*] V12 Phase: Generating Capability Contract...")
        
        prompt_path = os.path.join(os.path.dirname(__file__), '..', 'shards', 'core', 'contractor_prompt.md')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            template = f.read()

        prompt = template + f"\n\nUSER REQUEST: {user_input}"
        
        response = self.client.chat.completions.create(
            model=config.MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        
        raw = response.choices[0].message.content
        
        # Elite V14: Ultimate Robust JSON Extraction
        # Strategy: find the first { and last }, ignoring everything outside.
        # If loads fails, try to strip trailing/leading junk.
        json_match = re.search(r"(\{.*\})", raw, re.DOTALL)
        if json_match:
            json_str = json_match.group(1).strip()
            try:
                self.contract_data = json.loads(json_str)
                print(f"[+] Contract derived: {self.contract_data.get('project_name', 'Unknown')}")
                return self.contract_data
            except Exception as e:
                print(f"[*] Strict parse failed: {e}. Attempting aggressive normalization...")
                # Sanitization: remove markdown wrappers if they leaked into the braces
                json_str = re.sub(r"```json|```", "", json_str).strip()
                try:
                    self.contract_data = json.loads(json_str)
                    print(f"[+] Contract derived via normalization.")
                    return self.contract_data
                except Exception as e2:
                    print(f"[!] Contract parse error: {e2}")
        
        # Fallback empty contract
        print("[!] Failed to derive formal contract. Falling back to generic spec.")
        self.contract_data = {
            "stack": "unknown",
            "features": [],
            "critical_files": [],
            "forbidden_shortcuts": ["// TODO", "placeholder = true"]
        }
        return self.contract_data

    def get_assertion_for_file(self, filename):
        for ass in self.contract_data.get('semantic_assertions', []):
            if ass['file'] == filename:
                return ass['assertion']
        return None
