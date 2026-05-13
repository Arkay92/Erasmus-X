import os
import json
import re
from core import config
from core.pack_injector import PackInjector
from core.stack_policies import StackPolicyRegistry

class CapabilityContract:
    def __init__(self, client, brain=None):
        self.client = client
        self.brain = brain
        self.contract_data = {}
        self.injector = PackInjector(brain) if brain else None
        self.stack_policies = StackPolicyRegistry()

    def build(self, user_input):
        """Generates the machine-readable build contract with stack fidelity enforcement."""
        print("[*] V12 Phase: Generating Capability Contract...")
        
        prompt_path = os.path.join(os.path.dirname(__file__), '..', 'shards', 'core', 'contractor_prompt.md')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            template = f.read()

        fidelity_guidance = self.stack_policies.guidance_text()
        
        prompt = template + fidelity_guidance + f"\n\nUSER REQUEST: {user_input}"
        
        try:
            response = self.client.chat.completions.create(
                model=config.AGENT_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            raw = response.choices[0].message.content
        except Exception as e:
            print(f"[!] Contract API error: {e}")
            raw = "{}"
        
        # Elite V14: Ultimate Robust JSON Extraction
        json_match = re.search(r"(\{.*\})", raw, re.DOTALL)
        if json_match:
            json_str = json_match.group(1).strip()
            try:
                self.contract_data = json.loads(json_str)
                
                # STACK FIDELITY ENFORCEMENT: Validate consistency
                self._validate_stack_fidelity()
                
                print(f"[+] Contract derived: {self.contract_data.get('project_name', 'Unknown')}")
                print(f"[+] Stack: {self.contract_data.get('stack', 'unknown')}")
                return self.contract_data
            except Exception as e:
                print(f"[*] Strict parse failed: {e}. Attempting aggressive normalization...")
                json_str = re.sub(r"```json|```", "", json_str).strip()
                try:
                    self.contract_data = json.loads(json_str)
                    self._validate_stack_fidelity()
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

    def _validate_stack_fidelity(self):
        """
        Validates that the contract specifies a coherent tech stack.
        Fixes common mistakes like specifying Prisma but not providing schema.
        """
        stack = self.contract_data.get('stack', '').lower()
        critical_files = self.contract_data.get('critical_files', [])
        
        if 'sqlite' in stack and 'prisma' in stack:
            print("[!] Stack Conflict: Cannot specify both 'prisma' and 'sqlite'")
            stack = stack.replace('prisma', '').replace('|', ' ').strip()
            self.contract_data['stack'] = stack
        self.contract_data['critical_files'] = critical_files
        self.contract_data = self.stack_policies.apply_required_files(self.contract_data)
    
    def inject_required_packs(self, file_map):
        """
        Uses pack injector to automatically inject missing required packs.
        
        Args:
            file_map: Current file mapping
        
        Returns: Updated file_map with injected packs
        """
        if not self.injector:
            return file_map
        
        injected, updated_map = self.injector.inject_packs(self.contract_data, file_map)
        
        if injected:
            print(f"[+] Injected {len(injected)} files from required packs")
        
        return updated_map

    def get_assertion_for_file(self, filename):
        for ass in self.contract_data.get('semantic_assertions', []):
            if ass['file'] == filename:
                return ass['assertion']
        return None
