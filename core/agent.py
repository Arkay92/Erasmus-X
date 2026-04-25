import os
import re
import hashlib
import sys
import ast
import subprocess
import time
import json
from core import config, prompts
from core.compressor import PromptCompressor
from core.sandbox import SandboxManager
from core.local_llm import LocalLLM
from core.template_store import get_best_skeleton
from core.validators.validator_registry import ValidatorRegistry
from core.context_builder import ContextBuilder
from core.session_manager import SessionManager
from core.router import TaskRouter, ExecutionController
from core.contract_builder import CapabilityContract
from core.dependency_graph import DependencyGraph
from core.critic import BuildCritic
from core.failure_learner import FailureLearner
from core.reasoning_engine import ReasoningEngine
from core.prompt_distiller import PromptDistiller
from core.subagent_manager import SubagentManager
from utils.fidelity_scanner import check_fidelity
from utils.brain_sync import sync_project_dir, sync_from_sqlite, sync_from_json
from utils.text_utils import count_tokens, summarize_text_python
from utils.perf import tracker

class NeurosymbolicAgent:
    def __init__(self, client, brain, kg, searcher):
        self.client = client
        self.brain = brain
        self.kg = kg
        self.searcher = searcher
        self.sandbox = SandboxManager(root_dir=config.SANDBOX_ROOT)
        self.compressor = PromptCompressor(self.client) if config.COMPRESSION_ENABLED else None
        
        if config.ENABLE_LOCAL_LLM:
            self.local_llm = LocalLLM(model_name=config.LOCAL_MODEL_TYPE)
            
        self.messages = []
        self._persona_cache = {}
        
        # Elite V12 Subsystems
        self.reasoning_engine = ReasoningEngine(client=self.client, brain=self.brain)
        self.contractor = CapabilityContract(client=self.client)
        self.critic = BuildCritic(client=self.client)
        self.failure_memory = FailureLearner(brain=self.brain)
        
        # Elite V10 Subsystems
        self.context_builder = ContextBuilder(compressor=self.compressor, reasoning_engine=self.reasoning_engine)
        self.session_manager = SessionManager(brain=self.brain, client=self.client)
        self.router = TaskRouter(brain=self.brain, local_llm=self.local_llm)
        self.executor = ExecutionController(client=self.client)
        self.validator = ValidatorRegistry()
        self.prompt_distiller = PromptDistiller(self.local_llm)
        self.subagent_manager = SubagentManager(self)
        
        self._pre_cache_shards()

    def _pre_cache_shards(self):
        shards = self._load_shards_from_disk()
        for s in shards:
            self._persona_cache[s['name']] = s

    def chat(self, user_input, mode_override=None):
        """Elite V10: Orchestrated chat loop using modular subsystems."""
        with tracker.track("TASK_ROUTING"):
            meta = self.router.route(user_input)
        request_mode = mode_override or meta['mode']
        
        # 1. Cache & Stability
        with tracker.track("SEMANTIC_CACHE_LOOKUP"):
            norm_query = re.sub(r'[^\w\s]', '', user_input).lower().strip()
            cache_hit = self.brain.search_cache(norm_query, threshold=config.CACHE_THRESHOLD)
        if cache_hit: return cache_hit['raw'] + "\n[Semantic Cache Hit]", cache_hit['clean']

        with tracker.track("STABILITY_GUARD"):
            if self.session_manager.check_stability_trigger(self.messages):
                self.session_manager.perform_spin_down(self.messages, current_task=user_input)
                self.messages = []

        # 2. Retrieval
        with tracker.track("VECTOR_KNOWLEDGE_RETRIEVAL"):
            vector_results = self.brain.search(user_input, threshold=config.VECTOR_SEARCH_THRESHOLD)
            latest_state = self.session_manager.get_structured_state()
            session_mems = [(1.0, latest_state)] if latest_state else []
            graph_facts = self.kg.get_related_facts(user_input)
            
            web_text = None
            if meta['intent'] == "SEARCH" or (not vector_results and '?' in user_input):
                web_text = self.searcher.search(user_input)

        # 3. Context & Inference
        with tracker.track("CONTEXT_ASSEMBLY"):
            memory_results = {'session': session_mems, 'facts': graph_facts, 'web': web_text}
            
            # Speculative Tuning: Let Gemma 'fine-tune' GPT's instructions for this task
            distilled_tuning = None
            if request_mode != "FAST":
                distilled_tuning = self.prompt_distiller.distill_task_instructions(user_input, meta)
            
            messages, tokens = self.context_builder.build_messages(user_input, self.messages, memory_results, mode=request_mode)
            
            # Inject tuning into the system message (first message)
            if distilled_tuning and messages:
                messages[0]['content'] += distilled_tuning

        print(f"Gemma is thinking ({request_mode} mode)...", flush=True)
        try:
            with tracker.track("LLM_INFERENCE"):
                response = self.client.chat.completions.create(
                    model=config.MODEL_NAME,
                    messages=messages,
                    temperature=0.3 if request_mode == "DEEP" else 0.1,
                    max_tokens=config.DEEP_MODE_OUTPUT_TOKENS if request_mode == "DEEP" else config.FAST_MODE_OUTPUT_TOKENS
                )
                raw_response = response.choices[0].message.content
        except Exception as e:
            print(f"[!] Primary LLM Failed: {e}. Falling back to Local SLM...")
            if hasattr(self, 'local_llm'):
                try:
                    # FAST mode: use short focused prompt to avoid GPT-2 context overflow
                    if request_mode == "FAST":
                        slm_prompt = f"Answer this question concisely: {user_input}"
                    else:
                        # DEEP mode: include recent context but truncated to avoid overflow
                        ctx = "\n".join([m['content'][:200] for m in messages[-3:]])
                        slm_prompt = f"{ctx}\n\nAnswer: "
                    raw_response = self.local_llm.generate(slm_prompt, max_new_tokens=200)
                except Exception as llm_e:
                    print(f"[!] Local LLM generation error: {llm_e}")
                    raw_response = f"I encountered a local model error processing your request."
            else:
                raw_response = "I encountered an error and could not generate a response."
        
        # 4. Verification & Repair
        with tracker.track("CONTRACT_ENFORCEMENT"):
            ok, err = self.executor.enforce_contract(user_input, raw_response, meta)
            if not ok:
                 print(f"[!] Contract Violation: {err}")
                 messages.append({"role": "assistant", "content": raw_response})
                 messages.append({"role": "user", "content": f"RE-PROMPT: {err}"})
                 try:
                     response = self.client.chat.completions.create(model=config.MODEL_NAME, messages=messages, temperature=0.1)
                     raw_response = response.choices[0].message.content
                 except Exception:
                     pass # keep original raw_response if repair fails

        # 5. History & Sync
        if not raw_response or not raw_response.strip():
             print("[!] Language model returned an empty response. Using blank fallback.")
             if hasattr(self, 'local_llm'):
                  try:
                      raw_response = self.local_llm.generate("Answer succinctly: " + user_input, max_new_tokens=128)
                  except Exception as e:
                      raw_response = "I encountered an error and could not generate a response."
             else:
                  raw_response = "I encountered an error and could not generate a response. Please try with deeper context."
                  
        # 5b. SLM Repetition Guard: GPT-2 often generates degenerate loops
        if raw_response:
            lines = [l.strip() for l in raw_response.split('\n') if l.strip()]
            if len(lines) > 3:
                # Check if >60% of lines are duplicates of the first non-empty line
                first_line = lines[0]
                dupes = sum(1 for l in lines if l == first_line)
                if dupes > len(lines) * 0.6:
                    raw_response = first_line  # Collapse to single instance
                    
        clean_ans = re.sub(r'\[FACT\].*', '', raw_response, flags=re.DOTALL).strip()
        if not clean_ans:
             clean_ans = raw_response
             
        self.messages.append({"role": "user", "content": user_input})
        self.messages.append({"role": "assistant", "content": clean_ans})
        self.brain.add_document(f"Context: {user_input}. Summary: {clean_ans}")
        
        if config.ENABLE_REASONING_ENGINE:
             self.reasoning_engine.analyze_task(user_input, messages + [{"role": "assistant", "content": raw_response}], "SUCCESS")
        
        # 6. Multi-Agent Delegation Flow
        if "DELEGATE:" in raw_response:
             print("[*] Orchestrator: Detected delegation request. Spawning subagents...")
             delegations = re.findall(r"DELEGATE:\s*\[([\w\s]+)\]\s*(.*?)(?=DELEGATE:|$)", raw_response, re.DOTALL)
             if delegations:
                  results = self.subagent_manager.delegate_and_collect(delegations)
                  summary = "\n".join([f"SUBAGENT {r} REPORT: {v[:200]}..." for r, v in results.items()])
                  return f"ORCHESTRATOR REPORT: Task decentralized.\n{summary}", "Task decentralized across subagents."

        # 7. Project Flow
        is_project = self._is_project_request(user_input, intent=meta['intent'], confidence=meta['confidence'])
        if is_project:
            project_dir, project_summary = self._project_planning_flow(user_input, messages)
            return self._autonomous_coding_loop(user_input, messages, project_summary, base_dir=project_dir)
        elif meta['is_code']:
            # Single-File Code Task: Direct validate and save (bypass V12 Project Loop)
            saved, failures = self._extract_and_save_files(raw_response)
            status = f"Code Task Complete. Saved: {', '.join(saved) if saved else 'None'}"
            if failures: status += f" | Failures: {len(failures)}"
            return raw_response, status

        return raw_response, clean_ans

    def _project_planning_flow(self, user_input, messages):
        """Elite V10: 11-step project pipeline initialization."""
        print("[*] Project Phase: Planning & Manifesting...")
        with tracker.track("PROJECT_RESEARCH"):
            search_query = f"Architecture and file structure for {user_input}"
            web_ref = self.searcher.search(search_query)
        
        project_name = re.sub(r'[^a-z0-9]', '_', user_input.lower())[:20]
        project_dir = f"v12_{project_name}_{int(time.time())}"
        sandbox_path = self.sandbox.create_sandbox(project_dir)
        
        # Elite V12: Capability Contract Generation
        with tracker.track("CONTRACT_GENERATION"):
            contract = self.contractor.build(user_input)
            with open(os.path.join(sandbox_path, "CONTRACT.json"), "w", encoding="utf-8") as f:
                 json.dump(contract, f, indent=2)
                 
        with tracker.track("PLAN_GENERATION"):
            planner_prompt = prompts.PROJECT_PLANNER_PROMPT + f"\n\nUSER REQUEST: {user_input}"
            planner_prompt += f"\n\n[MANDATORY CONTRACT TARGETS]\nYour plan MUST include these exact files:\n"
            for crit in contract.get('critical_files', []):
                 planner_prompt += f"- {crit}\n"
                 
            if web_ref: planner_prompt += f"\n\nRESEARCH:\n{web_ref[:1000]}"
            
            response = self.client.chat.completions.create(
                model=config.MODEL_NAME,
                messages=[{"role": "system", "content": prompts.SYSTEM_PROMPT}, {"role": "user", "content": planner_prompt}],
                temperature=0.1
            )
            plan_text = response.choices[0].message.content
        
        # Save PLAN.md
        with open(os.path.join(sandbox_path, "PLAN.md"), "w", encoding="utf-8") as f:
            f.write(plan_text)
            
        print(f"[*] Project Planning Complete: {project_dir}")
        return project_dir, plan_text

    def _run_synthesis_loop(self, user_input, history):
        """Uses the Synthesis Prompt to create new shards/packs for future use."""
        print("[*] Phase 13: Engaging Autonomous Capability Synthesis...")
        
        synthesis_prompt = prompts._load_prompt("autonomous_synthesis_prompt.md")
        history_context = "\n".join([f"{m['role'].upper()}: {m['content'][:300]}..." for m in history[-5:]])
        synthesis_prompt = synthesis_prompt.format(history_context=history_context)
        
        try:
            response = self.client.chat.completions.create(
                model=config.MODEL_NAME,
                messages=[{"role": "user", "content": synthesis_prompt}],
                temperature=0.3
            )
            raw = response.choices[0].message.content
            
            if "[SYNTHESIS: SHARD]" in raw or "[SYNTHESIS: TOOL]" in raw or "[SYNTHESIS: PACK]" in raw:
                 name_match = re.search(r"Name:\s*(\w+)", raw)
                 content_match = re.search(r"Content:\s*(.*?)(?=Triggers:|$)", raw, re.DOTALL)
                 if name_match and content_match:
                      name = name_match.group(1).strip()
                      content = content_match.group(1).strip()
                      
                      if "[SYNTHESIS: PACK]" in raw:
                          # Persist as a Brain-based [FEATURE_PACK]
                          try:
                              pack_data = json.loads(content)
                              feature = pack_data.get('feature', name)
                              stack = pack_data.get('stack', 'unknown')
                              doc_text = f"[FEATURE_PACK] FEATURE: {feature} | STACK: {stack} | CONTENT: {content}"
                              self.brain.add_document(doc_text)
                              
                              # Add association
                              triggers = [f"implement {feature}", f"{feature} capability", f"add {feature} logic"]
                              self.brain.add_capability_association(name=feature, cap_type="SHARD", trigger_sentences=triggers)
                              self.brain.save()
                              print(f"[+] Autonomous Synthesis Success: New Feature Pack '{feature}' added to Brain.")
                          except Exception as pe:
                              print(f"[!] Pack Synthesis Parse Error: {pe}")
                      else:
                          # Store as a new shard or tool file
                          target_dir = "shards/core" if "[SYNTHESIS: SHARD]" in raw else "tools"
                          ext = ".md" if "[SYNTHESIS: SHARD]" in raw else ".py"
                          target_path = f"{target_dir}/{name.lower()}{ext}"
                          
                          os.makedirs(target_dir, exist_ok=True)
                          with open(target_path, "w", encoding="utf-8") as f:
                               f.write(content)
                          print(f"[+] Autonomous Synthesis Success: New {ext[1:]} created: {target_path}")
        except Exception as e:
            print(f"[!] Synthesis Error: {e}")

    def _generate_report(self, base_dir, manifest, saved, failures):
        """Generates a blunt, honest report of the build status."""
        total = len(manifest)
        
        # Elite V10.9: Hard Disk Skeleton Verification
        # A template skeleton placeholder is structurally valid but semantically un-implemented.
        # It therefore cannot count towards a SUCCESS build compliance.
        valid_features = []
        scratch_dir = self.sandbox.root_dir if not base_dir else os.path.join(self.sandbox.root_dir, base_dir)
        
        for f in saved:
            fpath = os.path.join(scratch_dir, f)
            try:
                with open(fpath, 'r', encoding='utf-8') as file_data:
                    content = file_data.read()
                    if '[Placeholder Component]' in content or 'Placeholder API' in content or 'export const placeholder = true' in content:
                        failures[f] = "File fell back to a structural placeholder. Feature implementation missing."
                    else:
                        valid_features.append(f)
            except Exception:
                pass
        
        done = len([f for f in valid_features if f in manifest])
        compliance = (done / total * 100) if total > 0 else 0
        
        # Elite V10.4: Strict framework compliance. A partial application is a broken application.
        status = "SUCCESS" if done == total and total > 0 else "CRITICAL FAILURE"
        
        missing_files = [f for f in manifest if f not in saved]
        missing_str = ", ".join(missing_files) if missing_files else "None"
        
        summary_prompt = f"""[REPORT GENERATOR]
Build Status: {status}
Compliance: {compliance:.1f}% ({done}/{total} files)
Files Saved: {', '.join(saved)}
Missing Targets: {missing_str}
Failures: {failures}

Write a 2-para blunt summary. If compliance is low, state explicitly that the scaffold is incomplete and not runnable.
"""
        response = self.client.chat.completions.create(model=config.MODEL_NAME, messages=[{"role": "user", "content": summary_prompt}])
        return f"### PROJECT BUILD REPORT: {base_dir}\n**Status**: {status}\n**Compliance**: {compliance:.1f}%\n**Missing**: {missing_str}\n\n" + response.choices[0].message.content

    def _autonomous_coding_loop(self, user_input, base_messages, initial_response, base_dir=None):
        """Elite V10.4: Layered repair loop with deterministic seeding and strict dependency traversal."""
        attempts = 0
        max_attempts = config.MAX_PROJECT_RETRIES + 5  # Increased runway for complex scaffolds
        current_response = initial_response
        is_nextjs = "next.js" in user_input.lower()
        manifest = self._extract_manifest(initial_response)
        scratch_dir = self.sandbox.root_dir if not base_dir else os.path.join(self.sandbox.root_dir, base_dir)
        
        # Unify Manifest Extensions for Next.js
        if is_nextjs:
            manifest = [f.replace('.js', '.tsx') if f.endswith('.js') else f for f in manifest]
            manifest = [f.replace('.jsx', '.tsx') if f.endswith('.jsx') else f for f in manifest]
            # Framework-aware route normalization
            manifest = [re.sub(r'^(?:app/)?api/(.*)\.tsx?$', r'app/api/\1/route.ts', f) for f in manifest]
        
        persistent_failures = {}
        file_attempts = {}
        forced_files = set()
        
        # Elite V12: Initialize Dependency Graph
        dep_graph = DependencyGraph(manifest)
        contract_path = os.path.join(scratch_dir, "CONTRACT.json")
        contract = {}
        if os.path.exists(contract_path):
             with open(contract_path, 'r', encoding='utf-8') as cf:
                  contract = json.load(cf)
        
        critic_pass_count = 0
        rejection_history = {} # File -> List of reasons
        is_authoritative_flush = False
        last_project_hash = None
        
        # Elite V17: Align Manifest with Capability Contract
        critical_files = contract.get('critical_files', [])
        if not critical_files:
             critical_files = contract.get('specs', {}).get('critical_files', [])
             
        if critical_files:
             print(f"[*] Contract Alignment: Synchronizing {len(critical_files)} critical targets.")
             for cf in critical_files:
                  cf_norm = cf.replace('\\', '/').lstrip('./')
                  if cf_norm not in manifest and cf_norm.lower() not in ['plan.md', 'contract.json']:
                       print(f"    [+] Adding mandatory file: {cf_norm}")
                       manifest.append(cf_norm)
        
        print(f"[*] V12 Build Stage: FOUNDATION ({len(manifest)} targets identified)")
        
        while attempts < max_attempts:
            with tracker.track(f"CODING_LOOP_ITERATION_{attempts}"):
                saved_files, current_failures = self._extract_and_save_files(current_response, base_dir=base_dir, manifest=manifest)
                
                # Update state
                for sf in saved_files:
                    if sf in persistent_failures: del persistent_failures[sf]
                    # V12: Update Dependency Graph
                    fpath = os.path.join(scratch_dir, sf)
                    with open(fpath, 'r', encoding='utf-8') as f_read:
                         code = f_read.read()
                         dep_graph.update_file(sf, code)
                         # Elite V17: Induced Dependencies from generated code
                         new_induced = self._induce_missing_dependencies(code, manifest, dep_graph)
                         if new_induced:
                              current_response += f"\n\n[DEPENDENCY INDUCTION]\nDetected missing local imports. Adding: {', '.join(new_induced)}"
                
            for f, err in current_failures.items():
                persistent_failures[f] = err
            for f in list(persistent_failures.keys()):
                if f in forced_files: del persistent_failures[f]
            
            # V12 Status
            graph_status = dep_graph.get_progressive_status()
            print(f"[*] V12 Progress: {graph_status} | {len(persistent_failures)} errors")
            
            # Step 1: Check completeness from disk
            actual_saved = []
            for f in manifest:
                if os.path.exists(os.path.join(scratch_dir, f)):
                    actual_saved.append(f)
                    
            missing = [f for f in manifest if f not in actual_saved and f != "PLAN.md"]
            if not missing and not persistent_failures:
                # Elite V13.0: High-Fidelity Build Critic
                critic_pass_count += 1
                print(f"[+] Manifest satisfied. Escalating to V13 Build Critic (Pass {critic_pass_count})...")
                
                # V12: Build file map for Critic
                file_map = {}
                project_content_blob = ""
                for f in actual_saved:
                     f_path = os.path.join(scratch_dir, f)
                     if os.path.exists(f_path):
                         with open(f_path, 'r', encoding='utf-8') as f_read:
                              content = f_read.read()
                              file_map[f] = content
                              project_content_blob += content

                # Elite V19: Stall Detection
                current_hash = hashlib.md5(project_content_blob.encode()).hexdigest()
                if current_hash == last_project_hash:
                     print("[!] Project State Stall Detected (No meaningful delta). Terminating build loop.")
                     break
                last_project_hash = current_hash

                with tracker.track("CRITIC_EVALUATION"):
                    # Fast-fail structural drift before expensive critic
                    fid_score, fid_targets = check_fidelity(contract, file_map)
                    if fid_targets:
                         print(f"[!] Fidelity Scanner found {len(fid_targets)} structural/stack violations. Skipping LLM Critic.")
                         critic_report = "SCORE: 70\n[REPAIR: JSON]\n" + json.dumps({"targets": fid_targets}) + "\n[/REPAIR]"
                    else:
                         critic_report = self.critic.evaluate(user_input, contract, file_map)
                
                if "SCORE: 100" in critic_report:
                     print("[+] Build Complete: V13 Critic PASS (Score: 100)")
                     if config.ENABLE_REASONING_ENGINE:
                          with tracker.track("REASONING_ANALYSIS"):
                               self.reasoning_engine.analyze_task(user_input, base_messages + [{"role": "assistant", "content": current_response}], "SUCCESS", critic_report)
                     return current_response, re.sub(r'\[FACT\].*', '', current_response).strip()
                else:
                     print(f"[!] V13 Critic Rejection: Logic depth or correctness issues found.")
                     # Record failure for learning
                     with tracker.track("REASONING_ANALYSIS"):
                          self.failure_memory.record_failure(contract.get('stack', 'unknown'), user_input, persistent_failures, critic_report)
                     
                     # Elite V13: Extract JSON-defined repair targets
                     rejection_targets = []
                     critic_notes = {}
                     
                     repair_match = re.search(r"\[REPAIR: JSON\]\s*(.*?)\s*\[/REPAIR\]", critic_report, re.DOTALL | re.IGNORECASE)
                     if repair_match:
                          try:
                                repair_data = json.loads(repair_match.group(1))
                                for t in repair_data.get('targets', []):
                                     fname = t['file'].replace('\\', '/').lstrip('./')
                                     rejection_targets.append(fname)
                                     critic_notes[fname] = t['reason']
                          except Exception as e:
                               print(f"[!] Critic JSON parse error: {e}")
                     
                     # Fallback to regex if JSON fails
                     if not rejection_targets:
                          rejection_targets = re.findall(r"[`']?([\w\.\/\-\[\]@]+\.\w+)[`']?", critic_report)
                          rejection_targets = [p.replace('\\', '/').lstrip('./') for p in rejection_targets if p in actual_saved]
                          if rejection_targets:
                               print(f"[*] V14 Feature Induction: Critic requested {len(rejection_targets)} files.")
                          else:
                               # Elite V18: Fidelity Recovery Fallback
                               print("[!] Critic rejected build but provided no specific file targets. Engaging Fidelity Scanner...")
                               # Build file map for scanner
                               f_map = {}
                               for f_name in actual_saved:
                                    p = os.path.join(scratch_dir, f_name)
                                    if os.path.exists(p):
                                         with open(p, 'r', encoding='utf-8') as f_r: f_map[f_name] = f_r.read()
                               
                               with tracker.track("FIDELITY_SCAN"):
                                    fid_score, fid_targets = check_fidelity(contract, f_map)
                               if fid_targets:
                                    print(f"[+] Fidelity Recovery: Identified {len(fid_targets)} missing or drifting files.")
                                    for ft in fid_targets:
                                         fname = ft['file']
                                         rejection_targets.append(fname)
                                         critic_notes[fname] = ft['reason']
                               else:
                                    print("[!] Fidelity Scan passed but Critic still rejected. Declaring closure failure.")
                                    return current_response, self._generate_report(base_dir, manifest, actual_saved, {"critic": critic_report})
                     
                     if rejection_targets:
                          induced_new = []
                          for rt in rejection_targets:
                               if rt not in manifest:
                                    manifest.append(rt)
                                    induced_new.append(rt)
                               
                               if rt in actual_saved: actual_saved.remove(rt)
                               if rt in persistent_failures: del persistent_failures[rt]
                               
                               # Track rejection history
                               reason = critic_notes.get(rt, "Logic depth insufficient. Implement deeper implementation.")
                               if rt not in rejection_history: rejection_history[rt] = []
                               rejection_history[rt].append(reason)
                               
                               # Inject reason into persistent failures
                               persistent_failures[rt] = f"CRITIC REJECTION ({len(rejection_history[rt])}): {reason}"
                          
                          if induced_new:
                               print(f"[+] Induced new structural targets: {induced_new}")
                               current_response += f"\n\n[FEATURE INDUCTION]\nCritic identified missing features: {', '.join(induced_new)}"
                          
                          # Elite V19: Absolute Critic Stop
                          if critic_pass_count > config.MAX_CRITIC_CYCLES:
                               print(f"[!] HARD LIMIT: Exiting after {critic_pass_count} critic cycles.")
                               return current_response, self._generate_report(base_dir, manifest, actual_saved, {"critic": "Hard Limit Reached"})

                          # Elite V18: Aggressive Runway Extension
                          # Ensure we have at least 5 more trials if new targets are found
                          if max_attempts - attempts < 5 and not is_authoritative_flush:
                               max_attempts = attempts + 5
                               print(f"[*] Runway Extended to {max_attempts} attempts for fidelity repair.")
                                
                          # Elite V17: Hard Critic Cap
                          if critic_pass_count >= config.MAX_CRITIC_CYCLES:
                               print(f"[!] MAX CRITIC CYCLES ({config.MAX_CRITIC_CYCLES}) REACHED. Engaging Authoritative Flush.")
                               is_authoritative_flush = True
                          else:
                               missing = [f for f in rejection_targets if f not in actual_saved]
                               # Cap runway growth
                               increase = len(rejection_targets) * 2
                               if max_attempts < 30: # Hard cap on runway
                                    max_attempts += min(increase, 10)
                          
                          current_response += f"\n\n[CRITIC REJECTION]\n{critic_report}"
                          attempts += 1
                          continue
                     else:
                          print("[!] Critic rejected build but provided no specific file targets. Declaring failure.")
                          return current_response, self._generate_report(base_dir, manifest, actual_saved, {"critic": critic_report})

            # Step 2: Surgical Repair
            attempts += 1
            print(f"[*] Build Attempt {attempts}/{max_attempts}: {len(missing)} missing, {len(persistent_failures)} invalid.")
            
            target_f = missing[0] if missing else list(persistent_failures.keys())[0]
            file_attempts[target_f] = file_attempts.get(target_f, 0) + 1
            
            # Elite V15: High-Precision Feature Pack Lookup
            skeleton = get_best_skeleton(target_f, brain=self.brain, stack_context=str(contract).lower())
            
            # Step 3: Authoritative Escalation (Elite V17 Hardening)
            # FORCE logic injection if:
            # 1. Authoritative flush is active (critic cap hit)
            # 2. File has failed multiple times (logic stall)
            # 3. File has been rejected by critic multiple times (depth stall)
            rejection_count = len(rejection_history.get(target_f, []))
            
            if (is_authoritative_flush or file_attempts[target_f] >= 2 or rejection_count >= 2) and skeleton:
                spath = os.path.join(scratch_dir, target_f)
                reason = "Flush" if is_authoritative_flush else ("Failure" if file_attempts[target_f] >= 2 else "Rejection")
                print(f"[!] Authoritative Logic Injection ({reason}): Forcing deep implementation for {target_f}")
                os.makedirs(os.path.dirname(spath), exist_ok=True)
                with open(spath, "w", encoding="utf-8") as f_force:
                    f_force.write(skeleton['content'])
                forced_files.add(target_f)
                
                # Elite V17: Induced Dependencies from forced skeleton
                new_induced = self._induce_missing_dependencies(skeleton['content'], manifest, dep_graph)
                
                # Advance loop explicitly to avoid stalling
                msg = f"[SYSTEM] Authoritative scaffold forced for {target_f} to break {reason} loop."
                if new_induced:
                     msg += f" Induced dependencies: {', '.join(new_induced)}"
                current_response = msg
                
                # Remove from failures to prevent re-repairing in same turn if manifest was huge
                if target_f in persistent_failures: del persistent_failures[target_f]
                continue
            
            repair_prompt = f"[SURGICAL REPAIR: LOGIC DEPTH V17] File: {target_f}\n"
            if target_f in persistent_failures: 
                # Limit failure reason length
                reason = persistent_failures[target_f][:300]
                repair_prompt += f"FAILURE: {reason}\n"
            
            if critic_pass_count >= 1:
                # Elite V17: Strict Context Budgeting (Limit Report)
                report_slice = critic_report[:config.CRITIC_REPORT_LIMIT]
                repair_prompt += f"CRITIC FEEDBACK: {report_slice}\n"
            
            if skeleton: 
                # Only include skeleton if it's the first attempt or failed multiple times
                if file_attempts[target_f] == 1 or file_attempts[target_f] > 2:
                     repair_prompt += f"SEED:\n```tsx\n{skeleton['content'][:800]}\n```\n"
            
            repair_prompt += "Implement FULL corrected code in [FILE: name] block. PRODUCTION DEPTH ONLY."
            
            messages = list(base_messages)
            # Elite V17: Shrink initial plan to save context
            plan_summary = initial_response[:400] + "..." if len(initial_response) > 500 else initial_response
            
            messages.append({"role": "system", "content": "You are in LOGIC DEPTH mode. Write complete code blocks."})
            messages.append({"role": "assistant", "content": f"PLAN SUMMARY:\n{plan_summary}\n\n[MANIFEST: {', '.join(manifest[:15])}]"})
            messages.append({"role": "user", "content": repair_prompt})
            
            response = self.client.chat.completions.create(model=config.MODEL_NAME, messages=messages, temperature=0.1)
            current_response = response.choices[0].message.content
            
        # Elite V12: Final Output & Ultimate Critic Gate
        actual_saved = [f for f in manifest if os.path.exists(os.path.join(scratch_dir, f))]
        file_map = {}
        for f in actual_saved:
             f_path = os.path.join(scratch_dir, f)
             if os.path.exists(f_path):
                 with open(f_path, 'r', encoding='utf-8') as f_read:
                      file_map[f] = f_read.read()
        
        critic_report = self.critic.evaluate(user_input, contract, file_map)
        print(f"[*] V12 Final Critic Evaluation: {critic_report.splitlines()[0] if critic_report else 'SCORE: 0'}")
        
        # Persist failure if low score
        if "SCORE: 100" not in critic_report:
             self.failure_memory.record_failure(contract.get('stack', 'unknown'), user_input, persistent_failures, critic_report)
             if config.ENABLE_REASONING_ENGINE:
                  self.reasoning_engine.analyze_task(user_input, base_messages + [{"role": "assistant", "content": current_response}], "FAILURE", critic_report)
        
        # Final output persistence: Guarantee the last generated file lands on disk
        self._extract_and_save_files(current_response, base_dir=base_dir, manifest=manifest)
        
        # Phase 13: Autonomous Synthesis - Create new packs/skills on the fly
        if "SCORE: 100" in critic_report and config.ENABLE_AUTONOMOUS_SYNTHESIS:
             self._run_synthesis_loop(user_input, base_messages + [{"role": "assistant", "content": current_response}])

        report = self._generate_report(base_dir, manifest, actual_saved, persistent_failures)
        return current_response, report

    def _extract_and_save_files(self, text, base_dir=None, manifest=None):
        """V10 Modular Extraction."""
        file_markers = list(re.finditer(r"\[FILE:\s*((?:\[[^\]]*\]|[^\]])+)\]", text))
        scratch_dir = self.sandbox.root_dir if not base_dir else os.path.join(self.sandbox.root_dir, base_dir)
        os.makedirs(scratch_dir, exist_ok=True)
        
        saved, failures = [], {}
        available = set(manifest) if manifest else set()
        is_nextjs = any("app/" in f for f in available) or (manifest and any(".tsx" in f for f in manifest))
        
        for i, marker in enumerate(file_markers):
            filename = marker.group(1).strip()
            
            # Extension Policy Enforcement
            if is_nextjs:
                if filename.endswith('.js'): filename = filename.replace('.js', '.tsx')
                if filename.endswith('.jsx'): filename = filename.replace('.jsx', '.tsx')
            start = marker.end()
            end = file_markers[i+1].start() if i+1 < len(file_markers) else len(text)
            block = re.search(r"```[a-z]*\n(.+?)(?:\n?```|$)", text[start:end], re.DOTALL)
            if block:
                code = block.group(1).strip()
                # Completion Check: Minimal balanced brace/parentheses check for code blocks
                if code.count('{') > code.count('}') or code.count('(') > code.count(')'):
                    failures[filename] = "Truncated code block missing closing markers."
                    continue
                
                # Elite V17: Zero-Tolerance Placeholder Detection
                # Catch hollow scaffolds before they touch the disk
                placeholders = ['[Placeholder Component]', 'Placeholder API', 'export const placeholder = true', 'Return Placeholder', 'TODO: implement']
                if any(p.lower() in code.lower() for p in placeholders):
                     failures[filename] = f"Rejected: Authoritative logic missing. Detected placeholder signal: {placeholders[0]}..."
                     continue
            else:
                skeleton = get_best_skeleton(filename, brain=self.brain)
                if skeleton: code = skeleton['content']
                else: failures[filename] = "No code"; continue

            ok, err = self.validator.validate(filename, code, {'available_files': available})
            if not ok: failures[filename] = err; continue

            fpath = os.path.join(scratch_dir, filename)
            
            # Phase 10: Authoritative Path Safety Guard
            if os.path.isdir(fpath):
                print(f"[!] Path Safety violation: {filename} matches an existing directory. Skipping.")
                failures[filename] = "Path collision with existing directory"
                continue

            os.makedirs(os.path.dirname(fpath), exist_ok=True)
            try:
                with open(fpath, "w", encoding="utf-8") as f: f.write(code)
                saved.append(filename); available.add(filename)
                print(f"Saved validated {filename}")
            except Exception as e:
                print(f"[!] Save FAILED for {filename}: {str(e)}")
                failures[filename] = str(e)
            
        return saved, failures

    def _is_project_request(self, text, intent=None, confidence=0):
        if intent == "PROJECT" and confidence > 0.35: return True
        return any(k in text.lower() for k in ['project', 'system', 'application', 'multiple files']) and len(text.split()) > 5

    def _induce_missing_dependencies(self, code, manifest, dep_graph):
        """Elite V17: Automatically adds missing imported files to the manifest."""
        missing = dep_graph.find_unresolved_imports(code)
        induced = []
        for m in missing:
            if m not in manifest:
                manifest.append(m)
                dep_graph.manifest.add(m)
                induced.append(m)
        if induced:
            print(f"[+] Dependency Induction: Added {len(induced)} missing targets ({', '.join(induced)})")
        return induced

    def _extract_manifest(self, plan_text):
        """Hardened V10.3: Path-aware and framework-shielded parsing."""
        raw_paths = re.findall(r"[`']?([\w\.\/\-\[\]@]+\.\w+)[`']?", plan_text)
        valid_exts = {'.py', '.js', '.tsx', '.jsx', '.css', '.html', '.json', '.md', '.sql', '.yml', '.yaml', '.toml'}
        framework_labels = {'next-js', 'nextjs', 'frontend', 'backend', 'database', 'sqlite', 'react', 'next.js'}
        root_allowlist = {'package.json', 'requirements.txt', 'dockerfile', 'docker-compose.yml', 'tsconfig.json'}
        
        manifest = []
        for p in raw_paths:
            p_norm = p.replace('\\', '/').lstrip('./')
            ext = os.path.splitext(p_norm)[1].lower()
            name = os.path.basename(p_norm).lower()
            
            # Junk Filter: Next.js often emits 'Next.js' as a 'file'
            if p_norm.lower() in framework_labels: continue
            
            # Root Requirement: Files must have a slash OR be in the root allowlist
            has_slash = '/' in p_norm
            is_root_file = name in root_allowlist
            
            if ext in valid_exts and (has_slash or is_root_file):
                if p_norm not in manifest and p_norm.lower() not in ['plan.md', 'readme.md', 'manifest.md']:
                    manifest.append(p_norm)
        
        print(f"[*] Manifest Audit: {len(manifest)} valid files identified.")
        if manifest: print(f"    Target List: {', '.join(manifest[:5])}...")
        return manifest

    def _load_shards_from_disk(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        shards = []
        for cat in ['agents', 'skills']:
            path = os.path.join(root, 'shards', cat)
            if not os.path.exists(path): continue
            for f in os.listdir(path):
                if f.endswith('.md'):
                    with open(os.path.join(path, f), 'r', encoding='utf-8') as sf:
                        shards.append({'name': f.replace('.md', ''), 'content': sf.read(), 'category': cat})
        return shards
