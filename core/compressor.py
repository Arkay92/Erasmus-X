import re

class PromptCompressor:
    def __init__(self, enabled=True):
        self.enabled = enabled
        # Lossy Rules: (Regex Pattern -> Replacement)
        # Focus on stripping "human fluff" and shortening verbose instructions
        self.rules = [
            (r"(?i)\bplease be advised that\b", ""),
            (r"(?i)\bi would appreciate it if you could\b", ""),
            (r"(?i)\bit is important to note that\b", "Note:"),
            (r"(?i)\bin order to\b", "to"),
            (r"(?i)\bcould you please\b", ""),
            (r"(?i)\bthe current results indicate that\b", "Results:"),
            (r"(?i)\bwe have found that\b", "Found:"),
            (r"(?i)\bif you have any questions\b", ""),
            (r"(?i)\bas far as I am aware\b", ""),
            (r"(?i)\bthank you for your patience\b", ""),
            # Persona fluff
            (r"(?i)\bi am a helpful ai\b", ""),
            (r"(?i)\bi am here to assist you\b", ""),
        ]

    def compress(self, text, apply_macros=False):
        if not self.enabled or not text:
            return text

        # 1. Apply Lossy Rules (Lossy Pass)
        compressed = text
        for pattern, replacement in self.rules:
            compressed = re.sub(pattern, replacement, compressed)

        # 2. Macro Logic (Hierarchical Pass - simplified for 2B)
        # We look for recurring long names or domain terms if apply_macros is True
        if apply_macros:
            compressed = self._apply_macros(compressed)

        # 3. Clean up formatting artifacts
        compressed = re.sub(r'\s{2,}', ' ', compressed) # Collapse multiple spaces
        compressed = compressed.strip()
        
        return compressed

    def _apply_macros(self, text):
        """
        Implementation of Rab McMenemy's 'Macro' strategy.
        Identifies highly repeating phrases and defines them in a header.
        """
        # For the 2B model, we use a conservative macro strategy:
        # Only replace the Triplet Instruction if it appears multiple times
        # (Though in our current agent, it's usually just once in the system prompt)
        
        # Example of a predefined macro for output rules
        triplet_rule = "[FACT] subject | relation | object"
        if text.count(triplet_rule) > 1:
            header = f"§T={triplet_rule}"
            text = text.replace(triplet_rule, "@T")
            return f"{header}\n{text}"
        
        return text

    def get_savings(self, original, compressed):
        """Calculates token savings estimate (chars used as proxy)."""
        o_len = len(original)
        c_len = len(compressed)
        savings = o_len - c_len
        percent = (savings / o_len) * 100 if o_len > 0 else 0
        return savings, percent
