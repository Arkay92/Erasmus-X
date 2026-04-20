import os

# Point to the new shards/core structure
_BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'shards', 'core')

def _load_prompt(filename, default_text=""):
    filepath = os.path.join(_BASE_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return default_text

# System prompt for the Neurosymbolic Agent
SYSTEM_PROMPT = _load_prompt("system_prompt.md", "You are a helpful AI.\nIf you write functional code, prefix the block with a tag: [FILE: filename.py].\nAt the end of your answer, output triplets:\n[FACT] subject | relation | object")

# Agnostic Query Brain prompts
ENTITY_PROMPT = _load_prompt("entity_prompt.md", "Identify the core subject or entity of this message. Be extremely concise (1-3 words). Text: ")
SKEPTIC_PROMPT = _load_prompt("skeptic_prompt.md", "Does this query require real-time data, current events, or information that changes frequently? Answer ONLY 'YES' or 'NO'. Text: ")

# Search/Discovery keywords (Not moved to MD as it's a simple list)
DISCOVERY_KEYWORDS = ['who', 'what', 'where', 'when', 'why', 'how', 'find', 'search', 'latest', 'news', 'update', 'status']

# Prompt templates
CONTEXT_PREVIOUS = "PREVIOUS KNOWLEDGE: "
CONTEXT_FACTS = "FACTS: "
CONTEXT_SOURCE_START = "--- SOURCE DATA ---\n"
CONTEXT_SOURCE_END = "\n--- END SOURCE ---"

# Meta-Question Generation for Seeding (Instructional for Stability)
META_GEN_PROMPT = _load_prompt("meta_gen_prompt.md")

# Autonomous Coding Loop Prompts
CODE_ERROR_PROMPT = _load_prompt("code_error_prompt.md")
CODE_REVIEW_PROMPT = _load_prompt("code_review_prompt.md")

# Project Planning Prompts
PROJECT_PLANNER_PROMPT = _load_prompt("project_planner_prompt.md")
