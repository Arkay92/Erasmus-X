import re
from core import config, prompts
from utils.text_utils import count_tokens

class ContextBuilder:
    def __init__(self, compressor=None, reasoning_engine=None):
        self.compressor = compressor
        self.reasoning_engine = reasoning_engine

    def build_messages(self, user_input, history, memory_results, mode="FAST"):
        """Tiered context assembly with hard token budgeting."""
        token_limit = config.DEEP_MODE_CONTEXT_TOKENS if mode == "DEEP" else config.FAST_MODE_CONTEXT_TOKENS
        sys_prompt = prompts.FAST_SYSTEM_PROMPT if mode == "FAST" else prompts.SYSTEM_PROMPT
        
        # Determine if this is a coding task to inject execution policy
        is_code = any(k in user_input.lower() for k in ['write', 'code', 'script', 'implement', 'algorithm', 'project'])
        if is_code or mode == "DEEP":
            sys_prompt += "\n" + prompts.WORKING_NOTES_MODE
            if is_code:
                sys_prompt += "\n" + prompts.EXECUTION_POLICY_CODE
                if "next.js" in user_input.lower():
                    sys_prompt += "\n[POLICY] Next.js detected: MANDATORY use of .tsx for all component/page files. NO .js allowed."
        
        # Token Budgeting (Priority: Current Request > Session State > History > Web > Facts)
        budget = token_limit - count_tokens(sys_prompt) - 512 # Reserve 512 for completion
        
        # 1. Current Objective (Top Priority)
        user_objective_block = f"### CURRENT OBJECTIVE\n{user_input}\n"
        budget -= count_tokens(user_objective_block)
        
        # 2. Session State / Grounding (High Priority)
        state_block = ""
        session_mems = memory_results.get('session', [])
        if session_mems:
            latest_state = session_mems[0][1] # [(score, doc), ...]
            state_text = latest_state.replace("[SESSION_STATE] Summary:", "").strip()
            state_block = f"### PREVIOUS STATE (Grounded)\n{state_text}\n"
            budget -= count_tokens(state_block)
        
        # 3. Dynamic History (Sliding Window)
        history_msgs = self._get_sliding_history(history, budget=min(budget, 1000))
        budget -= sum(count_tokens(m['content']) for m in history_msgs)
        
        # 4. Knowledge Retrieval (Supplemental)
        knowledge_blocks = []
        
        # Facts from KG
        facts = memory_results.get('facts', [])
        if facts and budget > 200:
            fact_text = f"### PROJECT FACTS\n" + " | ".join(facts[:3])
            knowledge_blocks.append(fact_text)
            budget -= count_tokens(fact_text)
            
        # Web / Research Context
        web_text = memory_results.get('web')
        if web_text and budget > 500:
            web_block = f"### RESEARCH FINDINGS\n{web_text[:800]}"
            knowledge_blocks.append(web_block)
            budget -= count_tokens(web_block)

        # 5. Reasoning Lessons (Reinforcement Learning)
        lessons_block = ""
        if self.reasoning_engine and config.ENABLE_REASONING_ENGINE:
            relevant_lessons = self.reasoning_engine.get_relevant_lessons(user_input, limit=config.MAX_REASONING_LESSONS_CONTEXT)
            if relevant_lessons:
                lessons_block = prompts.CONTEXT_LESSONS + "\n".join([f"- {l}" for l in relevant_lessons]) + "\n"
                budget -= count_tokens(lessons_block)

        # 6. Failure Memory (Mistake Avoidance)
        failures_block = ""
        failures = memory_results.get('failures', [])
        if failures and budget > 300:
            failures_block = "### RECENT BUILD FAILURES (Avoid these mistakes)\n"
            for f in failures:
                failures_block += f"- Request: {f['request']}\n  Failures: {f['failures']}\n"
            budget -= count_tokens(failures_block)

        # Final Assembly
        content_layers = []
        if failures_block: content_layers.append(failures_block)
        if lessons_block: content_layers.append(lessons_block)
        if state_block: content_layers.append(state_block)
        content_layers.extend(knowledge_blocks)
        content_layers.append(user_objective_block)
        
        full_user_content = "\n\n".join(content_layers)
        
        # Pre-Inference Compression for DEEP mode
        if mode == "DEEP" and self.compressor:
            full_user_content = self.compressor.compress(full_user_content)
            
        messages = [{"role": "system", "content": sys_prompt}]
        messages.extend(history_msgs)
        messages.append({"role": "user", "content": full_user_content})
        
        return messages, count_tokens(full_user_content) + count_tokens(sys_prompt)

    def _get_sliding_history(self, history, budget=500):
        """Prunes conversation history to fit within a specific sub-budget."""
        pruned = []
        current_cost = 0
        for msg in reversed(history):
            cost = count_tokens(msg['content'])
            if current_cost + cost > budget:
                break
            pruned.insert(0, msg)
            current_cost += cost
        return pruned
