import torch
import torchhd
from torchhd import embeddings
import os
import shutil
import tempfile

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
        
        # HDC Intent Routing (Fast Reasoning Lane)
        self.intent_centers = None # Class centroids for SEARCH vs RECALL intent
        
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
            # Optimization: Auto-save removed; calling code must sync when ready.

    def add_convo_step(self, entry):
        """Logs a conversation/benchmark step and vectorizes it."""
        self.convo_chain.append(entry)
        # Vectorize the query and response for "meta-memory" retrieval
        query = entry.get('query', 'Unknown')
        output = entry.get('raw_output', entry.get('raw_response', 'No output'))
        log_text = f"Query: {query} | Response: {str(output)[:200]}"
        self.add_document(log_text)

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

    def _init_intents(self):
        """Pre-seeds the Brain with class centroids for SEARCH vs RECALL vs TOOL."""
        print("[*] Training high-speed intent routing...")
        # 1. Search Intent (Dynamic/Discovery/News)
        search_seeds = ["latest news", "current status", "update on", "what is happening", "latest results", "current price", "news about", "who is CURRENTLY"]
        search_v = torch.stack([self.encode(s) for s in search_seeds])
        search_centroid = torchhd.functional.multiset(search_v)
        
        # 2. Recall Intent (Static/Facts/Identity)
        recall_seeds = ["who is", "what is", "about the", "tell me about", "history of", "capital of", "define", "what do we know about"]
        recall_v = torch.stack([self.encode(r) for r in recall_seeds])
        recall_centroid = torchhd.functional.multiset(recall_v)

        # 3. Tool/Utility Intent (Deterministic Scripts)
        tool_seeds = ["find files", "list directory", "scan project", "search pattern", "grep", "dependency audit", "check versions", "list all files", "where is"]
        tool_v = torch.stack([self.encode(t) for t in tool_seeds])
        tool_centroid = torchhd.functional.multiset(tool_v)
        
        # 4. Project Intent (Complex/Multi-file Requests)
        project_seeds = ["design and implement", "multi-file application", "system architecture", "build a complete project", "create an app", "software system with sqlite", "complex application generator", "create a project"]
        project_v = torch.stack([self.encode(p) for p in project_seeds])
        project_centroid = torchhd.functional.multiset(project_v)
        
        self.intent_centers = torch.stack([search_centroid, recall_centroid, tool_centroid, project_centroid])
        self.save()

    def classify_intent(self, query):
        """
        High-speed HDC intent classification.
        Returns 'SEARCH', 'RECALL', or 'TOOL' and the confidence score.
        """
        if self.intent_centers is None:
            self._init_intents()
            
        q_v = self.encode(query)
        # Cosine similarity against the class centroids
        sims = torchhd.functional.cosine_similarity(q_v, self.intent_centers)
        
        score, idx = torch.max(sims, dim=0)
        labels = ["SEARCH", "RECALL", "TOOL", "PROJECT"]
        label = labels[idx.item()]
        return label, score.item()

    def refine_intent(self, label, example_text):
        """
        Dynamically updates a class centroid with a new example.
        This is the 'learning' part of the HDC neurosymbolic brain.
        """
        if self.intent_centers is None:
            self._init_intents()
            
        labels = ["SEARCH", "RECALL", "TOOL", "PROJECT"]
        if label not in labels:
            return
            
        idx = labels.index(label)
        new_v = self.encode(example_text)
        
        # Bundle the new vector into the existing centroid
        # This shifts the centroid towards the new example
        self.intent_centers[idx] = torchhd.functional.multiset(torch.stack([self.intent_centers[idx], new_v]))
        self.save()
        print(f"[*] Brain learned new pattern for {label} intent.")

    def search(self, query, threshold=0.10, top_k=3):
        if not self.documents or self.memory_tensor is None:
            return []
            
        query_hv = self.encode(query)
        # Calculate cosine similarity against all stored hypervectors
        similarities = torchhd.functional.cosine_similarity(query_hv, self.memory_tensor)
        
        # Optimization: Use topk for efficient O(N log K) retrieval instead of O(N log N) sorting
        k = min(top_k * 2, len(self.documents)) # Retrieve a bit more to filter by threshold
        scores, indices = torch.topk(similarities, k=k)
        
        results = []
        for i in range(len(indices)):
            score = scores[i].item()
            idx = indices[i].item()
            if score >= threshold:
                results.append((score, self.documents[idx]))
                if len(results) >= top_k:
                    break
        return results

    def search_by_hv(self, query_hv, threshold=0.10, top_k=3):
        """Internal search using a pre-computed hypervector."""
        if not self.documents or self.memory_tensor is None:
            return []
            
        similarities = torchhd.functional.cosine_similarity(query_hv, self.memory_tensor)
        k = min(top_k * 2, len(self.documents))
        scores, indices = torch.topk(similarities, k=k)
        
        results = []
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
        
        # 1. Create backup of current stable file
        if os.path.exists(self.filename):
            shutil.copy2(self.filename, self.filename + ".bak")

        data = {
            "documents": self.documents,
            "memory_tensor": self.memory_tensor,
            "graph_data": self.graph_data,
            "convo_chain": self.convo_chain,
            "prompt_cache": self.prompt_cache,
            "cache_tensor": self.cache_tensor,
            "intent_centers": self.intent_centers
        }
        
        # 2. Atomic Save: Write to temp file and rename (prevent corruption on crash)
        fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(self.filename))
        try:
            with os.fdopen(fd, 'wb') as f:
                torch.save(data, f)
            # Rename is atomic on Unix and most Windows scenarios
            shutil.move(temp_path, self.filename)
        except Exception as e:
            if os.path.exists(temp_path): os.remove(temp_path)
            print(f"[Memory Save Error] {e}")

    def load(self):
        # Migration check: handle change from hypervector_memory.pt to agent_brain.pt
        target_file = self.filename
        legacy_pt = "memories/hypervector_memory.pt"
        if not os.path.exists(target_file) and os.path.exists(legacy_pt):
            print(f"[*] Upgrading storage from {legacy_pt} to {target_file}...")
            target_file = legacy_pt

        if os.path.exists(target_file):
            try:
                self._load_from_path(target_file)
            except Exception as e:
                print(f"[Memory Load Error] {e}. Attempting recovery from backup.")
                backup = target_file + ".bak"
                if os.path.exists(backup):
                    try:
                        self._load_from_path(backup)
                        print("[+] Successfully recovered from backup.")
                    except Exception as be:
                        print(f"[Memory Load Error] Backup also failed: {be}")
        
        # Check if intent centers need expansion (e.g. after update)
        if self.intent_centers is not None and self.intent_centers.shape[0] < 4:
            print("[*] Upgrading intent centers to include PROJECT intent...")
            self._init_intents()

    def _load_from_path(self, path):
        """Internal helper to load torch data into memory."""
        data = torch.load(path, weights_only=False)
        self.documents = data.get("documents", [])
        self.memory_tensor = data.get("memory_tensor")
        self.graph_data = data.get("graph_data")
        self.convo_chain = data.get("convo_chain", [])
        self.prompt_cache = data.get("prompt_cache", {})
        self.cache_tensor = data.get("cache_tensor")
        self.intent_centers = data.get("intent_centers")

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
