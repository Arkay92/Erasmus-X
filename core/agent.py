import re
from openai import OpenAI
from core import config, prompts

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

        # --- PHASE 1: AGNOSTIC QUERY BRAIN ---
        current_subject, is_dynamic = self._resolve_context(user_input)
        
        # Context expansion for follow-up queries
        search_query = user_input
        pronouns = ['it', 'they', 'them', 'him', 'her', 'this', 'that']
        is_followup = len(current_subject.split()) < 2 or any(p in user_input.lower() for p in pronouns)
        
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

        # --- PHASE 4: GENERATION ---
        current_prompt = prompts.SYSTEM_PROMPT + "\n\n"
        if context_blocks:
            current_prompt += "\n".join(context_blocks) + "\n\n"
        current_prompt += f"USER QUESTION: {user_input}"

        # Keep history tight
        if len(self.messages) > config.MAX_HISTORY_LEN:
            self.messages = self.messages[-config.MAX_HISTORY_LEN:]

        self.messages.append({"role": "user", "content": current_prompt})
        
        print("Gemma is thinking...", end="\r", flush=True)
        
        try:
            response = self.client.chat.completions.create(
                model=config.MODEL_NAME,
                messages=self.messages,
                stream=False,
                temperature=config.TEMPERATURE,
                max_tokens=config.MAX_TOKENS_GENERATION
            )
            
            raw_response = response.choices[0].message.content
            
            # --- PHASE 5: KNOWLEDGE SYNC ---
            # 1. Update Graph
            self.kg.extract_from_llm_response(raw_response)
            
            # 2. Cleanup response for chat history
            clean_ans = re.sub(r'\[FACT\].*', '', raw_response).strip()
            self.messages[-1] = {"role": "user", "content": user_input}
            self.messages.append({"role": "assistant", "content": clean_ans})
            
            # 3. Vectorize conclusion for long-term memory
            self.brain.add_document(f"Context: {user_input}. Summary: {clean_ans}")
            if web_text:
                self.brain.add_document(f"Internet record: {web_text[:400]}")
            
            # 4. Add to Semantic Prompt Cache
            self.brain.add_to_cache(user_input, raw_response, clean_ans)
            
            return raw_response, clean_ans

        except Exception as e:
            return f"[Error during generation: {e}]", None
