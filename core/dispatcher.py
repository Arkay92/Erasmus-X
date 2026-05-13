import json
import re
from core import config, prompts

class NeurosymbolicDispatcher:
    """Elite V15: Dynamic reasoning layer that selects the optimal operation path."""
    def __init__(self, client):
        self.client = client
        self.system_prompt = prompts.DISPATCHER_PROMPT

    def select_action(self, user_input, context_summary=""):
        """Analyzes task and returns a structured Action object."""
        print(f"[*] Dispatcher: Analyzing task complexity and tool availability...")
        
        full_prompt = f"{self.system_prompt}\n\nUSER_INPUT: {user_input}\nCONTEXT: {context_summary}"
        
        try:
            response = self.client.chat.completions.create(
                model=config.AGENT_MODEL_NAME,
                messages=[{"role": "system", "content": full_prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            raw_json = response.choices[0].message.content
            action = json.loads(raw_json)
            
            print(f"[+] Dispatcher choice: {action.get('operation')} (Reasoning: {action.get('thought')})")
            return action
        except Exception as e:
            print(f"[!] Dispatcher Error: {e}. Falling back to default CHAT.")
            return {
                "operation": "CHAT",
                "thought": "Fallback due to dispatcher error",
                "payload": {"query": user_input},
                "confidence": 0.5
            }

    def validate_action(self, action):
        """Ensures the selected action has required payload fields."""
        required = {
            "RESEARCH": ["query"],
            "SEARCH": ["query"],
            "CODE": ["objective"],
            "PROJECT": ["objective"],
            "DELEGATE": ["delegations"]
        }
        
        op = action.get("operation")
        if op not in required:
            return True
            
        payload = action.get("payload", {})
        for field in required[op]:
            if field not in payload:
                return False
        return True
