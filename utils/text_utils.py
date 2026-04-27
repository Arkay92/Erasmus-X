import math

def count_tokens(text):
    """Conservative proxy for BPE tokens (words * 1.6)."""
    if not text:
        return 0
    words = len(text.split())
    return math.ceil(words * 1.6)
