import os
from core import config

class BuildCritic:
    def __init__(self, client):
        self.client = client

    def evaluate(self, user_input, contract, file_map):
        """Separate LLM pass to score the project quality."""
        print("[*] V12 Phase: Running Critic Evaluation...")
        
        # Build Context for Critic (V17.1 Context Guarding)
        context = ""
        # Limit total files to prevent manifest overflow
        target_files = list(file_map.items())[:10]
        for name, content in target_files:
            # Surgical snapshot: first 400 chars of each file
            context += f"FILE: {name}\n```\n{content[:400]}\n```\n\n"

        prompt = f"""You are a senior code reviewer. You are auditing a newly generated project against a formal Capability Contract.

USER REQUEST: {user_input}
CONTRACT: {contract}

PROJECT FILES:
{context}

Tasks:
1. Score the project (0-100) based on:
   - Completeness (Are all critical files real?)
   - Logic Depth (Is auth/db actually implemented or just hollow?)
   - Correctness (Are imports and framework patterns correct?)
2. If the score is < 100, identify EXACT REASONS for rejection.
3. Check for forbidden placeholders/shortcuts.

Output Format:
SCORE: <number>
VIOLATIONS:
- <violation 1>
- <violation 2>
...

If SCORE < 100, you MUST provide exactly one JSON block:
[REPAIR: JSON]
{{
  "targets": [
    {{"file": "path/to/file.tsx", "reason": "Specific technical reason for logic failure"}},
    {{"file": "new/feature/file.ts", "reason": "Feature Induction: This file is required to implement the missing logic for X."}}
  ]
}}
[/REPAIR]

Note: You can and should suggest NEW files that are NOT in the PROJECT FILES list if they are necessary to fulfill the CONTRACT (e.g. adding a database utility or API route).
If you see a file required by the CONTRACT but missing from the PROJECT FILES, you MUST include it in the [REPAIR: JSON] list.

If perfect, output: SCORE: 100
"""
        
        response = self.client.chat.completions.create(
            model=config.MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )
        
        raw = response.choices[0].message.content
        return raw
