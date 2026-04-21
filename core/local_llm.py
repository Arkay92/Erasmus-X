import torch
from transformers import pipeline, set_seed

class LocalLLM:
    """Manages a local GPT-2 model for low-complexity routing and pre-review."""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(LocalLLM, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_name="gpt2", device=None):
        if self._initialized:
            return
            
        print(f"[*] Initializing Local LLM ({model_name})...")
        if device is None:
            self.device = 0 if torch.cuda.is_available() else -1
        else:
            self.device = device
            
        try:
            self.generator = pipeline(
                "text-generation", 
                model=model_name, 
                device=self.device,
                pad_token_id=50256 # Default for GPT-2
            )
            self._initialized = True
            print(f"[+] Local LLM ready on {'GPU' if self.device == 0 else 'CPU'}.")
        except Exception as e:
            print(f"[!] Failed to load Local LLM: {e}")
            self.generator = None

    def generate(self, prompt, max_new_tokens=20, temperature=0.1):
        """Generates a completion for simple tasks."""
        if not self.generator:
            return None
            
        try:
            # Conservative generation for speed
            results = self.generator(
                prompt, 
                max_new_tokens=max_new_tokens, 
                num_return_sequences=1,
                temperature=temperature,
                do_sample=True if temperature > 0 else False,
                truncation=True
            )
            # Extract only the newly generated text
            full_text = results[0]['generated_text']
            # Small heuristic to strip prompt from output
            if full_text.startswith(prompt):
                return full_text[len(prompt):].strip()
            return full_text.strip()
        except Exception as e:
            print(f"[!] Local LLM generation error: {e}")
            return None

    def classify_complexity(self, text):
        """Pre-review logic to decide if a task is 'simple'."""
        # This is a meta-heuristic:
        # 1. Short text (< 20 words)
        # 2. No code blocks
        # 3. No complex architectural terms
        words = text.split()
        if len(words) < 20 and "```" not in text:
            return "LOW"
        return "HIGH"
