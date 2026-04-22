import re
import subprocess
import os
import sys
import ast
from openai import OpenAI
from core import config, prompts
from core.compressor import PromptCompressor
from core.sandbox import SandboxManager
from core.local_llm import LocalLLM
from utils.brain_sync import sync_project_dir, sync_from_sqlite, sync_from_json
from utils.text_utils import count_tokens, summarize_text_python

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

    def chat(self, user_input, mode_override=None):
        """Processes a user message through the full neurosymbolic pipeline."""
        
        # --- PHASE 0: SEMANTIC CACHE LOOKUP ---
        # Normalize query for higher hit rate (Phase 9 optimization)
        norm_query = re.sub(r'[^\w\s]', '', user_input).lower().strip()
        cache_hit = self.brain.search_cache(norm_query, threshold=config.CACHE_THRESHOLD)
        if cache_hit:
            raw_response = cache_hit['raw'] + "\n[Semantic Cache Hit]"
            clean_ans = cache_hit['clean']
            # Update history but skip logic
            self.messages.append({"role": "user", "content": user_input})
            self.messages.append({"role": "assistant", "content": clean_ans})
            if len(self.messages) > 10: self.messages = self.messages[-10:]
            return raw_response, clean_ans

        # --- PHASE 0.5: CONTEXT STABILITY CHECK ---
        # Proactive Spin-Down (Elite V5): Trigger if history is nearing token limit
        request_mode = mode_override or config.OPERATING_MODE
        history_tokens = sum(count_tokens(m['content']) for m in self.messages)
        token_limit = config.DEEP_MODE_CONTEXT_TOKENS if request_mode == "DEEP" else config.FAST_MODE_CONTEXT_TOKENS
        
        if history_tokens > 0.8 * token_limit:
            print(f"[*] Proactive Context Guard: History ({history_tokens} tokens) near limit. Spinning down...")
            self._perform_spin_down(current_task=user_input)

        # --- PHASE 1: ULTRA-FAST INTENT ROUTING (HDC) ---
        intent, confidence = self.brain.classify_intent(user_input)
        is_code_task = any(k in user_input.lower() for k in ['write', 'code', 'script', 'implement', 'algorithm', 'project'])
        
        # --- PHASE 1.5: SHORT-CIRCUIT TOOLING ---
        is_command = user_input.startswith('/')
        fast_intent = self.local_llm.fast_intent_classify(user_input) if self.local_llm else "UNKNOWN"
        
        if (intent == "TOOL" and confidence > 0.40) or is_command or fast_intent == "SHELL":
            tool_res = self._try_tool_short_circuit(user_input)
            if tool_res:
                print(f"[*] Fast Lane: Tool Short-Circuit Success ({intent}/{fast_intent})")
                return tool_res + "\n[Fast-Lane Tool Success]", tool_res

        # Phase 7: Speculative Mode Switching
        if request_mode == "FAST":
             if intent == "PROJECT" and confidence > 0.85:
                  print("[!] Operating Mode Warning: Project requested but system is in FAST mode.")
                  msg = "I've detected a project-building request, but I am currently in LOW-POWER mode to save resources. Please switch to DEEP mode if you'd like me to build this for you."
                  return msg, msg

        # Gate 0: Ultra-Fast Path (Phase 8)
        is_simple = len(user_input.split()) < config.SIMPLE_QUERY_LIMIT
        is_static_recall = (intent == "RECALL" and confidence > 0.40)
        
        # Search for follow-up pronouns
        pronouns = ['it', 'they', 'them', 'him', 'her', 'this', 'that']
        is_followup = len(user_input.split()) < 3 or any(re.search(rf'\b{p}\b', user_input.lower()) for p in pronouns)

        if is_simple and is_static_recall and not cache_hit:
             print(f"[*] Gate 0: Simple Query Fast-Track (Confidence: {confidence:.2f})")
             current_subject = user_input
             is_dynamic = False
             # Bypass Deep Lane resolution entirely
        else:
            # Gate 1: Selective Reasoning (Deep Lane Trigger)
            if is_followup and self.last_subject:
                current_subject = self.last_subject
                is_dynamic = (intent == "SEARCH") or (confidence < 0.35)
            else:
                # Trigger Deep Lane only if uncertainty is high AND it's not a simple query
                if confidence < config.FORCE_DEEP_THRESHOLD and not is_simple:
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
        # Elite V5.6: Deterministic State Retrieval
        latest_state = self.brain.get_latest_session_state()
        session_mems = [(1.0, latest_state)] if latest_state else []
        
        # 3. Graph Search
        graph_facts = []
        search_terms = {current_subject.lower(), user_input.lower()}
        if self.last_subject: 
            search_terms.add(self.last_subject.lower())
        
        for word in user_input.split():
                search_terms.add(word.lower())
        
        for term in search_terms:
            graph_facts.extend(self.kg.get_related_facts(term))
        
        # Neurosymbolic Bridge: Semantic Search for Concept-Based Facts
        query_hv = self.brain.encode(user_input)
        graph_facts.extend(self.kg.get_related_facts_semantic(query_hv, self.brain, threshold=0.15))
        
        # --- PHASE 3: SELECTIVE DYNAMIC RETRIEVAL ---
        is_dynamic_query = any(k in user_input.lower() for k in config.DYNAMIC_ONLY_KEYWORDS)
        intent_to_discover = (is_dynamic_query or '?' in user_input) and (intent != "RECALL")
        web_text = None
        
        if intent_to_discover:
            # Skeptical Skip (Phase 11): Only search if vector confidence is low
            max_score = vector_results[0][0] if vector_results else 0.0
            if max_score < 0.75:
                print(f"[*] Analyzing dynamic context for: {search_query}...")
                web_raw = self.searcher.search(search_query)
                if web_raw:
                    sections = [s.strip() for s in web_raw.split('\n\n') if len(s.strip()) > 50]
                    web_text = "\n\n".join(sections[:2])

        # --- PHASE 4: CONTEXT BUILDER (Elite V6 Deterministic) ---
        # Centralized assembly with tiered budgeting and deduplication
        messages, context_tokens, request_mode = self._build_context(
            user_input, 
            intent, 
            confidence, 
            vector_results, 
            graph_facts, 
            session_mems, 
            web_text,
            is_code_task,
            request_mode
        )

        # Pre-Inference Compression for DEEP mode
        if request_mode == "DEEP" and context_tokens > 0.7 * config.DEEP_MODE_CONTEXT_TOKENS:
             print(f"[*] Pre-Inference Compression: Optimizing {context_tokens} tokens...")
             for m in messages:
                  if m['role'] == 'user':
                       m['content'] = self.compressor.compress(m['content'])

        print(f"Gemma is thinking ({request_mode} mode)...", flush=True)
        
        try:
            # Enforcement of output budget
            max_out = config.FAST_MODE_OUTPUT_TOKENS if request_mode == "FAST" else config.DEEP_MODE_OUTPUT_TOKENS
            
            # Phase 8: Escalate to DEEP mode if code task
            current_temp = config.TEMPERATURE
            if (is_code_task or "[FILE:" in user_input) and request_mode == "FAST":
                 print(f"[*] Selective Gating: Escalating code task from {request_mode} to DEEP mode budgets.")
                 request_mode = "DEEP"
                 max_out = config.DEEP_MODE_OUTPUT_TOKENS
                 current_temp = 0.4
            elif request_mode == "FAST":
                 current_temp = 0.2 # Extreme focus for FAST mode

            # --- PHASE 4.7: NO-FAIL INFERENCE (Elite V5.2 MVC) ---
            try:
                # Step 1 Guard: Use smaller budget for initial reasoning turns
                actual_max_out = max_out
                if len(self.messages) < 2 and request_mode == "DEEP":
                     actual_max_out = min(max_out, config.INITIAL_TURN_MAX_TOKENS)

                response = self.client.chat.completions.create(
                    model=config.MODEL_NAME,
                    messages=messages,
                    temperature=current_temp,
                    max_tokens=actual_max_out,
                    stop=config.STOP_SEQUENCES,
                    timeout=config.REQUEST_TIMEOUT
                )
            except Exception as e:
                # Tier 1: Emergency MVC Recovery (Strip-to-Basic)
                if "context" in str(e).lower() or "500" in str(e) or "timeout" in str(e).lower():
                    print("[!] Context Overrun: Triggering Emergency MVC Recovery (Tier 1)...")
                    mvc_messages = [
                        {"role": "system", "content": messages[0]['content']},
                        {"role": "user", "content": f"USER QUESTION: {user_input}"}
                    ]
                    try:
                        response = self.client.chat.completions.create(
                            model=config.MODEL_NAME,
                            messages=mvc_messages,
                            temperature=0.1,
                            max_tokens=128, # Very small for recovery
                            timeout=60
                        )
                    except Exception as e2:
                        # Tier 2: Nuclear MVC (Minimal System + Small Question)
                        print("[!] Tier 1 FAILED: Triggering NUCLEAR MVC Recovery (Tier 2)...")
                        nuclear_messages = [
                            {"role": "system", "content": "Answer concisely in 1-2 sentences."},
                            {"role": "user", "content": f"Quickly answer: {user_input[:50]}"}
                        ]
                        response = self.client.chat.completions.create(
                            model=config.MODEL_NAME,
                            messages=nuclear_messages,
                            temperature=0.1,
                            max_tokens=64,
                            timeout=30
                        )
                else: raise e
            
            raw_response = response.choices[0].message.content
            
            # --- PHASE 4.8: STRICT OUTPUT GUARD (Elite V5.6) ---
            # EXTREME RELAXATION: Only trigger on truly empty/None
            if not raw_response or len(raw_response.strip()) == 0:
                print("[!] Strict Output Guard: Empty response detected. Triggering recovery...")
                # Log the failing messages for offline audit
                with open("test/logs/failing_prompt.json", "w") as f:
                    import json
                    json.dump(messages, f, indent=2)

                # Elite V5.7: Context-Aware Recovery
                state_prefix = ""
                if session_mems:
                    state_prefix = f"PREVIOUS CONTEXT: {session_mems[0][1]}\n"

                mvc_messages = [
                    {"role": "system", "content": "You are a helpful assistant. Answer concisely and factually based on the provided context."},
                    {"role": "user", "content": f"{state_prefix}Answer concisely: {user_input}"}
                ]
                try:
                    response = self.client.chat.completions.create(
                        model=config.MODEL_NAME,
                        messages=mvc_messages,
                        temperature=0.1,
                        max_tokens=256,
                        timeout=150
                    )
                    raw_response = response.choices[0].message.content
                except: raw_response = ""

                # --- PHASE 4.9: DETERMINISTIC FALLBACK (Final Stand) ---
                if not raw_response or len(raw_response.strip()) == 0:
                    # Elite V6: Harden summary detection
                    is_summary_req = (intent == "SUMMARY") or any(k in user_input.lower() for k in ["summarize", "recap", "recapitulate", "synthesize this session", "what happened", "what did we do"])
                    
                    if is_summary_req:
                        print("[!] Final Stand: Summary synthesis failed. Attempting direct retrieval...")
                        if session_mems:
                            raw_response = f"I'm having trouble synthesizing a new summary, but here is my retrieved state: {session_mems[0][1]}"
                        else:
                            raw_response = "I have preserved our session state, but I'm having trouble accesssing the summary right now. Our progress is safe."
                    else:
                        print("[!] Final Stand: LLM unresponsive. Falling back to Knowledge Graph...")
                        if graph_facts:
                            raw_response = f"I am experiencing high latency with my reasoning engine. Based on my internal knowledge graph, I know the following: {', '.join(graph_facts[:3])}. How else can I help?"
                        else:
                            raw_response = "My reasoning layer is currently under heavy load. Please try a simpler query or check the local logs for details."
            
            print(f"[DEBUG RAW OUTPUT]: {repr(raw_response)}")

            # --- PHASE 4.7: AUTOMATIC CONSTRAINT VALIDATION (Elite V4) ---
            if is_code_task and "[FILE:" not in raw_response:
                print("[!] Execution Policy Violation: Code task detected but no [FILE:] tags found. Triggering repair...")
                repair_msg = "Your previous response was purely conversational. RE-PROMPT: Output the actual source code now in [FILE: filename] blocks as required by the Execution Policy."
                messages.append({"role": "assistant", "content": raw_response})
                messages.append({"role": "user", "content": repair_msg})
                
                response = self.client.chat.completions.create(
                    model=config.MODEL_NAME,
                    messages=messages,
                    temperature=0.2, # Lower temp for strict compliance
                    max_tokens=max_out
                )
                raw_response = response.choices[0].message.content
                print(f"[DEBUG REPAIR OUTPUT]: {repr(raw_response)}")
            
            # --- PHASE 5: KNOWLEDGE SYNC ---
            # 1. Update Graph (Skip triplets in FAST mode to save tokens)
            if request_mode != "FAST":
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
            if web_text and request_mode != "FAST":
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
                pass # Cache moved after fallback logic (Gate 5)
            
            # --- PHASE 6: AUTONOMOUS TEST-EDIT LOOP ---
            final_response, final_clean = self._autonomous_coding_loop(user_input, messages, raw_response, base_dir=project_dir)
            
            # --- PHASE 7: POST-BUILD DATA SYNC ---
            # After a project is built, auto-ingest any .db or .json data files from sandbox
            if project_dir:
                full_project_path = os.path.join(self.sandbox.root_dir, project_dir)
                synced = sync_project_dir(self.brain, self.kg, full_project_path)
                if synced > 0:
                    print(f"[BrainSync] Auto-synced {synced} records from sandbox '{project_dir}' into agent memory.")
            
            # Gate 5: Blank Response Fallback - 2-Tier Elite V3 System
            if not final_clean:
                if request_mode == "FAST":
                    print("[*] FAST mode failure detected. Escalating directly to DEEP mode recovery...")
                    return self.chat(user_input, mode_override="DEEP")

            # 4. Add to Semantic Prompt Cache (only if not empty)
            if final_clean:
                # Cache the normalized query for higher recall
                norm_query = re.sub(r'[^\w\s]', '', user_input).lower().strip()
                self.brain.add_to_cache(norm_query, raw_response, final_clean)

            return final_response, final_clean

        except Exception as e:
            return f"[Error during generation: {e}]", None

    def _autonomous_coding_loop(self, user_input, messages, raw_response, base_dir=None):
        """Iteratively tests and fixes code blocks with state-tracking and vector-memory feedback."""
        attempts = 0
        max_attempts = 5
        current_response = raw_response
        last_error = None
        
        # Keep track of the original context (system + plan) to avoid bloat
        # We only need the core instructions and the first turn's context
        base_messages = [messages[0]] # System Prompt
        if len(messages) > 1:
            base_messages.append(messages[1]) # Original User Input
        
        best_state = {} 
        best_failure_count = float('inf')
        
        while attempts < max_attempts:
            # 1. Audit Filesystem
            fs_audit = ""
            if base_dir:
                existing_files = self.sandbox.get_audit(base_dir)
                fs_audit = "\n[FILESYSTEM AUDIT] Files currently in sandbox: " + (", ".join(existing_files) if existing_files else "None")

            # 2. Extract & Save Files
            saved_files, failures = self._extract_and_save_files(current_response, base_dir=base_dir)
            if not saved_files and not failures:
                # No code found, return what we have
                return current_response, re.sub(r'\[FACT\].*', '', current_response).strip()

            # 3. Verify Files
            all_success = True
            test_results = []
            failure_count = len(failures)
            current_files_state = {}
            
            for f in saved_files:
                sandbox_root = self.sandbox.root_dir
                filepath = os.path.join(sandbox_root, base_dir, f) if base_dir else os.path.join(sandbox_root, f)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f_read:
                        current_files_state[f] = f_read.read()
                except: pass

                success, output = self._run_test(f, base_dir=base_dir)
                test_results.append(f"File: {f} | Success: {success}\nOutput:\n{output}")
                
                # --- PHASE 9: FAILURE VECTORIZATION (Coding Lessons) ---
                if not success:
                    all_success = False
                    failure_count += 1
                    error_type = self._classify_error(output)
                    # Phase 10: Granular Feedback logic
                    clean_error = output.replace(sandbox_root, "[SANDBOX]")
                    lesson = f"[CODING_LESSON] File: {f} | Error: {error_type} | Message: {clean_error[:300]}"
                    self.brain.add_document(lesson)
                    print(f"[*] Memory Sync: Vectorized failure as coding lesson ({error_type}).")

            result_summary = "\n\n".join(test_results)
            
            # --- SUCCESS PATH ---
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
            
            # --- FAILURE PATH & REPAIR ---
            if failure_count < best_failure_count:
                best_failure_count = failure_count
                best_state = current_files_state
            elif failure_count > best_failure_count:
                print(f"[!] Regression: Rolling back to best state ({best_failure_count} failures).")
                for fname, content in best_state.items():
                    fpath = os.path.join(self.sandbox.root_dir, base_dir, fname) if base_dir else os.path.join(self.sandbox.root_dir, fname)
                    with open(fpath, 'w', encoding='utf-8') as f_write:
                        f_write.write(content)

            # --- STATELESS REPAIR PROMPT RECONSTRUCTION ---
            error_type = self._classify_error(result_summary)
            attempts += 1
            print(f"[!] Autonomous Testing: Attempt {attempts}/{max_attempts} FAILED. Class: {error_type}")

            # 1. Retrieve Lessons Learned from Memory
            related_lessons = self.brain.search(result_summary, threshold=0.05, top_k=2)
            lessons_text = ""
            if related_lessons:
                lessons_text = prompts.CONTEXT_LESSONS + "\n".join([f"- {l[1]}" for l in related_lessons]) + "\n"

            # 2. Build Targeted Error Content
            error_content = ""
            failing_files = [res.split('|')[0].replace('File:', '').strip() for res in test_results if 'Success: False' in res]
            
            # Phase 12: Manifest Audit (Elite V5.5)
            manifest_audit = ""
            if base_dir:
                try:
                    plan_path = os.path.join(self.sandbox.root_dir, base_dir, "PLAN.md")
                    if os.path.exists(plan_path):
                        with open(plan_path, 'r') as f_plan:
                            manifest = self._extract_manifest(f_plan.read())
                            actual_files = os.listdir(os.path.join(self.sandbox.root_dir, base_dir))
                            missing = [m for m in manifest if m not in actual_files]
                            if missing:
                                manifest_audit = f"[MANIFEST ALERT] The following files from the plan are MISSING. You MUST generate them now: {missing}\n"
                except: pass

            # Phase 11: Dependency Guard (Elite V5.1)
            dependency_warning = ""
            if error_type == "IMPORT":
                # Find which import failed
                imp_match = re.search(r"ModuleNotFoundError: No module named '([\w.]+)'", result_summary)
                if imp_match:
                    hallucinated_mod = imp_match.group(1)
                    # List actual sandbox files
                    sandbox_files = [f for f in os.listdir(os.path.join(self.sandbox.root_dir, base_dir)) if f.endswith('.py')]
                    
                    # Blacklisting common hallucinated patterns
                    if any(x in hallucinated_mod for x in ["core.utils", "app.utils", "common.utils"]):
                         dependency_warning = f"[DEPENDENCY GUARD] STOP. You are hallucinating a utility file '{hallucinated_mod}'. ONLY use standard libraries or the following project files: {sandbox_files}.\n"
                    else:
                         dependency_warning = f"[DEPENDENCY GUARD] Hallucinated Import: '{hallucinated_mod}'. This module is not available. Project files: {sandbox_files}.\n"

            # Phase 10: Heuristic Correction for Numerical/Logic errors
            heuristic_tip = ""
            if any("fahrenheit" in res.lower() for res in test_results):
                heuristic_tip = "[HEURISTIC] Note: Fahrenheit to Celsius conversion uses (F-32)/1.8. Verify your math constants.\n"

            if error_type == "IMPORT":
                error_content = f"{dependency_warning}[FIX: MISSING IMPORT] {result_summary}"
            elif len(failing_files) >= 1:
                # Surgical Repair Hint
                target = failing_files[0]
                error_content = f"{dependency_warning}{heuristic_tip}[SURGICAL REPAIR] Focus ONLY on fixing {target}.\nFAILURE DETAILS:\n{result_summary}\n\nREPROMPT: Fix the code for {target} and output the full correct version now."
            else:
                error_content = f"{dependency_warning}{heuristic_tip}{prompts.CODE_ERROR_PROMPT.format(error_output=result_summary)}"

            # 3. Construct Repair Message
            repair_user_content = f"{lessons_text}\n{fs_audit}\n{manifest_audit}\nCURRENT ERROR:\n{error_content}"
            
            # 4. Token Budget Guard (Hard Cap)
            total_tokens = count_tokens(repair_user_content) + 500 # buffer for system prompt
            if total_tokens > config.MAX_REPAIR_HISTORY_TOKENS:
                print(f"[!] Context Caution: Prompt ({total_tokens}) near limit. Truncating audit data.")
                repair_user_content = f"{lessons_text}\n[SYSTEM: CONTEXT TRUNCATED]\n\nCURRENT ERROR:\n{error_content[:1500]}"

            # Reconstruct clean message history for this attempt
            repair_messages = list(base_messages)
            repair_messages.append({"role": "user", "content": repair_user_content})
            
            print("Gemma is re-thinking (Memory-Augmented Repair)...", flush=True)
            response = self.client.chat.completions.create(
                model=config.MODEL_NAME,
                messages=repair_messages,
                temperature=0.3,
                max_tokens=config.MAX_TOKENS_GENERATION
            )
            current_response = response.choices[0].message.content
            last_error = result_summary

        return current_response, re.sub(r'\[FACT\].*', '', current_response).strip()

    def _classify_error(self, error_text):
        """Phase 9: Categorizes errors for targeted repair."""
        if not error_text: return "UNKNOWN"
        if "ModuleNotFoundError" in error_text or "No module named" in error_text:
            return "IMPORT"
        if "SyntaxError" in error_text or "invalid syntax" in error_text:
            return "SYNTAX"
        if "NameError" in error_text:
            return "NAME"
        return "RUNTIME"

    def _is_complex_reasoning(self, text, intent, confidence):
        """Elite V3: identifies queries that should skip the FAST lane."""
        # 1. Subject markers for high abstraction
        complexity_keywords = ['compare', 'relate', 'relationship', 'ethics', 'impact', 'intersection', 'theory', 'structure of', 'logical']
        text_low = text.lower()
        has_complex_keyword = any(k in text_low for k in complexity_keywords)
        
        # 2. HDC Uncertainty (if confidence is moderate but not high)
        is_uncertain = confidence < 0.60
        
        # 3. Query length as proxy for nuance
        is_long = len(text.split()) > 10
        
        # 4. Intent Gating: SEARCH intent and low-confidence RECALL of complex topics
        if (intent == "SEARCH") or (intent == "RECALL" and has_complex_keyword and is_uncertain):
            return True
            
        return is_long and has_complex_keyword

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

    def _extract_symbols(self, code):
        """Extracts top-level class and function names from Python code."""
        try:
            tree = ast.parse(code)
            symbols = set()
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    symbols.add(node.name)
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            symbols.add(target.id)
            return symbols
        except:
            return set()

    def _validate_code(self, filename, code, available_files=None, base_dir=None):
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
            local_symbols = {} # module_name -> set of symbols
            
            if available_files:
                for f in available_files:
                    if f.endswith('.py'):
                        mod_name = f.replace('.py', '')
                        project_modules.add(mod_name)
                        
                        # Extract symbols from the available file if it exists on disk
                        sandbox_root = self.sandbox.root_dir
                        fpath = os.path.join(sandbox_root, base_dir, f) if base_dir else os.path.join(sandbox_root, f)
                        if os.path.exists(fpath):
                            try:
                                with open(fpath, 'r', encoding='utf-8') as fr:
                                    local_symbols[mod_name] = self._extract_symbols(fr.read())
                            except: pass

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
                        
                        # Symbol check for local from-imports
                        if base_mod in local_symbols:
                            for alias in node.names:
                                if alias.name != '*' and alias.name not in local_symbols[base_mod]:
                                    return False, f"AttributeError: Module '{node.module}' has no symbol '{alias.name}'"
                
                # Attribute check for 'module.name' style access
                elif isinstance(node, ast.Attribute):
                    if isinstance(node.value, ast.Name) and node.value.id in local_symbols:
                        if node.attr not in local_symbols[node.value.id]:
                            return False, f"AttributeError: Module '{node.value.id}' has no attribute '{node.attr}'"
        
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
                is_valid, reason = self._validate_code(filename, code, available_files=available, base_dir=base_dir)
                
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

        # --- SURGICAL COMPLETENESS LOOP ---
        if manifest:
            print(f"[*] Autonomous Audit: Manifest requires {len(manifest)} files.")
            retries = 0
            while retries < 5: # Increased capacity for surgical patching
                missing = [f for f in manifest if f not in saved_files and f != "PLAN.md"]
                
                # Check for broken files (those that failed validation or tests)
                broken = [fn for fn, rs in failures.items() if fn in manifest]
                
                target_file = None
                reason = ""
                
                if broken:
                    target_file = broken[0]
                    reason = f"The following error was detected in {target_file}: {failures[target_file]}"
                elif missing:
                    target_file = missing[0]
                    reason = f"The file {target_file} was defined in the plan but is missing from the sandbox."
                
                if not target_file:
                    print("[+] Autonomous Audit: Project manifest satisfied.")
                    break
                
                retries += 1
                print(f"[!] Autonomous Audit: Failure in {target_file}. Surgical Repair ({retries}/5)...")
                
                # Build focused repair context
                existing = ", ".join(saved_files)
                # Elite V6.1: Include exact prior iteration failures for grounding
                failure_context = ""
                if target_file in failures:
                    failure_context = f"PREVIOUS ATTEMPT FAILURE: {failures[target_file]}\n"
                
                resume_prompt = f"""[SURGICAL REPAIR]
We are building the project. The following file is BROKEN or MISSING: {target_file}
{reason}
{failure_context}
MANIFEST: {', '.join(manifest)}
EXISTING FILES: {existing}

Please output the FULL CORRECT CODE for {target_file} now using the [FILE: filename] tag. 
Ensure all local imports (like 'from . import module' or 'import module') correctly reference the manifest files.
"""
                messages.append({"role": "user", "content": resume_prompt})
                
                response = self.client.chat.completions.create(
                    model=config.MODEL_NAME,
                    messages=messages,
                    temperature=0.1,
                    max_tokens=config.MAX_TOKENS_GENERATION,
                    timeout=180
                )
                
                new_resp = response.choices[0].message.content
                # Update failures: remove the target file failure before re-extraction
                if target_file in failures:
                    del failures[target_file]
                
                newly_saved, new_failures = self._extract_and_save_files(new_resp, base_dir=project_dir_name, manifest=manifest)
                saved_files.extend([f for f in newly_saved if f not in saved_files])
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
        """Elite V5.3: Robust manifest parsing to catch multi-format plans."""
        # Find the 'File Structure' or 'Files' section
        match = re.search(r"## (?:File Structure|Files)\s*\n(.*?)(?:\n##|$)", plan_text, re.DOTALL | re.IGNORECASE)
        if not match:
            return []
        
        section = match.group(1)
        # Handle multiple bullet styles and optional backticks
        files = re.findall(r"(?:^|\n)[-*]\s*`?([\w\./-]+)`?", section)
        return [f.strip() for f in files if '.' in f]

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

    def _get_sliding_history(self, budget=500):
        """Returns a window of messages that fits within the token budget."""
        # Start with latest messages
        history = []
        current_tokens = 0
        for msg in reversed(self.messages):
            tokens = count_tokens(msg['content'])
            if current_tokens + tokens > budget:
                break
            history.insert(0, msg)
            current_tokens += tokens
        return history

    def _perform_spin_down(self, current_task=""):
        """Summarizes state with grounded memory retrieval and resets context."""
        print(f"[*] Context window full ({self._check_context_stability()} chars). Grounding session state...")
        
        # 1. Retrieve most relevant session memories for grounding (Elite V5.8 Deterministic)
        latest_state = self.brain.get_latest_session_state()
        retrieved_context = f"[PRIOR SESSION SUMMARY]\n{latest_state}" if latest_state else "None"
        
        # 2. Build history context (Expand to capture depth without truncation)
        history_context = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in self.messages])

        # 3. Generate Grounded Summary
        summary_prompt = prompts.GROUNDED_SUMMARY_PROMPT.format(
            retrieved_context=retrieved_context,
            history_context=history_context
        )
        temp_messages = [{"role": "user", "content": summary_prompt}]
        
        try:
            response = self.client.chat.completions.create(
                model=config.MODEL_NAME,
                messages=temp_messages,
                temperature=0.1,
                max_tokens=400,
                timeout=90
            )
            summary = response.choices[0].message.content
            
            # Elite V5.6: Spin-Down Recovery Guard
            if not summary or len(summary.strip()) == 0:
                print("[!] Spin-down recovery: Primary summary failed, attempting emergency synthesis...")
                emergency_prompt = f"Provide a 2-sentence summary of what happened here: {history_context}"
                response = self.client.chat.completions.create(
                    model=config.MODEL_NAME,
                    messages=[{"role": "user", "content": emergency_prompt}],
                    temperature=0.1,
                    max_tokens=200
                )
                summary = response.choices[0].message.content

            # Elite V7: Save with structured marker for deterministic retrieval
            marker = f"[SESSION_STATE] Summary: {summary}"
            self.brain.add_document(marker)
            
            # Reset active history
            self.reset()
            print(f"[+] State grounded and saved to Brain. Summary: {summary[:50]}...")
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
    def _build_context(self, user_input, intent, confidence, vector_results, graph_facts, session_mems, web_text, is_code_task, request_mode):
        """Elite V5: Centralized context assembly with precise token budgeting and deduplication."""
        # Reasoning Gateway check (already performed in chat() but kept for stability)
        is_complex = self._is_complex_reasoning(user_input, intent, confidence)
        if is_complex and request_mode == "FAST":
            print("[*] Reasoning Gateway: Complex query detected. Escalating to DEEP mode.")
            request_mode = "DEEP"

        token_limit = config.DEEP_MODE_CONTEXT_TOKENS if request_mode == "DEEP" else config.FAST_MODE_CONTEXT_TOKENS
        
        # 1. System Prompt Priority
        sys_prompt = prompts.FAST_SYSTEM_PROMPT if request_mode == "FAST" else prompts.SYSTEM_PROMPT
        if is_code_task: sys_prompt += "\n" + prompts.EXECUTION_POLICY_CODE
        elif request_mode == "DEEP": sys_prompt += "\n[GUARD] DO NOT generate code blocks or [FILE:] tags."
        
        budget = token_limit - count_tokens(sys_prompt) - 256 # Buffer for generation
        
        # 2. Build User Question (Highest Priority)
        user_q = f"USER QUESTION: {user_input}"
        budget -= count_tokens(user_q)
        
        # 3. Tiered Retrieval Assembly (Grounding First)
        blocks = []
        
        # Grounded Session Memory (Elite V6: Deterministic Spin-Up)
        if session_mems:
            latest_summary = None
            for score, doc in session_mems:
                if "[SESSION_STATE]" in doc:
                    latest_summary = doc.replace("[SESSION_STATE] Summary:", "").strip()
                    break
            
            if latest_summary:
                state_text = f"### PREVIOUS SESSION GROUND TRUTH\n{latest_summary}\n"
                blocks.append(state_text)
                budget -= count_tokens(state_text)

        # Unique Facts (Hard cap to prevent context pollution)
        unique_facts = sorted(list(set(graph_facts)))[:5]
        if unique_facts:
            facts_text = prompts.CONTEXT_FACTS + " | ".join(unique_facts)
            if count_tokens(facts_text) < budget * 0.15:
                blocks.append(facts_text)
                budget -= count_tokens(facts_text)

        # Web Context (Grounded Research)
        if web_text:
            web_block = prompts.CONTEXT_SOURCE_START + web_text[:800] + prompts.CONTEXT_SOURCE_END
            if count_tokens(web_block) < budget * 0.25:
                blocks.append(web_block)
                budget -= count_tokens(web_block)

        # Vector Memories (Semantic History)
        if vector_results:
            top_mem = vector_results[0][1]
            if "[SESSION_STATE]" not in top_mem:
                mem_text = prompts.CONTEXT_PREVIOUS + top_mem
                if count_tokens(mem_text) < budget * 0.15:
                    blocks.append(mem_text)
                    budget -= count_tokens(mem_text)

        # 4. Sliding Window History (Remaining Budget)
        full_user_content = "\n\n".join(blocks) + "\n\n" + user_q
        history = self._get_sliding_history(budget=budget)
        
        messages = [{"role": "system", "content": sys_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": full_user_content})
        
        return messages, count_tokens(full_user_content) + count_tokens(sys_prompt), request_mode
