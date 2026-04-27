import re
from core import prompts

class PromptDistiller:
    def __init__(self, local_llm):
        self.local_llm = local_llm

    def distill_task_instructions(self, user_input, meta):
        """
        Uses Local SLM (Erasmus) to generate task-specific constraints 
        to 'tune' the main LLM's behavior without weight updates.
        """
        if not self.local_llm:
            return ""

        # Speculative Analysis Prompt
        analysis_prompt = (
            f"Analyze the following task and generate 3-5 specific, high-fidelity engineering constraints "
            f"for a senior developer. Focus on {meta.get('intent', 'general coding')}.\n"
            f"TASK: {user_input}\n"
            f"CONSTRAINTS:"
        )
        
        raw_distillation = self.local_llm.generate(analysis_prompt, max_new_tokens=100, temperature=0.2)
        
        if not raw_distillation:
            return ""

        distilled_section = f"\n\n[SPECULATIVE CONSTRAINTS (Tuned by Erasmus X)]\n{raw_distillation}\n"
        return distilled_section
