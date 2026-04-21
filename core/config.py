import os

# API Configuration
API_BASE_URL = "http://localhost:12345/v1"
API_KEY = "local"
MODEL_NAME = "local-model"

# Storage Configuration
BRAIN_STORAGE_PATH = "memories/agent_brain.pt"
LEGACY_JSON_MEMORY = "memories/hypervector_memory.json"
LEGACY_PT_MEMORY = "memories/hypervector_memory.pt"
LEGACY_KG_JSON = "memories/knowledge_graph.json"

# Hypervector Configuration
HV_DIMENSIONS = 10000
VECTOR_SEARCH_THRESHOLD = 0.15
TOP_K_RESULTS = 3

# Agent Configuration
MAX_HISTORY_LEN = 2
MAX_CONTEXT_HISTORY_CHARS = 4000 # Trigger for "Spin Down"
MAX_RETRIEVED_MEMORIES = 2      # How many past summaries to reload
MAX_TOKENS_GENERATION = 1024
TEMPERATURE = 0.1

# Semantic Cache Configuration
CACHE_THRESHOLD = 0.98

# Prompt Compression (McMenemy Strategy)
ENABLE_PROMPT_COMPRESSION = True
COMPRESSION_DEBUG = True  # Set to True to see char savings in console

# Phase 5: Resource Optimization & Sandbox
ENABLE_LOCAL_LLM = True
LOCAL_MODEL_TYPE = "gpt2" # "gpt2", "gpt2-medium"
SANDBOX_ENFORCED = True
SANDBOX_ROOT = "sandboxes"
SANDBOX_RETENTION_HOURS = 24 
