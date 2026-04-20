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
MAX_TOKENS_GENERATION = 1024
TEMPERATURE = 0.1

# Semantic Cache Configuration
CACHE_THRESHOLD = 0.98

# Prompt Compression (McMenemy Strategy)
ENABLE_PROMPT_COMPRESSION = True
COMPRESSION_DEBUG = True  # Set to True to see char savings in console
