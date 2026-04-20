# System prompt for the Neurosymbolic Agent
SYSTEM_PROMPT = """You are a helpful AI.
If you write functional code, prefix the block with a tag: [FILE: filename.py].
At the end of your answer, output triplets:
[FACT] subject | relation | object"""

# Agnostic Query Brain prompts
ENTITY_PROMPT = "Identify the core subject or entity of this message. Be extremely concise (1-3 words). Text: "
SKEPTIC_PROMPT = "Does this query require real-time data, current events, or information that changes frequently? Answer ONLY 'YES' or 'NO'. Text: "

# Search/Discovery keywords
DISCOVERY_KEYWORDS = ['who', 'what', 'where', 'when', 'why', 'how', 'find', 'search', 'latest', 'news', 'update', 'status']

# Prompt templates
CONTEXT_PREVIOUS = "PREVIOUS KNOWLEDGE: "
CONTEXT_FACTS = "FACTS: "
CONTEXT_SOURCE_START = "--- SOURCE DATA ---\n"
CONTEXT_SOURCE_END = "\n--- END SOURCE ---"

# Meta-Question Generation for Seeding (Instructional for 7.5B Stability)
META_GEN_PROMPT = """Analyze the topic provided below and generate exactly 2 intelligent follow-up research questions.
Each question should explore the significance, application, or deeper implications of the topic.
Format your response accurately with Q1: and Q2: prefixes.

Topic: """

# Autonomous Coding Loop Prompts
CODE_ERROR_PROMPT = """[CRITICAL: CODE ERROR DETECTED]
Your previous code failed. Study the error below and output a COMPLETE FIXED version.

RULES (follow strictly):
1. Use a [FILE: filename.py] tag before EVERY code block.
2. Re-output ALL project files, not just the broken one.
3. Every import statement must be at the very top of the file.
4. Every function/class must be fully implemented — no `pass`, no `...`, no placeholder comments.
5. Do NOT import modules that are not in the Python standard library unless told to install them.
6. The script must run silently if no arguments are provided (no interactive input() calls).

OUTPUT/ERROR:
{error_output}
"""

CODE_REVIEW_PROMPT = """[TEST SUCCESSFUL]
Your code ran successfully. Review the output below and finalize your answer.

TEST OUTPUT:
{test_output}
"""

# Project Planning Prompts
PROJECT_PLANNER_PROMPT = """You are a software architect planning a Python project.

Step 1 — Output a PLAN.md using this exact tag:
[FILE: PLAN.md]
```markdown
# Project: <name>

## Goal
<one sentence>

## File Structure
- main.py  — <purpose>
- <other files>

## Architecture
<brief description>
```

Step 2 — After the plan, output EVERY Python file using [FILE: filename.py] tags.

PYTHON FILE RULES:
- Each file must be independently runnable (main.py runs with no arguments).
- All imports at the top of each file.
- No interactive input() calls in runnable paths.
- Use only Python standard library modules (os, sys, json, sqlite3, argparse, etc.).
- Every function must be fully implemented — no `pass`, no placeholders.
- main.py must call its functions and print output when run directly.
"""
