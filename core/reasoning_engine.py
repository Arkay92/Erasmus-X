import os
import json
import time
import re
from core import config, prompts

class ReasoningEngine:
    def __init__(self, client, brain=None):
        self.client = client
        self.brain = brain
        self.lessons = []

    def _save_lesson(self, lesson_obj):
        """Saves a reasoning lesson into the brain's deterministic registry."""
        self.lessons.append(lesson_obj)
        if not self.brain: return
        self.brain.record_lesson(lesson_obj)

    def analyze_task(self, user_input, messages, outcome_status, critic_report=""):
        """Performs a Meta-Critic pass to extract reasoning lessons."""
        print(f"[*] Reasoning Phase: Analyzing reasoning performance for RL feedback...")
        
        # 1. Extract CoT (Working Notes) from history
        cot = ""
        for msg in reversed(messages):
            if msg['role'] == 'assistant':
                # Look for Working Notes markers [Goal], [Action], etc.
                if "[Goal]" in msg['content'] or "[Action]" in msg['content']:
                    cot = msg['content']
                    break
        
        if not cot:
            print("[!] No Chain of Thought found in recent history. Skipping analysis.")
            return

        # 2. Run Meta-Critic
        meta_prompt = prompts._load_prompt("reasoning_meta_critic.md")
        meta_prompt = meta_prompt.replace("{{user_input}}", user_input)
        meta_prompt = meta_prompt.replace("{{cot}}", cot)
        meta_prompt = meta_prompt.replace("{{outcome_status}}", outcome_status)
        meta_prompt = meta_prompt.replace("{{critic_report}}", critic_report)

        try:
            response = self.client.chat.completions.create(
                model=config.AGENT_MODEL_NAME,
                messages=[{"role": "user", "content": meta_prompt}],
                temperature=0.1,
                timeout=getattr(config, "REASONING_TIMEOUT", 5),
            )
            raw_analysis = response.choices[0].message.content
            
            # 3. Extract Lesson
            lesson_match = re.search(r"LEARNED_LESSON:\s*(.*)", raw_analysis)
            if lesson_match:
                lesson_text = lesson_match.group(1).strip()
                if lesson_text.lower() != "none" and len(lesson_text) > 10:
                    new_lesson = {
                        "timestamp": time.time(),
                        "user_input": user_input[:100],
                        "lesson": lesson_text,
                        "quality_score": self._parse_score(raw_analysis)
                    }
                    self._save_lesson(new_lesson)
                    print(f"[+] Reasoning Lesson Learned: {lesson_text[:60]}...")
        except Exception as e:
            print(f"[!] Reasoning Engine Error: {e}")

    def _parse_score(self, text):
        match = re.search(r"REASONING_QUALITY:\s*(\d+)", text)
        return int(match.group(1)) if match else 0

    def get_relevant_lessons(self, query, limit=5):
        """Returns relevant lessons from the brain's deterministic registry."""
        if not self.brain:
            return [l['lesson'] for l in self.lessons[-limit:]]
        
        lessons = self.brain.get_lessons(limit=limit) or self.lessons
        # Simple keyword relevance filter
        keywords = query.lower().split()
        relevant = []
        for l in reversed(lessons):
            lesson_text = l.get('lesson', '').lower()
            if any(k in lesson_text for k in keywords):
                relevant.append(l['lesson'])
            if len(relevant) >= limit:
                break
        
        # If no keyword matches, return most recent
        if not relevant and lessons:
            relevant = [l['lesson'] for l in lessons[-limit:]]
            
        return relevant
