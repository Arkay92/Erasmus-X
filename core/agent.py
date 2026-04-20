import re
import subprocess
import os
from openai import OpenAI
from core import config, prompts
from core.compressor import PromptCompressor
from utils.brain_sync import sync_project_dir, sync_from_sqlite, sync_from_json

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
            
            # --- PHASE 0.5: MANUAL BRAIN SYNC TRIGGER ---
            # User can say "sync db <path>" or "sync json <path>" to ingest data
            sync_match = re.match(r'sync\s+(db|json|sqlite)\s+(.+)', user_input.strip(), re.IGNORECASE)
            if sync_match:
                ftype, fpath = sync_match.group(1).lower(), sync_match.group(2).strip()
                fpath = os.path.normpath(fpath)
                if ftype in ('db', 'sqlite'):
                    count = sync_from_sqlite(self.brain, self.kg, fpath)
                else:
                    count = sync_from_json(self.brain, self.kg, fpath)
                msg = f"[BrainSync] Ingested {count} records from {os.path.basename(fpath)} into agent memory."
                print(msg)
                return msg, msg

            # --- PHASE 0.6: PROJECT DETECTION ---
            is_project = self._is_project_request(user_input)
            project_dir = None
            
            if is_project:
                print("[*] Project Mode Detected: Entering planning phase...")
                project_dir, raw_response = self._project_planning_flow(user_input, messages)
            else:
                # 4. Add to Semantic Prompt Cache
                self.brain.add_to_cache(user_input, raw_response, clean_ans)
            
            # --- PHASE 6: AUTONOMOUS TEST-EDIT LOOP ---
            final_response, final_clean = self._autonomous_coding_loop(user_input, messages, raw_response, base_dir=project_dir)
            
            # --- PHASE 7: POST-BUILD DATA SYNC ---
            # After a project is built, auto-ingest any .db or .json data files
            if project_dir:
                root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
                full_project_path = os.path.join(root_dir, 'scratch', project_dir)
                synced = sync_project_dir(self.brain, self.kg, full_project_path)
                if synced > 0:
                    print(f"[BrainSync] Auto-synced {synced} records from project '{project_dir}' into agent memory.")
            
            return final_response, final_clean

        except Exception as e:
            return f"[Error during generation: {e}]", None

    def _autonomous_coding_loop(self, user_input, messages, raw_response, base_dir=None):
        """Iteratively tests and fixes code blocks."""
        attempts = 0
        max_attempts = 5
        current_response = raw_response
        
        while attempts < max_attempts:
            files = self._extract_and_save_files(current_response, base_dir=base_dir)
            if not files:
                return current_response, re.sub(r'\[FACT\].*', '', current_response).strip()

            print(f"[*] Autonomous Testing: Verifying {len(files)} files...")
            
            all_success = True
            test_results = []
            
            for f in files:
                success, output = self._run_test(f, base_dir=base_dir)
                test_results.append(f"File: {f} | Success: {success}\nOutput:\n{output}")
                if not success:
                    all_success = False
            
            result_summary = "\n\n".join(test_results)
            
            if all_success:
                print("[+] Autonomous Testing: All tests PASSED.")
                # Final pass to let the model review the output
                review_prompt = prompts.CODE_REVIEW_PROMPT.format(test_output=result_summary)
                messages.append({"role": "user", "content": review_prompt})
                
                response = self.client.chat.completions.create(
                    model=config.MODEL_NAME,
                    messages=messages,
                    temperature=config.TEMPERATURE,
                    max_tokens=config.MAX_TOKENS_GENERATION
                )
                final_response = response.choices[0].message.content
                return final_response, re.sub(r'\[FACT\].*', '', final_response).strip()
            
            # If we reached here, something failed
            attempts += 1
            print(f"[!] Autonomous Testing: Test FAILED (Attempt {attempts}/{max_attempts})")
            
            if attempts == 3:
                print("[*] Autonomous Search: Consulting the web for coding help...")
                search_query = f"how to fix python error in {user_input}: {result_summary[:200]}"
                web_help = self.searcher.search(search_query)
                error_content = prompts.CODE_ERROR_PROMPT.format(error_output=result_summary)
                if web_help:
                    error_content += f"\n\nSEARCH RESULTS HELP:\n{web_help[:500]}"
            else:
                error_content = prompts.CODE_ERROR_PROMPT.format(error_output=result_summary)
            
            messages.append({"role": "user", "content": error_content})
            
            print("Gemma is re-thinking (Self-Correction)...", flush=True)
            response = self.client.chat.completions.create(
                model=config.MODEL_NAME,
                messages=messages,
                temperature=config.TEMPERATURE,
                max_tokens=config.MAX_TOKENS_GENERATION
            )
            current_response = response.choices[0].message.content

        return current_response, re.sub(r'\[FACT\].*', '', current_response).strip()

    def _run_test(self, filename, base_dir=None):
        """Executes a saved Python script and returns (success, output).
        Non-Python files (PLAN.md, .json, .db, etc.) are skipped as passing.
        """
        # Only test Python files — other files are not executable
        if not filename.endswith('.py'):
            return True, f"[Skipped: {filename} is not a Python file]"

        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        if base_dir:
            filepath = os.path.join(root_dir, 'scratch', base_dir, filename)
        else:
            filepath = os.path.join(root_dir, 'scratch', filename)
        
        try:
            exec_cwd = os.path.dirname(filepath)
            run_res = subprocess.run(
                ["python", filepath], 
                capture_output=True, 
                text=True, 
                timeout=15,
                cwd=exec_cwd
            )
            output = run_res.stdout.strip() or run_res.stderr.strip()
            return (run_res.returncode == 0), output
        except subprocess.TimeoutExpired:
            return False, "Error: Execution timed out (15s limit)."
        except Exception as e:
            return False, f"System Error executing script: {str(e)}"

    def _extract_and_save_files(self, text, base_dir=None):
        """Finds [FILE: name] tags and saves code blocks to scratch/."""
        pattern = r"\[FILE:\s*(.+?)\]\s*[\n\s]*```[a-z]*\n(.+?)(?:\n?```|$)"
        matches = re.finditer(pattern, text, re.DOTALL)
        
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        if base_dir:
            scratch_dir = os.path.join(root_dir, 'scratch', base_dir)
        else:
            scratch_dir = os.path.join(root_dir, 'scratch')
            
        os.makedirs(scratch_dir, exist_ok=True)
        
        saved_files = []
        for match in matches:
            filename = match.group(1).strip()
            code = match.group(2)
            filepath = os.path.join(scratch_dir, filename)
            # Ensure parent directories exist within the project
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(code)
                print(f"[*] Autonomous Coding: Saved {filename} to {os.path.basename(scratch_dir)}/")
                saved_files.append(filename)
            except Exception as e:
                print(f"[!] Failed to save autonomous code {filename}: {e}")
        return saved_files

    def _is_project_request(self, text):
        """Detects if the request is for a complex project."""
        keywords = ['project', 'application', 'system', 'multiple files', 'app', 'complex software', 'sqlite', 'database']
        return any(k in text.lower() for k in keywords) and len(text.split()) > 5

    def _project_planning_flow(self, user_input, messages):
        """Runs the project planning phase."""
        # 1. Gather technical context
        print("[*] Project Planning: Researching architecture...")
        search_query = f"Modern Python architecture for {user_input}"
        web_help = self.searcher.search(search_query)
        
        # 2. Generate Plan
        print("[*] Project Planning: Generating PLAN.md...")
        planner_content = f"{prompts.PROJECT_PLANNER_PROMPT}\n\nUSER REQUEST: {user_input}"
        if web_help:
            planner_content += f"\n\nTECHNICAL REFERENCE:\n{web_help[:800]}"
            
        planner_messages = [
            {"role": "system", "content": prompts.SYSTEM_PROMPT},
            {"role": "user", "content": planner_content}
        ]
        
        response = self.client.chat.completions.create(
            model=config.MODEL_NAME,
            messages=planner_messages,
            temperature=config.TEMPERATURE,
            max_tokens=config.MAX_TOKENS_GENERATION
        )
        
        plan_raw = response.choices[0].message.content
        
        # 3. Create Project Directory
        import time
        project_name = re.sub(r'[^a-z0-9]', '_', user_input.lower())[:20]
        project_dir_name = f"project_{project_name}_{int(time.time())}"
        
        # 4. Save PLAN.md — two-stage approach:
        #    a) Try extracting a tagged [FILE: PLAN.md] block from the response
        #    b) Guarantee write: if nothing was extracted, write the raw plan directly
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        plan_dir = os.path.join(root_dir, 'scratch', project_dir_name)
        os.makedirs(plan_dir, exist_ok=True)

        extracted = self._extract_and_save_files(plan_raw, base_dir=project_dir_name)
        plan_md_path = os.path.join(plan_dir, 'PLAN.md')
        if 'PLAN.md' not in extracted:
            # Fallback: write the raw model response as PLAN.md
            with open(plan_md_path, 'w', encoding='utf-8') as f:
                f.write(plan_raw)
            print(f"[*] Project Planning: Plan saved to scratch/{project_dir_name}/PLAN.md (fallback write)")
        else:
            print(f"[*] Project Planning: Plan saved to scratch/{project_dir_name}/PLAN.md")

        # We return the project_dir and the plan as the 'initial response' for the coding loop
        # We also instruct the model to start building
        building_instruction = f"The plan is approved. Now implement the project files into the {project_dir_name} directory as defined in the plan."
        messages.append({"role": "assistant", "content": plan_raw})
        messages.append({"role": "user", "content": building_instruction})
        
        # Generate the first set of files
        response = self.client.chat.completions.create(
            model=config.MODEL_NAME,
            messages=messages,
            temperature=config.TEMPERATURE,
            max_tokens=config.MAX_TOKENS_GENERATION
        )
        
        return project_dir_name, response.choices[0].message.content

    def reset(self):
        """Clears the conversational history."""
        self.messages = []
        self.last_subject = None
        print("[*] Agent Brain history purged for fresh context.")
