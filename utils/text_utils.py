import math

def count_tokens(text):
    """Conservative proxy for BPE tokens (words * 1.6)."""
    if not text:
        return 0
    words = len(text.split())
    return math.ceil(words * 1.6)

def summarize_text_python(text, max_sentences=2):
    """Pure Python summarizer: extracts first N sentences as a budget-friendly proxy."""
    if not text:
        return ""
    sentences = text.replace('\n', ' ').split('. ')
    return ". ".join(sentences[:max_sentences]) + "."
