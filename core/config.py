import os

# API Configuration
API_BASE_URL = "http://localhost:12345/v1"
API_KEY = "local"
MODEL_NAME = "local-model"

# Storage Configuration
BRAIN_STORAGE_PATH = "memories/agent_brain.pt"

# Hypervector Configuration
HV_DIMENSIONS = 10000
VECTOR_SEARCH_THRESHOLD = 0.15
TOP_K_RESULTS = 3

# Agent Configuration
MAX_HISTORY_LEN = 2
MAX_CONTEXT_HISTORY_CHARS = 2000 # Trigger for "Spin Down"
MAX_RETRIEVED_MEMORIES = 1      # Minimum viable reload
MAX_TOKENS_GENERATION = 1024
TEMPERATURE = 0.7
REQUEST_TIMEOUT = 300           # Safety timeout in seconds (Increased for slow hardware)
INITIAL_TURN_MAX_TOKENS = 512   # Startup budget for Step 1

# Semantic Cache Configuration
CACHE_THRESHOLD = 0.65

# Prompt Compression (McMenemy Strategy)
ENABLE_PROMPT_COMPRESSION = True
COMPRESSION_ENABLED = True
COMPRESSION_DEBUG = True  # Set to True to see char savings in console

# Phase 5 & 6: Resource Optimization & Sandbox
ENABLE_LOCAL_LLM = True
LOCAL_MODEL_TYPE = "gpt2" # "gpt2", "gpt2-medium"
SANDBOX_ENFORCED = True
SANDBOX_ROOT = "sandboxes"
SANDBOX_RETENTION_HOURS = 24 

# Phase 8: Selective Capability & Gating
SIMPLE_QUERY_LIMIT = 15
DYNAMIC_ONLY_KEYWORDS = ['latest', 'news', 'price', 'status', 'current', 'today', 'happening', 'update']
FORCE_DEEP_THRESHOLD = 0.25

# Phase 7: SLM Optimization (Fast/Deep Mode)
# NOTE: DO NOT mutate this global variable directly at runtime. Use a local state.
OPERATING_MODE = "FAST" # Default back to FAST for Phase 8 testing
STOP_SEQUENCES = ["\nYou:"]

# Fast Mode Budgets (Tokens - estimated via whitespace)
FAST_MODE_CONTEXT_TOKENS = 512
FAST_MODE_OUTPUT_TOKENS = 64

# Mid Mode Budgets (Reasoning fallback)
MID_MODE_CONTEXT_TOKENS = 1024
MID_MODE_OUTPUT_TOKENS = 256

# Deep Mode Budgets
DEEP_MODE_CONTEXT_TOKENS = 2048
DEEP_MODE_OUTPUT_TOKENS = 512

# Phase 9: Iterative Repair Guard
MAX_REPAIR_HISTORY_TOKENS = 600
CRITIC_REPORT_LIMIT = 500

# Phase 10: Autonomous Capability Synthesis
ENABLE_AUTONOMOUS_SYNTHESIS = True
SYNTHESIS_THRESHOLD = 0.8
ASSOCIATION_RECALL_THRESHOLD = 0.35
MAX_PROJECT_RETRIES = 8
MAX_CRITIC_CYCLES = 3

# Phase 11: Chain of Thought & Reinforcement Learning
ENABLE_REASONING_ENGINE = True
REASONING_LESSONS_STORAGE = "core/memory/reasoning_lessons.json"
MAX_REASONING_LESSONS_CONTEXT = 3
REASONING_EVALUATION_THRESHOLD = 80
