"""
Enhanced Local LLM with support for better models than GPT-2.
Supports Mistral, Llama2, and other optimized models for better reasoning and generation.
"""
import os
import json
import urllib.error
import urllib.request

from core import config

os.makedirs(config.MODEL_CACHE_DIR, exist_ok=True)
os.environ.setdefault("HF_HOME", config.MODEL_CACHE_DIR)
os.environ.setdefault("HUGGINGFACE_HUB_CACHE", config.MODEL_CACHE_DIR)

import torch

class LocalLLM:
    """Manages a local LLM for fast routing, reasoning, and low-complexity tasks."""
    
    _instance = None
    SUPPORTED_MODELS = {
        "gpt2": "gpt2",
        "gpt2-medium": "gpt2-medium",
        "mistral": "mistralai/Mistral-7B-v0.1",
        "mistral-instruct": "mistralai/Mistral-7B-Instruct-v0.1",
        "llama2": "meta-llama/Llama-2-7b-hf",
        "llama2-chat": "meta-llama/Llama-2-7b-chat-hf",
        "tinyllama": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",  # Fast, lightweight
        "phi": "microsoft/phi-1.5",  # Efficient, good performance
    }
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(LocalLLM, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_name="phi", device=None, use_quantization=True):
        server_signature = (
            bool(config.USE_LOCAL_LLM_SERVER),
            config.LOCAL_LLM_SERVER_TYPE,
            self._server_base_url(),
        )
        if self._initialized and self.model_name == model_name and getattr(self, "server_signature", None) == server_signature:
            return
            
        self.model_name = model_name
        self.use_quantization = use_quantization
        self.device = device if device is not None else (0 if torch.cuda.is_available() else -1)
        self.server_signature = server_signature
        self.generator = None

        if config.USE_LOCAL_LLM_SERVER:
            self.server_type = config.LOCAL_LLM_SERVER_TYPE
            self.server_base_url = self._server_base_url()
            self._initialized = True
            print(f"[*] Local LLM server mode enabled ({self.server_type}) at {self.server_base_url}")
            return
        
        print(f"[*] Initializing Local LLM ({model_name})...")
        print(f"[*] Using device: {'CUDA' if self.device == 0 else 'CPU'}")
        
        try:
            from transformers import pipeline
            # Resolve model name
            model_id = self.SUPPORTED_MODELS.get(model_name, model_name)
            
            # For large models, use pipeline with optimizations
            if model_name in ["mistral", "mistral-instruct", "llama2", "llama2-chat"]:
                try:
                    # Try with 4-bit quantization for memory efficiency
                    if self.use_quantization:
                        print("[*] Attempting to load with 4-bit quantization...")
                        from transformers import BitsAndBytesConfig
                        
                        bnb_config = BitsAndBytesConfig(
                            load_in_4bit=True,
                            bnb_4bit_quant_type="nf4",
                            bnb_4bit_compute_dtype=torch.float16
                        )
                        
                        self.generator = pipeline(
                            "text-generation",
                            model=model_id,
                            model_kwargs={"cache_dir": config.MODEL_CACHE_DIR, "quantization_config": bnb_config},
                            device=self.device,
                            torch_dtype=torch.float16,
                        )
                    else:
                        self.generator = pipeline(
                            "text-generation",
                            model=model_id,
                            model_kwargs={"cache_dir": config.MODEL_CACHE_DIR},
                            device=self.device,
                            torch_dtype=torch.float16,
                        )
                except Exception as e:
                    print(f"[!] Quantization failed: {e}. Loading without quantization...")
                    self.generator = pipeline(
                        "text-generation",
                        model=model_id,
                        model_kwargs={"cache_dir": config.MODEL_CACHE_DIR},
                        device=self.device,
                    )
            else:
                # For smaller models like GPT2, TinyLlama
                self.generator = pipeline(
                    "text-generation",
                    model=model_id,
                    model_kwargs={"cache_dir": config.MODEL_CACHE_DIR},
                    device=self.device,
                )
            
            self._initialized = True
            print(f"[+] Local LLM '{model_name}' ready on {'CUDA' if self.device == 0 else 'CPU'}.")
            
        except Exception as e:
            print(f"[!] Failed to load Local LLM: {e}")
            print(f"[*] Falling back to GPT-2 as emergency fallback...")
            try:
                from transformers import pipeline
                self.generator = pipeline(
                    "text-generation",
                    model=self.SUPPORTED_MODELS["gpt2"],
                    model_kwargs={"cache_dir": config.MODEL_CACHE_DIR},
                    device=self.device,
                    pad_token_id=50256
                )
                self._initialized = True
            except Exception as e2:
                print(f"[!] Emergency fallback also failed: {e2}")
                self.generator = None
                self._initialized = True

    def _server_base_url(self):
        if config.LOCAL_LLM_SERVER_API_BASE_URL:
            return config.LOCAL_LLM_SERVER_API_BASE_URL.rstrip("/")
        if config.LOCAL_LLM_SERVER_TYPE == "ollama":
            return config.OLLAMA_API_BASE_URL.rstrip("/")
        return config.LMSTUDIO_API_BASE_URL.rstrip("/")

    def generate(self, prompt, max_new_tokens=128, temperature=0.7, stop_sequences=None, do_sample=True, stop=None):
        """
        Generates completion for a prompt.
        
        Args:
            prompt: Input text to complete
            max_new_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0 = deterministic, 1.0 = creative)
            stop_sequences: List of strings that stop generation
            stop: Backward-compatible alias for stop_sequences
            do_sample: Whether to use sampling (vs greedy)
        
        Returns: Generated text (without prompt prefix)
        """
        if config.USE_LOCAL_LLM_SERVER:
            return self._generate_from_server(prompt, max_new_tokens=max_new_tokens, temperature=temperature, stop_sequences=stop_sequences, stop=stop)

        if not self.generator:
            return None
            
        try:
            results = self.generator(
                prompt,
                max_new_tokens=max_new_tokens,
                num_return_sequences=1,
                temperature=temperature,
                do_sample=do_sample,
                truncation=True
            )
            
            full_text = results[0]['generated_text']
            
            # Remove prompt from output
            output = full_text
            if full_text.startswith(prompt):
                output = full_text[len(prompt):].strip()
            
            if stop and not stop_sequences:
                stop_sequences = stop

            # Apply stop sequences
            if stop_sequences:
                for stop in stop_sequences:
                    if stop in output:
                        output = output.split(stop)[0]
            
            return output.strip()
        except Exception as e:
            print(f"[!] Generation error: {e}")
            return None

    def _generate_from_server(self, prompt, max_new_tokens=128, temperature=0.7, stop_sequences=None, stop=None):
        if stop and not stop_sequences:
            stop_sequences = stop
        try:
            if self.server_type == "ollama":
                return self._generate_from_ollama(prompt, max_new_tokens, temperature, stop_sequences)
            return self._generate_from_openai_compatible(prompt, max_new_tokens, temperature, stop_sequences)
        except Exception as exc:
            print(f"[!] Local LLM server generation error: {exc}")
            return None

    def _generate_from_openai_compatible(self, prompt, max_new_tokens, temperature, stop_sequences):
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_new_tokens,
            "temperature": temperature,
        }
        if stop_sequences:
            payload["stop"] = stop_sequences
        data = self._post_json(
            f"{self.server_base_url}/chat/completions",
            payload,
            headers={"Authorization": f"Bearer {config.LOCAL_LLM_SERVER_API_KEY}"},
        )
        return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip() or None

    def _generate_from_ollama(self, prompt, max_new_tokens, temperature, stop_sequences):
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_new_tokens,
            },
        }
        if stop_sequences:
            payload["options"]["stop"] = stop_sequences
        data = self._post_json(f"{self.server_base_url}/api/generate", payload)
        return data.get("response", "").strip() or None

    def _post_json(self, url, payload, headers=None):
        request_headers = {"content-type": "application/json"}
        if headers:
            request_headers.update(headers)
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=request_headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=config.REQUEST_TIMEOUT) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code}: {body}") from exc

    def fast_intent_classify(self, text):
        """Speculative intent classification for routing."""
        prompt = f"Classify intent (SEARCH, CODE, CHAT, MATH):\n{text[:100]}\nIntent: "
        res = self.generate(prompt, max_new_tokens=5, temperature=0)
        if not res:
            return "CHAT"
        res = res.upper()
        if any(w in res for w in ["SEARCH", "FIND", "LOOK"]):
            return "SEARCH"
        if any(w in res for w in ["CODE", "WRITE", "BUILD", "CREATE"]):
            return "CODE"
        if any(w in res for w in ["MATH", "CALCULATE", "COMPUTE"]):
            return "MATH"
        return "CHAT"

    def classify_complexity(self, text):
        """Determine if task is simple or complex."""
        words = text.split()
        has_code = "```" in text
        has_arch_terms = any(term in text.lower() for term in 
                            ["architecture", "design", "system", "framework", "pattern"])
        
        if len(words) < 15 and not has_code and not has_arch_terms:
            return "LOW"
        return "HIGH"

    def chain_of_thought(self, prompt, num_steps=3):
        """
        Generate chain-of-thought reasoning.
        
        Args:
            prompt: The task/question
            num_steps: Number of reasoning steps to generate
        
        Returns: List of reasoning steps
        """
        cot_prompt = f"""Think step by step:
Question: {prompt}

Step 1: """
        
        steps = []
        for i in range(num_steps):
            result = self.generate(
                cot_prompt,
                max_new_tokens=100,
                temperature=0.3,
                do_sample=True
            )
            if result:
                step_text = f"Step {i+1}: {result}"
                steps.append(step_text)
                cot_prompt += result + f"\n\nStep {i+2}: "
        
        return steps

    def summarize(self, text, max_length=100):
        """Generate a brief summary of text."""
        prompt = f"Summarize this concisely in {max_length} words:\n{text[:500]}\n\nSummary: "
        return self.generate(prompt, max_new_tokens=50, temperature=0.1)

    def extract_key_points(self, text):
        """Extract 3-5 key points from text."""
        prompt = f"Extract 3-5 key points from this:\n{text[:500]}\n\nKey Points:\n"
        result = self.generate(prompt, max_new_tokens=150, temperature=0.1)
        if result:
            return [line.strip() for line in result.split('\n') if line.strip() and not line.startswith('Key')]
        return []
