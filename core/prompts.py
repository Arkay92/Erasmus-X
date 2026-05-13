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

# --- CORE PROMPT MANAGEMENT ---
# All significant prompts are stored as external .md files in shards/core/
# To add a new prompt:
# 1. Create a markdown file in shards/core/
# 2. Add a variable here using _load_prompt("filename.md")
# This ensures prompts remain modular and can be edited without touching Python code.

# System prompts for the Neurosymbolic Agent modes
SYSTEM_PROMPT = _load_prompt("system_prompt.md")
FAST_SYSTEM_PROMPT = _load_prompt("fast_system_prompt.md")
MID_SYSTEM_PROMPT = _load_prompt("mid_system_prompt.md")
DISPATCHER_PROMPT = _load_prompt("dispatcher_system_prompt.md")
WORKING_NOTES_MODE = _load_prompt("working_notes_mode.md")

# Agnostic Query Brain prompts
ENTITY_PROMPT = _load_prompt("entity_prompt.md")
SKEPTIC_PROMPT = _load_prompt("skeptic_prompt.md")

# Search/Discovery keywords (Not moved to MD as it's a simple list)
DISCOVERY_KEYWORDS = ['who', 'what', 'where', 'when', 'why', 'how', 'find', 'search', 'latest', 'news', 'update', 'status']

# Prompt templates
CONTEXT_PREVIOUS = "PREVIOUS KNOWLEDGE: "
CONTEXT_FACTS = "FACTS: "
CONTEXT_SOURCE_START = "--- SOURCE DATA (Trustworthy) ---\n"
CONTEXT_SOURCE_END = "\n--- END SOURCE ---"
CONTEXT_LESSONS = "--- LESSONS FROM PREVIOUS ATTEMPTS (Memory) ---\n"

# Meta-Question Generation for Seeding (Instructional for Stability)
META_GEN_PROMPT = _load_prompt("meta_gen_prompt.md")

# Autonomous Coding Loop Prompts
CODE_ERROR_PROMPT = _load_prompt("code_error_prompt.md")
CODE_REVIEW_PROMPT = _load_prompt("code_review_prompt.md")

# Project Planning Prompts
PROJECT_PLANNER_PROMPT = _load_prompt("project_planner_prompt.md")

# Execution Policies (Elite V4)
EXECUTION_POLICY_CODE = _load_prompt("execution_policy_code.md")

# Grounded Summary Template
GROUNDED_SUMMARY_PROMPT = _load_prompt("grounded_summary_prompt.md")

# Final Project Summary Report Prompt
PROJECT_REPORT_PROMPT = _load_prompt("project_report_prompt.md")

# Autonomous Capability Synthesis
AUTONOMOUS_SYNTHESIS_PROMPT = _load_prompt("autonomous_synthesis_prompt.md")
