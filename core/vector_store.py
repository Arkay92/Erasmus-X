import torch
import torchhd
from torchhd import embeddings
import os

class HypervectorDB:
    def __init__(self, filename="memories/agent_brain.pt", dim=10000):
        self.filename = filename
        self.dim = dim
        self.documents = []
        self.memory_tensor = None
        self.graph_data = None  # Storage for Knowledge Graph node-link data
        self.convo_chain = []   # Storage for benchmark/conversation logs
        
        # Semantic Cache (Query -> Response Data)
        self.prompt_cache = {}
        self.cache_tensor = None
        
        # Expanded ASCII character alphabet for robust encoding
        self.alphabet = "abcdefghijklmnopqrstuvwxyz0123456789 .,!?-()\":;'"
        self.char_to_idx = {c: i for i, c in enumerate(self.alphabet)}
        
        # Fix: Seed the random generation for consistency across loads
        torch.manual_seed(42)
        self.char_embeds = embeddings.Random(len(self.alphabet), self.dim)
        
        self.load()

    def encode(self, text):
        """
        Encodes text into a hypervector using 3-gram circular shifts and bindings.
        """
        text = text.lower()
        # Filter text to supported alphabet
        chars = [c for c in text if c in self.alphabet]
        if not chars:
            return torch.zeros(self.dim)
            
        indices = torch.tensor([self.char_to_idx[c] for c in chars])
        vectors = self.char_embeds(indices)
        
        # Handle short texts
        if len(vectors) < 3:
            return torchhd.functional.multiset(vectors) if len(vectors) > 0 else torch.zeros(self.dim)
            
        # N-gram encoding (N=3) - representing sequence structure
        return torchhd.functional.ngrams(vectors, n=3)

    def add_document(self, text):
        if not text or len(text.strip()) == 0:
            return
        if text not in self.documents:
            hv = self.encode(text)
            self.documents.append(text)
            if self.memory_tensor is None:
                self.memory_tensor = hv.unsqueeze(0)
            else:
                self.memory_tensor = torch.cat([self.memory_tensor, hv.unsqueeze(0)])
            self.save()

    def add_convo_step(self, entry):
        """Logs a conversation/benchmark step and vectorizes it."""
        self.convo_chain.append(entry)
        # Vectorize the query and response for "meta-memory" retrieval
        log_text = f"Query: {entry.get('query')} | Response: {entry.get('raw_output')[:200]}"
        self.add_document(log_text)
        self.save()

    def add_to_cache(self, query, raw_response, clean_ans):
        """Adds a response to the semantic cache."""
        query = query.strip().lower()
        if query not in self.prompt_cache:
            hv = self.encode(query)
            self.prompt_cache[query] = {
                "raw": raw_response,
                "clean": clean_ans
            }
            if self.cache_tensor is None:
                self.cache_tensor = hv.unsqueeze(0)
            else:
                self.cache_tensor = torch.cat([self.cache_tensor, hv.unsqueeze(0)])
            self.save()

    def search_cache(self, query, threshold=0.98):
        """Checks the cache for a highly similar query."""
        if not self.prompt_cache or self.cache_tensor is None:
            return None
            
        query_hv = self.encode(query)
        similarities = torchhd.functional.cosine_similarity(query_hv, self.cache_tensor)
        
        score, idx = torch.max(similarities, dim=0)
        if score.item() >= threshold:
            # Match found! Map back to the query string to get the data
            cached_queries = list(self.prompt_cache.keys())
            matched_query = cached_queries[idx.item()]
            return self.prompt_cache[matched_query]
        return None

    def search(self, query, threshold=0.10, top_k=3):
        if not self.documents or self.memory_tensor is None:
            return []
            
        query_hv = self.encode(query)
        # Calculate cosine similarity against all stored hypervectors
        similarities = torchhd.functional.cosine_similarity(query_hv, self.memory_tensor)
        
        results = []
        # Sort indices by highest score
        scores, indices = torch.sort(similarities, descending=True)
        
        for i in range(len(indices)):
            score = scores[i].item()
            idx = indices[i].item()
            if score >= threshold:
                results.append((score, self.documents[idx]))
                if len(results) >= top_k:
                    break
        return results

    def save(self):
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.filename), exist_ok=True)
        data = {
            "documents": self.documents,
            "memory_tensor": self.memory_tensor,
            "graph_data": self.graph_data,
            "convo_chain": self.convo_chain,
            "prompt_cache": self.prompt_cache,
            "cache_tensor": self.cache_tensor
        }
        torch.save(data, self.filename)

    def load(self):
        # Migration check: handle change from hypervector_memory.pt to agent_brain.pt
        target_file = self.filename
        legacy_pt = "memories/hypervector_memory.pt"
        if not os.path.exists(target_file) and os.path.exists(legacy_pt):
            print(f"[*] Upgrading storage from {legacy_pt} to {target_file}...")
            target_file = legacy_pt

        if os.path.exists(target_file):
            try:
                data = torch.load(target_file, weights_only=False)
                self.documents = data.get("documents", [])
                self.memory_tensor = data.get("memory_tensor")
                self.graph_data = data.get("graph_data")
                self.convo_chain = data.get("convo_chain", [])
                self.prompt_cache = data.get("prompt_cache", {})
                self.cache_tensor = data.get("cache_tensor")
            except Exception as e:
                print(f"[Memory Load Error] {e}. Attempting recovery.")

        # Specific migration for Knowledge Graph JSON
        kg_json = "memories/knowledge_graph.json"
        if not self.graph_data and os.path.exists(kg_json):
            print(f"[*] Migrating Knowledge Graph from {kg_json}...")
            try:
                import json
                with open(kg_json, 'r', encoding='utf-8') as f:
                    self.graph_data = json.load(f)
            except Exception as e:
                print(f"[Graph Migration Error] {e}")

        # Specific migration for Legacy Memory JSON
        memory_json = "memories/hypervector_memory.json"
        if not self.documents and os.path.exists(memory_json):
            print(f"[*] Migrating legacy memory from {memory_json}...")
            try:
                import json
                with open(memory_json, 'r', encoding='utf-8') as f:
                    old_docs = json.load(f)
                for doc in old_docs:
                    self.add_document(doc)
            except Exception as e:
                print(f"[Memory Migration Error] {e}")
