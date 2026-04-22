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

# System prompts for the Neurosymbolic Agent modes
SYSTEM_PROMPT = _load_prompt("system_prompt.md", "You are a helpful AI.\nIf you write functional code, prefix the block with a tag: [FILE: filename.py].\nAt the end of your answer, output triplets:\n[FACT] subject | relation | object")
FAST_SYSTEM_PROMPT = _load_prompt("fast_system_prompt.md", "Answer briefly in 2–4 sentences. No formatting. No files.")
MID_SYSTEM_PROMPT = _load_prompt("mid_system_prompt.md", "Provide a structured answer with facts extracted at the end.")

# Agnostic Query Brain prompts
ENTITY_PROMPT = _load_prompt("entity_prompt.md", "Identify the core subject or entity of this message. Be extremely concise (1-3 words). Text: ")
SKEPTIC_PROMPT = _load_prompt("skeptic_prompt.md", "Does this query require real-time data, current events, or information that changes frequently? Answer ONLY 'YES' or 'NO'. Text: ")

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
EXECUTION_POLICY_CODE = """[CONSTRAINT: EXECUTION POLICY]
You MUST output the full runnable source code for all requested functionality.
Requirements:
1. Wrap each file in a [FILE: filename] tag and a code block.
2. NO conversational prose. NO summaries. NO apologies.
3. Only the code is allowed. If you explain the code, you HAVE FAILED THE TASK.
4. DEPENDENCY RULE: Do not invent or create new 'utility' or 'core' files. Stick to standard libraries or files already established in the plan.
5. NUMERICAL RULE: For temperature conversions, Fahrenheit to Celsius must use (F-32)/1.8. Never use 1.7 or other approximations.
"""

# Grounded Summary Template
GROUNDED_SUMMARY_PROMPT = """[GROUNDED STATE SUMMARY]
Our conversation history is being reset. Based on the following retrieved memories and our current history, provide a COHERENT NARRATIVE SYNTHESIS of what has happened.
Focus on:
1. What was the user's core intent?
2. What critical facts were established?
3. What is the current progress of the active task (e.g., Planet Explorer Project, Higgs calculation)?
4. What specifically needs to happen next?

DO NOT list metadata. DO NOT output triplets here. Be the bridge between this session and the next.

RETRIEVED CONTEXT:
{retrieved_context}

CURRENT HISTORY:
{history_context}
"""

# Final Project Summary Report Prompt
PROJECT_REPORT_PROMPT = """[PROJECT REPORT GENERATOR]
Based on the following project plan and the list of files actually generated, create a professional summary.
Include:
1. **Description**: What the project does.
2. **Entrypoint**: Which file to run first.
3. **Run Instructions**: How to execute the project.
4. **Unresolved Issues**: Anything missing or failed during construction.

PLAN:
{plan_text}

GENERATED FILES:
{files_list}

TEST RESULTS:
{test_results}
"""
