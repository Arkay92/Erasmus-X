# System prompt for the Neurosymbolic Agent
SYSTEM_PROMPT = """You are a helpful AI.
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
