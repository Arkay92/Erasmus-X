import re
import subprocess
import os
import sys
from openai import OpenAI
from core import config, prompts
from core.compressor import PromptCompressor
from core.sandbox import SandboxManager
from core.local_llm import LocalLLM
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
        self.sandbox = SandboxManager(root_dir=os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')), config.SANDBOX_ROOT))
        
        self.local_llm = None
        if config.ENABLE_LOCAL_LLM:
            self.local_llm = LocalLLM(model_name=config.LOCAL_MODEL_TYPE)
            
        self.messages = []
        self.last_subject = None
        self._persona_cache = {}
        self._pre_cache_shards()

    def _pre_cache_shards(self):
        """Warm up the persona cache for high-speed routing."""
        shards = self._load_shards_from_disk()
        for s in shards:
            self._persona_cache[s['name']] = s
        print(f"[*] Agent initialized with {len(self._persona_cache)} persona shards cached.")

    def _resolve_context(self, text):
        """Agnostic entity resolution and staleness check (optimized)."""
        # Pre-review routing
        if self.local_llm and self.local_llm.classify_complexity(text) == "LOW":
            print("[*] Performance Optimization: Using Local LLM for context resolution.")
            entity = self.local_llm.generate(prompts.ENTITY_PROMPT + text, max_new_tokens=15, temperature=0)
            if entity:
                return entity, False # GPT-2 assumed static for safety

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

        # --- PHASE 0.5: CONTEXT STABILITY CHECK ---
        # "Spin Down" if we are hitting context limits
        if self._check_context_stability() > config.MAX_CONTEXT_HISTORY_CHARS:
            self._perform_spin_down(current_task=user_input)

        # --- PHASE 1: ULTRA-FAST INTENT ROUTING (HDC) ---
        intent, confidence = self.brain.classify_intent(user_input)
        
        # --- PHASE 1.5: SHORT-CIRCUIT TOOLING ---
        # If the intent is TOOL and confidence is high, or if it's an explicit command
        is_command = user_input.startswith('/')
        if (intent == "TOOL" and confidence > 0.40) or is_command:
            tool_res = self._try_tool_short_circuit(user_input)
            if tool_res:
                return tool_res + "\n[Short-Circuit Tool Success]", tool_res

        # Approximative context resolution (lossy but fast)
        # Search for follow-up pronouns
        pronouns = ['it', 'they', 'them', 'him', 'her', 'this', 'that']
        # Avoid substring matching; ensure exact token boundary check
        is_followup = len(user_input.split()) < 3 or any(re.search(rf'\b{p}\b', user_input.lower()) for p in pronouns)
        
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
        # 1. Vector Search (General)
        vector_results = self.brain.search(search_query, threshold=config.VECTOR_SEARCH_THRESHOLD)
        
        # 2. Session Continuity Search (Spin-Up)
        # Specifically look for recent state summaries if we don't have enough history
        session_mems = []
        if len(self.messages) < 2:
            session_mems = self.brain.search("[SESSION_STATE]", threshold=0.05, top_k=config.MAX_RETRIEVED_MEMORIES)
        
        # 3. Graph Search
        graph_facts = []
        search_terms = {current_subject.lower(), user_input.lower()}
        if self.last_subject: 
            search_terms.add(self.last_subject.lower())
        
        for word in user_input.split():
            if len(word) > 3: 
                search_terms.add(word.lower())
        
        for term in search_terms:
            graph_facts.extend(self.kg.get_related_facts(term))
        
        # Neurosymbolic Bridge: Semantic Search for Concept-Based Facts
        # If we have a query HV, find nearest concepts in the KG
        query_hv = self.brain.encode(user_input)
        graph_facts.extend(self.kg.get_related_facts_semantic(query_hv, self.brain, threshold=0.15))
        
        # Build context blocks
        context_blocks = []
        max_score = vector_results[0][0] if vector_results else 0.0
        
        # Inject Session Continuity (Spin-Up)
        if session_mems:
             session_text = "\n".join([m[1] for m in session_mems])
             context_blocks.append("--- PREVIOUS SESSION SUMMARY ---\n" + session_text[:300])

        if vector_results:
            mem_text = " | ".join([doc[:150] for score, doc in vector_results])
            context_blocks.append(prompts.CONTEXT_PREVIOUS + mem_text[:300])
            
        if graph_facts:
            facts_text = " | ".join(set(graph_facts))
            context_blocks.append(prompts.CONTEXT_FACTS + facts_text[:300])
        
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
                    context_blocks.append(prompts.CONTEXT_SOURCE_START + web_text[:400] + prompts.CONTEXT_SOURCE_END)

        # --- PHASE 3.5: STRUCTURED CONTEXT BUILDING ---
        # Quotas for a hard 1000-char budget (including labels)
        quotas = {
            'memory': 320,
            'graph': 320,
            'web': 360
        }
        
        final_context_blocks = []
        
        # 1. Session & Vector Memory
        mem_block = ""
        if session_mems:
             mem_block += "--- PREVIOUS SESSION SUMMARY ---\n" + "\n".join([m[1] for m in session_mems]) + "\n"
        if vector_results:
            mem_block += prompts.CONTEXT_PREVIOUS + " | ".join([doc[:150] for score, doc in vector_results])
        
        if mem_block:
            final_context_blocks.append(self.compressor.compress(mem_block[:quotas['memory']]))

        # 2. Graph Facts
        if graph_facts:
            facts_block = prompts.CONTEXT_FACTS + " | ".join(set(graph_facts))
            final_context_blocks.append(self.compressor.compress(facts_block[:quotas['graph']]))
            
        # 3. Web Data
        if web_text:
            web_block = prompts.CONTEXT_SOURCE_START + web_text + prompts.CONTEXT_SOURCE_END
            final_context_blocks.append(self.compressor.compress(web_block[:quotas['web']]))

        # --- PHASE 4: GENERATION ---
        # 1. Build User Content
        user_content = ""
        if final_context_blocks:
            user_content += "\n".join(final_context_blocks) + "\n\n"
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
            is_project = self._is_project_request(user_input, intent=intent, confidence=confidence)
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
            # After a project is built, auto-ingest any .db or .json data files from sandbox
            if project_dir:
                full_project_path = os.path.join(self.sandbox.root_dir, project_dir)
                synced = sync_project_dir(self.brain, self.kg, full_project_path)
                if synced > 0:
                    print(f"[BrainSync] Auto-synced {synced} records from sandbox '{project_dir}' into agent memory.")
            
            return final_response, final_clean

        except Exception as e:
            return f"[Error during generation: {e}]", None

    def _autonomous_coding_loop(self, user_input, messages, raw_response, base_dir=None):
        """Iteratively tests and fixes code blocks with state-tracking and rollback."""
        attempts = 0
        max_attempts = 5
        current_response = raw_response
        last_error = None
        
        best_state = {} # filename -> content
        best_failure_count = float('inf')
        
        while attempts < max_attempts:
            # Audit current sandbox state
            fs_audit = ""
            if base_dir:
                existing_files = self.sandbox.get_audit(base_dir)
                fs_audit = "\n[FILESYSTEM AUDIT] Files currently in sandbox: " + (", ".join(existing_files) if existing_files else "None")

            saved_files, failures = self._extract_and_save_files(current_response, base_dir=base_dir)
            if not saved_files and not failures:
                return current_response, re.sub(r'\[FACT\].*', '', current_response).strip()

            print(f"[*] Autonomous Testing: Verifying {len(saved_files)} files...")
            
            all_success = True
            test_results = []
            failure_count = len(failures)
            current_files_state = {}
            
            for f in saved_files:
                # Read from sandbox for state tracking
                sandbox_root = self.sandbox.root_dir
                filepath = os.path.join(sandbox_root, base_dir, f) if base_dir else os.path.join(sandbox_root, f)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f_read:
                        current_files_state[f] = f_read.read()
                except: pass

                success, output = self._run_test(f, base_dir=base_dir)
                test_results.append(f"File: {f} | Success: {success}\nOutput:\n{output}")
                if not success:
                    all_success = False
                    failure_count += 1
            
            result_summary = "\n\n".join(test_results)
            
            if all_success:
                print("[+] Autonomous Testing: All tests PASSED.")
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
            
            # --- STATE DISCIPLINE ---
            if failure_count < best_failure_count:
                best_failure_count = failure_count
                best_state = current_files_state
                print(f"[*] New Best State: {best_failure_count} failures.")
            elif failure_count > best_failure_count:
                print(f"[!] Regression Detected: {failure_count} failures (Best was {best_failure_count}). Rolling back...")
                # Restore best state to sandbox
                sandbox_root = self.sandbox.root_dir
                for fname, content in best_state.items():
                    fpath = os.path.join(sandbox_root, base_dir, fname) if base_dir else os.path.join(sandbox_root, fname)
                    with open(fpath, 'w', encoding='utf-8') as f_write:
                        f_write.write(content)
                result_summary += "\n\n[SYSTEM] REGRESSION DETECTED. Files have been rolled back to the last best state. Please try a different approach."

            attempts += 1
            print(f"[!] Autonomous Testing: Test FAILED (Attempt {attempts}/{max_attempts})")
            
            if result_summary == last_error:
                print("[!] Stagnation Detected: Error is identical to previous attempt.")
                error_content = f"[STAGNATION WARNING] You are repeating the same error. CHANGE YOUR STRATEGY.\n\n{prompts.CODE_ERROR_PROMPT.format(error_output=result_summary)}"
            else:
                error_content = prompts.CODE_ERROR_PROMPT.format(error_output=result_summary)
            
            # Add FS Audit to context
            error_content += fs_audit
            
            last_error = result_summary
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

        # Sandbox Containment Check
        sandbox_root = self.sandbox.root_dir
        if base_dir:
            filepath = os.path.join(sandbox_root, base_dir, filename)
        else:
            filepath = os.path.join(sandbox_root, filename)
            
        if config.SANDBOX_ENFORCED and not self.sandbox.is_safe_path(base_dir or "", filepath):
            return False, f"Aborted: Security violation (path traversal detected for {filename})"
        
        try:
            exec_cwd = os.path.dirname(filepath)
            run_res = subprocess.run(
                [sys.executable, filepath], 
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

    def _validate_code(self, filename, code, available_files=None):
        """Checks code for deep errors (syntax, imports, structure) before saving."""
        if not code or len(code.strip()) == 0:
            return False, "Empty code block."
            
        # JSON Validation
        if filename.endswith('.json'):
            try:
                import json
                json.loads(code)
                return True, "Valid JSON"
            except Exception as e:
                return False, f"Invalid JSON: {str(e)}"

        # Python Validation
        if filename.endswith('.py'):
            import ast
            try:
                tree = ast.parse(code)
            except SyntaxError as e:
                return False, f"Syntax Error: {e.msg} (line {e.lineno})"
            except Exception as e:
                return False, f"Validation system error: {e}"

            # Deep Import Validation
            import sys, pkgutil
            std_libs = set(sys.builtin_module_names)
            for m in pkgutil.iter_modules():
                std_libs.add(m.name)
            
            # Additional allowed environment modules (e.g., config, utils)
            project_modules = {'core', 'utils', 'shards', 'tools'}
            if available_files:
                for f in available_files:
                    if f.endswith('.py'):
                        project_modules.add(f.replace('.py', ''))

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        base_mod = alias.name.split('.')[0]
                        if base_mod not in std_libs and base_mod not in project_modules:
                            return False, f"ModuleNotFoundError: Hallucinated import '{alias.name}'"
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        base_mod = node.module.split('.')[0]
                        if base_mod not in std_libs and base_mod not in project_modules and node.level == 0:
                             return False, f"ModuleNotFoundError: Hallucinated from-import '{node.module}'"
        
        # Check for obvious truncation (unclosed quotes)
        if code.count('"""') % 2 != 0 or code.count("'''") % 2 != 0:
            return False, "Potential truncation detected (unclosed triple-quotes)."
            
        return True, "Valid"

    def _extract_and_save_files(self, text, base_dir=None, manifest=None):
        """Robustly finds [FILE: name] tags, validates, and saves using SandboxManager. Returns (saved, failures)."""
        file_markers = list(re.finditer(r"\[FILE:\s*(.+?)\]", text))
        
        if base_dir:
            scratch_dir = self.sandbox.create_sandbox(base_dir)
        else:
            scratch_dir = self.sandbox.root_dir
            
        os.makedirs(scratch_dir, exist_ok=True)
        
        saved_files = []
        failure_reasons = {} # filename -> reason
        
        # Prepare availability list for import validation
        available = set(manifest) if manifest else set()
        
        for i, marker in enumerate(file_markers):
            filename = marker.group(1).strip()
            start_search = marker.end()
            end_search = file_markers[i+1].start() if i+1 < len(file_markers) else len(text)
            look_ahead_text = text[start_search:end_search]
            
            block_match = re.search(r"```[a-z]*\n(.+?)(?:\n?```|$)", look_ahead_text, re.DOTALL)
            
            if block_match:
                code = block_match.group(1)
                is_valid, reason = self._validate_code(filename, code, available_files=available)
                
                if not is_valid:
                    print(f"[!] Validation FAILED for {filename}: {reason}")
                    failure_reasons[filename] = reason
                    continue

                filepath = os.path.join(scratch_dir, filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                
                try:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(code)
                    print(f"[*] Autonomous Coding: Saved validated {filename}")
                    saved_files.append(filename)
                    available.add(filename) # Self-consistency check for multi-file batches
                except Exception as e:
                    failure_reasons[filename] = f"Disk Write Error: {str(e)}"
            else:
                failure_reasons[filename] = "No code block found after tag."
                
        return saved_files, failure_reasons

    def _is_project_request(self, text, intent=None, confidence=0):
        """Detects if the request is for a complex project using HDC semantic routing."""
        # 1. Primary: HDC Intent Routing
        if intent == "PROJECT" and confidence > 0.35:
            return True
            
        # 2. Secondary: Rule-based fallback with learning trigger
        keywords = [
            r'\bproject\b', r'\bapplication\b', r'\bsystem\b', 
            r'\bmultiple files\b', r'\bapp\b', r'\bcomplex software\b', 
            r'\bsqlite\b', r'\bdatabase\b'
        ]
        text_low = text.lower()
        # Ensure we match whole words only (e.g. 'app' but not 'applied')
        has_keywords = any(re.search(k, text_low) for k in keywords) and len(text.split()) > 5
        
        if has_keywords:
            # Rule matched but HDC was uncertain. Feedback loop: teach the brain!
            print(f"[*] HDC confidence low ({confidence:.2f}), but rules matched. Reinforcing brain...")
            self.brain.refine_intent("PROJECT", text)
            return True

        return False

    def _load_available_shards(self):
        """Optimized shard retrieval using local cache."""
        if self._persona_cache:
            return list(self._persona_cache.values())
        return self._load_shards_from_disk()

    def _load_shards_from_disk(self):
        """Scans shards/agents and shards/skills for available personas."""
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        shards_dir = os.path.join(root_dir, 'shards')
        
        shards = []
        for category in ['agents', 'skills']:
            cat_path = os.path.join(shards_dir, category)
            if not os.path.exists(cat_path):
                continue
            for f in os.listdir(cat_path):
                if f.endswith('.md'):
                    shard_path = os.path.join(cat_path, f)
                    with open(shard_path, 'r', encoding='utf-8') as sf:
                        content = sf.read()
                        # Basic metadata extraction (look for frontmatter or name)
                        name = f.replace('.md', '')
                        shards.append({
                            'name': name,
                            'path': shard_path,
                            'content': content,
                            'category': category
                        })
        return shards

    def _select_best_persona(self, plan_text, shards):
        """Asks the LLM to select the best shard (optimized)."""
        # Pre-review routing
        if self.local_llm and self.local_llm.classify_complexity(plan_text) == "LOW":
             print("[*] Performance Optimization: Using Local LLM for persona selection.")
             shard_list = ", ".join([s['name'] for s in shards])
             prompt = f"[ROUTER] Shards: {shard_list}. Select best for: {plan_text[:100]}. Answer: "
             selection = self.local_llm.generate(prompt, max_new_tokens=10, temperature=0)
             if selection:
                 selection = selection.lower().strip()
                 for s in shards:
                     if s['name'].lower() in selection:
                         return s

        shard_list = "\n".join([f"- {s['name']} ({s['category']})" for s in shards])
        
        routing_prompt = f"""[INTENT ROUTER]
Given the following project plan, select the BEST specialized agent or skill to implement it.
Return ONLY the name of the shard (e.g., 'code_architect').

SHARDS AVAILABLE:
{shard_list}

PROJECT PLAN:
{plan_text[:1000]}...
"""
        
        messages = [
            {"role": "system", "content": "You are a high-speed routing engine. Output ONLY the filename (without extension)."},
            {"role": "user", "content": routing_prompt}
        ]
        
        response = self.client.chat.completions.create(
            model=config.MODEL_NAME,
            messages=messages,
            temperature=0, # Deterministic routing
            max_tokens=20
        )
        
        selection = response.choices[0].message.content.strip().lower()
        print(f"[*] Project Routing: LLM suggested '{selection}'")

        # Robust matching: Strip extension and search for shard names within the response
        for s in shards:
            shard_name = s['name'].lower()
            # Check if name is in selection or selection contains name
            if shard_name in selection or selection in shard_name:
                return s
        
        return None

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
        
        # 3. Create Sandbox Environment
        import time
        project_name = re.sub(r'[^a-z0-9]', '_', user_input.lower())[:20]
        project_dir_name = f"project_{project_name}_{int(time.time())}"
        sandbox_path = self.sandbox.create_sandbox(project_dir_name)
        
        # 4. Save PLAN.md
        #    a) Try extracting a tagged [FILE: PLAN.md] block from the response
        #    b) Guarantee write: if nothing was extracted, write the raw plan directly
        saved_files, _ = self._extract_and_save_files(plan_raw, base_dir=project_dir_name)
        
        plan_md_path = os.path.join(sandbox_path, 'PLAN.md')
        if 'PLAN.md' not in saved_files:
            # Fallback: write the raw model response as PLAN.md to the sandbox
            with open(plan_md_path, 'w', encoding='utf-8') as f:
                f.write(plan_raw)
            print(f"[*] Project Planning: Plan saved to sandbox/{project_dir_name}/PLAN.md (fallback write)")
        else:
            print(f"[*] Project Planning: Plan saved to sandbox/{project_dir_name}/PLAN.md (validated write)")

        # 5. Dynamic Persona Selection
        print("[*] Project Routing: Selecting best persona for implementation...")
        available_shards = self._load_available_shards()
        selected_shard = self._select_best_persona(plan_raw, available_shards)
        
        if selected_shard:
            print(f"[+] Project Routing: Selected '{selected_shard['name']}' ({selected_shard['category']}) persona.")
            # Swapping context: Build a fresh message history with the new persona
            messages = [
                {"role": "system", "content": selected_shard['content']},
                {"role": "user", "content": f"Previous Request: {user_input}"},
                {"role": "assistant", "content": plan_raw}
            ]
        else:
            print("[!] Project Routing: No specific shard selected. Using default system prompt.")
            # Fallback to standard messages
            messages.append({"role": "assistant", "content": plan_raw})

        # 6. Building Phase (Iterative Manifest Check)
        building_instruction = f"The plan is approved. Now implement the project files into the {project_dir_name} directory as defined in the plan. Return ALL files using [FILE: filename] tags."
        messages.append({"role": "user", "content": building_instruction})
        
        print(f"[*] Autonomous Coding: Transitioning to implementation with persona...")
        
        # turn 1
        response = self.client.chat.completions.create(
            model=config.MODEL_NAME,
            messages=messages,
            temperature=config.TEMPERATURE,
            max_tokens=config.MAX_TOKENS_GENERATION
        )
        first_resp = response.choices[0].message.content
        manifest = self._extract_manifest(plan_raw)
        saved_files, failures = self._extract_and_save_files(first_resp, base_dir=project_dir_name, manifest=manifest)
        messages.append({"role": "assistant", "content": first_resp})

        # --- COMPLETENESS LOOP ---
        if manifest:
            print(f"[*] Autonomous Audit: Manifest requires {len(manifest)} files.")
            retries = 0
            while retries < 3:
                missing = [f for f in manifest if f not in saved_files and f != "PLAN.md"]
                if not missing:
                    print("[+] Autonomous Audit: Project manifest satisfied.")
                    break
                
                retries += 1
                rejection_notes = ""
                if failures:
                    rejection_notes = "\nSpecific Rejections:\n" + "\n".join([f"- {fn}: {rs}" for fn, rs in failures.items() if fn in manifest])

                print(f"[!] Autonomous Audit: Missing/Broken {len(missing)} files. Retrying ({retries}/3)...")
                
                resume_prompt = f"The follow-up Turn is required. The following files are missing or were rejected by the system: {', '.join(missing)}.{rejection_notes}\n\nPlease output the full code for THESE FILES ONLY now using the [FILE: filename] tags."
                messages.append({"role": "user", "content": resume_prompt})
                
                response = self.client.chat.completions.create(
                    model=config.MODEL_NAME,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=config.MAX_TOKENS_GENERATION
                )
                
                new_resp = response.choices[0].message.content
                newly_saved, new_failures = self._extract_and_save_files(new_resp, base_dir=project_dir_name, manifest=manifest)
                saved_files.extend(newly_saved)
                failures.update(new_failures)
                messages.append({"role": "assistant", "content": new_resp})

        # Synthesize a meaningful project summary
        saved_unique = set(saved_files)
        required = {f for f in manifest if f != "PLAN.md"}
        done = len(saved_unique & required)
        total = len(required)
        
        compliance_str = f"{done}/{total} files" if total > 0 else "N/A"
        print(f"[*] Project Planning: Manifest compliance: {compliance_str}")

        # For the final summary, we use a specialized report generator
        final_summary = self._generate_project_report(
            plan_raw, 
            list(saved_unique), 
            project_dir_name
        )
            
        return project_dir_name, final_summary

    def _extract_manifest(self, plan_text):
        """Parses PLAN.md to find the list of required files."""
        # Find the 'File Structure' section
        match = re.search(r"## File Structure\s*\n(.*?)(?:\n##|$)", plan_text, re.DOTALL)
        if not match:
            return []
        
        section = match.group(1)
        # Find bullets like "- `filename`" or "- filename"
        # Regex explanation: optional bullet, optional backtick, path-like chars, optional backtick
        files = re.findall(r"[-*]\s*`?([\w\./-]+)`?", section)
        return [f.strip() for f in files]

    def _generate_project_report(self, plan_text, saved_files, project_dir):
        """Uses LLM to synthesize a professional project summary with programmatic audit."""
        print("[*] Project Reporting: Synthesizing final report...")
        
        # 1. Deterministic Audit
        unresolved = []
        entrypoint = "Not detected"
        for f in saved_files:
            if f.endswith('.py'):
                # Heuristic for entrypoint
                if f in ['main.py', 'app.py', 'index.py'] or 'start' in f.lower():
                    entrypoint = f
                
                success, output = self._run_test(f, base_dir=project_dir)
                if not success:
                    unresolved.append(f"{f}: {output[:100]}")

        # Programmatic Audit Header (The "Truth" Layer)
        audit_header = f"""### SYSTEM AUDIT (Deterministic)
- **Project Directory**: `sandboxes/{project_dir}`
- **Entrypoint**: `{entrypoint}`
- **Files Created**: {len(saved_files)}
- **Files List**: {", ".join(saved_files)}
- **Test Failures**: {len(unresolved)}
"""
        if unresolved:
            audit_header += "- **Failure Logs**:\n  - " + "\n  - ".join(unresolved) + "\n"
        
        audit_header += "\n---\n"

        # 2. LLM Synthesized Summary
        report_prompt = prompts.PROJECT_REPORT_PROMPT.format(
            plan_text=plan_text[:1000],
            files_list=", ".join(saved_files),
            test_results="\n".join(unresolved) if unresolved else "All basic tests passed."
        )
        
        try:
            response = self.client.chat.completions.create(
                model=config.MODEL_NAME,
                messages=[{"role": "user", "content": report_prompt}],
                temperature=0.3,
                max_tokens=500
            )
            return audit_header + response.choices[0].message.content
        except Exception as e:
            return audit_header + f"\n[LLM Synthesis failed: {e}]"

    def reset(self):
        """Clears the conversational history."""
        self.messages = []
        self.last_subject = None
        print("[*] Agent Brain history purged for fresh context.")

    def _check_context_stability(self):
        """Calculates total character length of current history."""
        total_chars = sum(len(m['content']) for m in self.messages)
        return total_chars

    def _perform_spin_down(self, current_task=""):
        """Summarizes state, stores in Brain, and resets context."""
        print(f"[*] Context window full ({self._check_context_stability()} chars). Spinning down...")
        
        summary_prompt = f"""[INTERNAL: CONTEXT RESET]
Our conversation history is being reset to save memory. 
Summarize the current state of our work, active tasks, and any critical decisions made so far. 
Be concise but ensure Your future self can continue without losing momentum.
Current Task context: {current_task}
"""
        temp_messages = self.messages + [{"role": "user", "content": summary_prompt}]
        
        try:
            response = self.client.chat.completions.create(
                model=config.MODEL_NAME,
                messages=temp_messages,
                temperature=0.1,
                max_tokens=300
            )
            summary = response.choices[0].message.content
            # Save to Brain with a specialized marker
            marker = f"[SESSION_STATE] Timestamp: {os.path.getmtime(self.brain.filename if os.path.exists(self.brain.filename) else '.')}\nSummary: {summary}"
            self.brain.add_document(marker)
            
            # Reset active history
            self.reset()
            print("[+] State summarized and saved to Brain. Session restarted.")
            return True
        except Exception as e:
            print(f"[!] Spin down failed: {e}")
            return False

    def _try_tool_short_circuit(self, query):
        """Attempts to execute a local tool to save tokens and time."""
        query_low = query.lower()
        cmd = None
        args = []

        # Map query to tools
        if any(x in query_low for x in ["/scan", "scan project", "list directory", "list all files"]):
            cmd = "tools/project_scanner.py"
        elif any(x in query_low for x in ["/grep", "search pattern", "find in files", "grep"]):
            cmd = "tools/pattern_grep.py"
            # Extract pattern if possible
            parts = query.split()
            if len(parts) > 1:
                args = [parts[-1].strip("'\"")]
        elif any(x in query_low for x in ["/audit", "dependency audit", "check versions"]):
            cmd = "tools/dependency_audit.py"

        if not cmd:
            return None

        print(f"[*] Tool Short-Circuit: Running {cmd}...")
        try:
            # Use sys.executable to ensure we use the same environment
            full_cmd = [sys.executable, cmd] + args
            result = subprocess.run(full_cmd, capture_output=True, text=True)
            return result.stdout if result.returncode == 0 else f"Tool Error: {result.stderr}"
        except Exception as e:
            return f"System Error executing tool: {str(e)}"
