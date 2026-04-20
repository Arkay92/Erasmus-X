import re
from openai import OpenAI
from core import config, prompts
from core.compressor import PromptCompressor

class NeurosymbolicAgent:
    def __init__(self, brain, kg, searcher):
        """
        The orchestrator for the Neurosymbolic Agent Pipeline.
        Args:
            brain (HypervectorDB): The vector memory component.
            kg (KnowledgeGraph): The symbolic graph component.
            searcher (WebSearcher): The tool for real-time web retrieval.
        """
        self.brain = brain
        self.kg = kg
        self.searcher = searcher
        self.client = OpenAI(base_url=config.API_BASE_URL, api_key=config.API_KEY)
        self.compressor = PromptCompressor(enabled=config.ENABLE_PROMPT_COMPRESSION)
        self.messages = []
        self.last_subject = None

    def _resolve_context(self, text):
        """Agnostic entity resolution and staleness check."""
        try:
            # Step 1: Extract subject
            e_resp = self.client.chat.completions.create(
                model=config.MODEL_NAME,
                messages=[{"role": "user", "content": prompts.ENTITY_PROMPT + text}],
                max_tokens=15,
                temperature=0
            )
            entity = e_resp.choices[0].message.content.strip()
            
            # Step 2: Binary staleness check
            s_resp = self.client.chat.completions.create(
                model=config.MODEL_NAME,
                messages=[{"role": "user", "content": prompts.SKEPTIC_PROMPT + text}],
                max_tokens=5,
                temperature=0
            )
            is_dynamic = "YES" in s_resp.choices[0].message.content.upper()
            
            return entity, is_dynamic
        except:
            return text, False

    def chat(self, user_input):
        """Processes a user message through the full neurosymbolic pipeline."""
        
        # --- PHASE 0: SEMANTIC CACHE LOOKUP ---
        cache_hit = self.brain.search_cache(user_input, threshold=config.CACHE_THRESHOLD)
        if cache_hit:
            raw_response = cache_hit['raw'] + "\n[Semantic Cache Hit]"
            clean_ans = cache_hit['clean']
            
            # Sync to history for convo continuity
            if len(self.messages) > config.MAX_HISTORY_LEN:
                self.messages = self.messages[-config.MAX_HISTORY_LEN:]
            self.messages.append({"role": "assistant", "content": clean_ans})
            
            return raw_response, clean_ans

        # --- PHASE 1: ULTRA-FAST INTENT ROUTING (HDC) ---
        intent, confidence = self.brain.classify_intent(user_input)
        
        # Approximative context resolution (lossy but fast)
        # Search for follow-up pronouns
        pronouns = ['it', 'they', 'them', 'him', 'her', 'this', 'that']
        is_followup = len(user_input.split()) < 3 or any(p in user_input.lower() for p in pronouns)
        
        if is_followup and self.last_subject:
            current_subject = self.last_subject
            is_dynamic = (intent == "SEARCH") or (confidence < 0.35) # Err on the side of search for follow-ups
        else:
            # Fallback to Deep reasoning only if HDC is uncertain
            if confidence < 0.30:
                print("[*] Transitioning to Deep Lane for uncertainty resolution...")
                current_subject, is_dynamic = self._resolve_context(user_input)
            else:
                current_subject = user_input
                is_dynamic = (intent == "SEARCH")

        # Context expansion for actual search string
        search_query = user_input
        if self.last_subject and is_followup:
            search_query = f"{user_input} (Context: {self.last_subject})"
        
        if current_subject and len(current_subject) > 2:
            self.last_subject = current_subject
        
        # --- PHASE 2: RETRIEVAL ---
        # 1. Vector Search
        vector_results = self.brain.search(search_query, threshold=config.VECTOR_SEARCH_THRESHOLD)
        
        # 2. Graph Search
        graph_facts = []
        search_terms = {current_subject.lower(), user_input.lower()}
        if self.last_subject: 
            search_terms.add(self.last_subject.lower())
        
        for word in user_input.split():
            if len(word) > 3: 
                search_terms.add(word.lower())
        
        for term in search_terms:
            graph_facts.extend(self.kg.get_related_facts(term))
        
        # Build context blocks
        context_blocks = []
        max_score = 0
        if vector_results:
            max_score = vector_results[0][0]
            context_blocks.append(prompts.CONTEXT_PREVIOUS + " | ".join([doc[:150] for score, doc in vector_results]))
        if graph_facts:
            context_blocks.append(prompts.CONTEXT_FACTS + " | ".join(set(graph_facts)))
        
        # --- PHASE 3: AGNOSTIC SEARCH TRIGGER ---
        intent_to_discover = any(q in user_input.lower() for q in prompts.DISCOVERY_KEYWORDS) or '?' in user_input
        web_text = None
        
        if intent_to_discover:
            # Skeptical Skip: Only skip if NOT dynamic AND we have very high confidence memory.
            should_skip = (not is_dynamic) and (max_score > 0.75)
            
            if not should_skip:
                print(f"[*] Analyzing dynamic context for: {search_query}...")
                web_text = self.searcher.search(search_query)
                if web_text:
                    context_blocks.append(prompts.CONTEXT_SOURCE_START + web_text[:500] + prompts.CONTEXT_SOURCE_END)

        # --- PHASE 3.5: PROMPT COMPRESSION ---
        final_context_blocks = []
        for block in context_blocks:
            c_block = self.compressor.compress(block)
            final_context_blocks.append(c_block)
            
            if config.COMPRESSION_DEBUG:
                savings, pct = self.compressor.get_savings(block, c_block)
                if savings > 0:
                    print(f"[*] Compressed block: saved {savings} chars ({pct:.1f}%)")
        
        # --- PHASE 4: GENERATION ---
        # 1. Build User Content with limited context
        user_content = ""
        if final_context_blocks:
            context_text = "\n".join(final_context_blocks)
            # Extreme context budget for 2048-token stability
            if len(context_text) > 400:
                context_text = context_text[:400] + "... [Context Pruned]"
            user_content += context_text + "\n\n"
        user_content += f"USER QUESTION: {user_input}"

        # 2. Reconstruct messages list with System Role first
        # Format: [System, {History}, CurrentUser]
        messages = [{"role": "system", "content": prompts.SYSTEM_PROMPT}]
        
        # Keep history extremely tight (1 turn for benchmark sanity)
        history = []
        if len(self.messages) > 1:
            history = self.messages[-2:] # Keep last turn (User + Assistant)
        
        messages.extend(history)
        messages.append({"role": "user", "content": user_content})
        
        print("Gemma is thinking...", flush=True)
        
        try:
            response = self.client.chat.completions.create(
                model=config.MODEL_NAME,
                messages=messages,
                stream=False,
                temperature=config.TEMPERATURE,
                max_tokens=config.MAX_TOKENS_GENERATION
            )
            
            raw_response = response.choices[0].message.content
            
            # --- PHASE 5: KNOWLEDGE SYNC ---
            # 1. Update Graph
            self.kg.extract_from_llm_response(raw_response)
            
            # 2. Cleanup response for chat history
            # Standard conversational history ONLY (User/Assistant)
            clean_ans = re.sub(r'\[FACT\].*', '', raw_response).strip()
            self.messages.append({"role": "user", "content": user_input})
            self.messages.append({"role": "assistant", "content": clean_ans})
            
            if len(self.messages) > 10: # Long-term safety cap
                self.messages = self.messages[-10:]
            
            # 3. Vectorize conclusion for long-term memory
            self.brain.add_document(f"Context: {user_input}. Summary: {clean_ans}")
            if web_text:
                self.brain.add_document(f"Internet record: {web_text[:400]}")
            
            # 4. Add to Semantic Prompt Cache
            self.brain.add_to_cache(user_input, raw_response, clean_ans)
            
            # 5. Extract and Save Files to Scratch
            self._extract_and_save_files(raw_response)
            
            return raw_response, clean_ans

        except Exception as e:
            return f"[Error during generation: {e}]", None

    def _extract_and_save_files(self, text):
        """Finds [FILE: name] tags and saves code blocks to scratch/."""
        import os
        pattern = r"\[FILE:\s*(.+?)\]\s*[\n\s]*```[a-z]*\n(.+?)(?:\n?```|$)"
        matches = re.finditer(pattern, text, re.DOTALL)
        
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        scratch_dir = os.path.join(root_dir, 'scratch')
        os.makedirs(scratch_dir, exist_ok=True)
        
        for match in matches:
            filename = match.group(1).strip()
            code = match.group(2)
            filepath = os.path.join(scratch_dir, filename)
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(code)
                print(f"\n[*] Autonomous Coding: Saved {filename} to scratch/")
            except Exception as e:
                print(f"\n[!] Failed to save autonomous code: {e}")

    def reset(self):
        """Clears the conversational history."""
        self.messages = []
        self.last_subject = None
        print("[*] Agent Brain history purged for fresh context.")
