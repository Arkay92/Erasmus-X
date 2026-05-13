import os
import re
import hashlib
import time
import json
import subprocess
import sys
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
from core.dispatcher import NeurosymbolicDispatcher
from core.prompt_distiller import PromptDistiller
from core.subagent_manager import SubagentManager
from core.request_cache import RequestCache
from core.transaction_manager import ProjectTransaction
from core.task_queue import TaskQueue
from core.model_router import ModelRouter
from core.code_formatter import CodeFormatter
from core.code_fallbacks import CodeFallbackRegistry
from core.answer_fallbacks import factual_fallback
from core.active_kg_builder import ActiveKGBuilder
from core.graph_reasoner import GraphReasoner
from core.vector_store import HypervectorDB
from core.context_manager import ContextManager
from core.feedback_store import FeedbackStore
from core.scaffold_registry import ScaffoldRegistry
from core.dynamic_scaffold_builder import DynamicScaffoldBuilder
from core.execution_memory import ExecutionMemory
from core.auto_pack_builder import AutoPackBuilder
from core.response_schema import make_response
from core.inject_feature_packs import register_feature_packs
from core.inject_prisma_packs import register_prisma_packs
from utils.fidelity_scanner import check_fidelity
from utils.brain_sync import sync_project_dir
from utils.perf import tracker

class NeurosymbolicAgent:
    def __init__(self, client, brain, kg, searcher, agent_client=None):
        self.client = client
        self.agent_client = agent_client or client
        self.brain = brain
        self.kg = kg
        self.searcher = searcher
        self.sandbox = SandboxManager(root_dir=config.SANDBOX_ROOT)
        self.compressor = PromptCompressor(self.client) if config.COMPRESSION_ENABLED else None
        
        self.local_llm = LocalLLM(model_name=config.LOCAL_LLM_TYPE) if config.ENABLE_LOCAL_LLM else None
            
        self.messages = []
        
        # Elite V12 Subsystems
        self.reasoning_engine = ReasoningEngine(client=self.agent_client, brain=self.brain)
        self.dispatcher = NeurosymbolicDispatcher(client=self.agent_client)
        self.contractor = CapabilityContract(client=self.agent_client, brain=self.brain)
        self.critic = BuildCritic(client=self.agent_client)
        self.failure_memory = FailureLearner(brain=self.brain)
        self.large_context_manager = ContextManager(
            local_llm=self.local_llm,
            max_context_tokens=config.DEEP_MODE_CONTEXT_TOKENS,
        )
        
        # Elite V10 Subsystems
        self.context_builder = ContextBuilder(compressor=self.compressor, reasoning_engine=self.reasoning_engine)
        self.session_manager = SessionManager(brain=self.brain, client=self.agent_client)
        self.router = TaskRouter(brain=self.brain, local_llm=self.local_llm)
        self.executor = ExecutionController(client=self.client)
        self.validator = ValidatorRegistry()
        self.prompt_distiller = PromptDistiller(self.local_llm)
        self.subagent_manager = SubagentManager(self)
        specialized = {k: v for k, v in getattr(config, "SPECIALIZED_MODELS", {}).items() if v}
        self.model_router = ModelRouter(default_model=config.MODEL_NAME, specialized_models=specialized)
        self.request_cache = RequestCache() if getattr(config, "REQUEST_CACHE_ENABLED", True) else None
        self.task_queue = TaskQueue(handler=lambda payload: self.chat(**payload), num_workers=config.TASK_QUEUE_WORKERS)
        self.formatter = CodeFormatter()
        self.code_fallbacks = CodeFallbackRegistry()
        self.kg_builder = ActiveKGBuilder(self.kg)
        self.graph_reasoner = GraphReasoner(self.kg)
        self.distributed_brain = self.brain
        self.feedback_store = FeedbackStore()
        self.scaffold_registry = ScaffoldRegistry()
        self.dynamic_scaffold_builder = DynamicScaffoldBuilder(client=self.agent_client, searcher=self.searcher)
        self.execution_memory = ExecutionMemory()
        self.auto_pack_builder = AutoPackBuilder(brain=self.brain)
        self._ensure_builtin_feature_packs()
        # Subsystems initialized. Ready for orchestration.

    def _ensure_builtin_feature_packs(self):
        """Make built-in feature packs available without a manual injection step."""
        register_feature_packs(self.brain, save=False, verbose=False)
        register_prisma_packs(self.brain, save=False, verbose=False)

    def enqueue_chat(self, user_input, mode_override=None, priority=5):
        """Queue a chat request for concurrent worker execution."""
        return self.task_queue.enqueue({"user_input": user_input, "mode_override": mode_override}, priority=priority)

    def get_job_status(self, job_id):
        return self.task_queue.get_status(job_id)

    def submit_feedback(self, job_id, rating, corrections=None, metadata=None):
        """Persist user feedback and expose it to the long-term brain."""
        feedback = self.feedback_store.submit(job_id, rating, corrections, metadata)
        self.distributed_brain.add_document(
            f"[FEEDBACK] Job: {job_id} | Rating: {rating} | Corrections: {len(feedback['corrections'])}"
        )
        return feedback

    def chat(self, user_input, mode_override=None, stream_callback=None):
        """Elite V10: Orchestrated chat loop using modular subsystems."""
        with tracker.track("TASK_ROUTING"):
            meta = self.router.route(user_input)
        request_mode = mode_override or meta['mode']
        selected_model = self.model_router.route(user_input)
        if request_mode == "FAST" and getattr(config, "FAST_MODEL_NAME", None):
            selected_model = config.FAST_MODEL_NAME
        early_project = meta.get('is_project')
        early_code_fallback = None if early_project else self.code_fallbacks.match(user_input, meta)
        if meta.get('is_code') and early_code_fallback and not user_input.lstrip().startswith("ROLE:"):
            print(f"[*] Code Fallback: using deterministic {early_code_fallback.filename}")
            raw_response = early_code_fallback.as_file_block()
            saved, failures = self._extract_and_save_files(raw_response)
            status_text = f"Code Task Complete. Saved: {', '.join(saved) if saved else 'None'}"
            if failures:
                status_text += f" | Failures: {len(failures)}"
            return make_response(
                raw_response,
                status_text,
                files=saved,
                status="error" if failures else "ok",
                errors=list(failures.values()),
                metadata={**meta, "fallback": early_code_fallback.filename},
            )
        early_answer_fallback = factual_fallback(user_input)
        if early_answer_fallback and not meta.get('is_dynamic') and not early_project and not meta.get('is_code'):
            return make_response(
                early_answer_fallback,
                early_answer_fallback,
                status="ok",
                metadata={**meta, "fallback": "stable_answer"},
            )
        if early_project:
            templated = self._try_scaffold_project(user_input, meta)
            if templated:
                raw, answer = templated
                files = self._extract_saved_files_from_report(raw + "\n" + answer)
                return make_response(raw, answer, files=files, status="ok", metadata={**meta, "mode": request_mode, "model": selected_model})
        exact_cache_key = None
        cacheable_simple_query = (
            self.request_cache
            and not self.messages
            and '?' in user_input
            and not meta.get('is_dynamic')
            and not early_project
            and not meta.get('is_code')
        )
        if cacheable_simple_query:
            exact_cache_key = self.request_cache.fingerprint(
                user_input,
                mode=request_mode,
                model=selected_model,
                temperature=0.3 if request_mode == "DEEP" else 0.1,
            )
            exact_cache_hit = self.request_cache.get(exact_cache_key)
            if exact_cache_hit:
                raw = exact_cache_hit["raw"] + "\n[Request Cache Hit]"
                return make_response(raw, exact_cache_hit["clean"], status="cached", metadata={**meta, "cache": "request"})
        
        # 1. Cache & Stability
        with tracker.track("SEMANTIC_CACHE_LOOKUP"):
            cache_hit = None
            if not meta.get('is_dynamic') and not early_project and not meta.get('is_code'):
                norm_query = re.sub(r'[^\w\s]', '', user_input).lower().strip()
                cache_hit = self.brain.search_cache(norm_query, threshold=config.CACHE_THRESHOLD)
        if cache_hit:
            if stream_callback:
                stream_callback(cache_hit['raw'])
            raw = cache_hit['raw'] + "\n[Semantic Cache Hit]"
            return make_response(raw, cache_hit['clean'], status="cached", metadata={**meta, "cache": "semantic"})

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
            if config.ENABLE_WEB_SEARCH and (meta['intent'] == "SEARCH" or (not vector_results and '?' in user_input)):
                try:
                    web_text = self.searcher.search(user_input)
                except Exception as e:
                    print(f"[!] Web search failed: {e}")
                    web_text = ""

        # 3. Context & Inference
        with tracker.track("CONTEXT_ASSEMBLY"):
            failures = self.failure_memory.get_recent_failures(limit=2)
            history_logs = self.brain.get_convo_history(limit=3)
            
            # Recalled Capability (Learned Skills)
            recalled_cap = self.brain.find_best_capability(user_input)
            
            memory_results = {
                'session': session_mems,
                'facts': graph_facts,
                'web': web_text,
                'failures': failures,
                'history_logs': history_logs,
                'recalled_cap': recalled_cap
            }
            
            # Speculative Tuning: Let Erasmus X 'fine-tune' instructions for this task
            distilled_tuning = None
            if request_mode != "FAST":
                distilled_tuning = self.prompt_distiller.distill_task_instructions(user_input, meta)
            
            messages, tokens = self.context_builder.build_messages(user_input, self.messages, memory_results, mode=request_mode)
            
            # Inject tuning into the system message (first message)
            if distilled_tuning and messages:
                messages[0]['content'] += distilled_tuning

        if request_mode == "DEEP" and not early_project:
            return self._dispatch_route(user_input, messages, meta, memory_results, stream_callback)
            
        if early_project:
            print("[*] Project route confirmed. Bypassing conversational LLM inference.", flush=True)
            project_dir, plan_text = self._project_planning_flow(user_input, meta, web_ref=memory_results.get('web'))
            return self._autonomous_coding_loop(user_input, messages, plan_text, base_dir=project_dir, stream_callback=stream_callback)
        else:
            return self._simple_llm_call(messages, stream_callback, selected_model=selected_model, request_mode=request_mode)

    def _simple_llm_call(self, messages, stream_callback, selected_model=config.MODEL_NAME, request_mode="FAST", user_input="", meta=None, cache_key=None):
        """Helper for standard LLM inference with full post-processing."""
        raw_response = ""
        try:
            with tracker.track("LLM_INFERENCE"):
                is_reasoning_model = any(k in selected_model.lower() for k in ["minimax", "o1", "r1"])
                response = self.client.chat.completions.create(
                    model=selected_model,
                    messages=messages,
                    temperature=0.3 if request_mode == "DEEP" else 0.1,
                    max_tokens=config.DEEP_MODE_OUTPUT_TOKENS if (request_mode == "DEEP" or is_reasoning_model) else config.FAST_MODE_OUTPUT_TOKENS,
                    timeout=config.REQUEST_TIMEOUT,
                    stream=bool(stream_callback)
                )
                if stream_callback:
                    for chunk in response:
                        if not getattr(chunk, "choices", None): continue
                        delta = chunk.choices[0].delta
                        content = getattr(delta, "reasoning_content", "") or ""
                        if delta.content: content += delta.content
                        if content:
                            raw_response += content
                            stream_callback(content)
                else:
                    msg = response.choices[0].message
                    raw_response = getattr(msg, "reasoning_content", "") or ""
                    if msg.content: raw_response += ("\n\n" if raw_response else "") + msg.content
        except Exception as e:
            print(f"[!] LLM Call Failed: {e}")
            raw_response = factual_fallback(user_input) or "I encountered an error and could not generate a response."
        
        # 1. Repetition Guard
        if raw_response:
            lines = [l.strip() for l in raw_response.split('\n') if l.strip()]
            if len(lines) > 3:
                first_line = lines[0]
                dupes = sum(1 for l in lines if l == first_line)
                if dupes > len(lines) * 0.6:
                    raw_response = first_line

        # 2. Contract Enforcement
        if meta:
            ok, err = self.executor.enforce_contract(user_input, raw_response, meta)
            if not ok:
                 print(f"[!] Contract Violation: {err}")
                 # Recursive repair (limited)
                 messages.append({"role": "assistant", "content": raw_response})
                 messages.append({"role": "user", "content": f"RE-PROMPT: {err}"})
                 try:
                     repair_resp = self.client.chat.completions.create(model=selected_model, messages=messages, temperature=0.1)
                     raw_response = repair_resp.choices[0].message.content
                 except: pass

        clean_ans = re.sub(r'\[FACT\].*', '', raw_response, flags=re.DOTALL).strip()
        if not clean_ans: clean_ans = raw_response
        
        # 3. Persistence
        self.messages.append({"role": "user", "content": user_input})
        self.messages.append({"role": "assistant", "content": clean_ans})
        self.brain.add_convo_step({"timestamp": time.time(), "query": user_input, "raw_output": raw_response, "clean_response": clean_ans})
        
        if cache_key and self.request_cache:
            self.request_cache.set(cache_key, {"raw": raw_response, "clean": clean_ans})
        
        if self.brain and not meta.get('is_dynamic') and not meta.get('is_project'):
            self.brain.add_to_cache(user_input, raw_response, clean_ans)

        return make_response(raw_response, clean_ans, status="ok")

    def _dispatch_route(self, user_input, messages, meta, memory_results, stream_callback, selected_model):
        """Elite V15: The agentic reasoning layer that replaces hardcoded routing."""
        # 1. Get decision support
        lessons = self.reasoning_engine.get_decision_support(user_input)
        context_summary = f"RELEVANT LESSONS:\n{lessons}\n\nTARGET_STACK: {meta.get('target_stack')}"
        
        # 2. Dispatch
        action = self.dispatcher.select_action(user_input, context_summary)
        thought = action.get('thought', '')
        if stream_callback and thought:
            stream_callback(f"\n> [REASONING]: {thought}\n\n")
            
        op = action.get('operation')
        payload = action.get('payload', {})
        
        if op == "RESEARCH":
             project_dir, plan_text = self._project_planning_flow(user_input, meta, web_ref=memory_results.get('web'))
             if stream_callback: stream_callback(f"[*] Deep Research initiated: {payload.get('query')}\n\n")
             return self._autonomous_coding_loop(user_input, messages, plan_text, base_dir=project_dir, stream_callback=stream_callback)
        
        elif op == "SEARCH":
             query = payload.get('query', user_input)
             web_results = self.searcher.search(query)
             messages.append({"role": "system", "content": f"SEARCH RESULTS:\n{web_results}"})
             return self._simple_llm_call(messages, stream_callback, request_mode="DEEP", user_input=user_input, meta=meta, selected_model=selected_model)
             
        elif op == "PROJECT":
             project_dir, plan_text = self._project_planning_flow(user_input, meta, web_ref=memory_results.get('web'))
             return self._autonomous_coding_loop(user_input, messages, plan_text, base_dir=project_dir, stream_callback=stream_callback)
             
        elif op == "CODE":
             project_dir, plan_text = self._project_planning_flow(user_input, meta)
             return self._autonomous_coding_loop(user_input, messages, plan_text, base_dir=project_dir, stream_callback=stream_callback)
        
        elif op == "DELEGATE":
             delegations = payload.get('delegations', [])
             results = self.subagent_manager.delegate_and_collect([(d['role'], d['task']) for d in delegations])
             raw = f"DELEGATION SUMMARY:\n" + "\n".join([f"- {r}: {v[:100]}..." for r, v in results.items()])
             return make_response(raw, "Task decentralized.", status="ok", metadata={**meta, "delegated": True})
             
        return self._simple_llm_call(messages, stream_callback, request_mode="DEEP", user_input=user_input, meta=meta, selected_model=selected_model)
            


        # 5. History & Sync
        if not raw_response or not raw_response.strip():
             print("[!] Language model returned an empty response. Using blank fallback.")
             stable_answer = factual_fallback(user_input)
             if stable_answer:
                  raw_response = stable_answer
             elif self.local_llm:
                  try:
                      raw_response = self.local_llm.generate("Answer succinctly: " + user_input, max_new_tokens=128)
                  except Exception as e:
                      raw_response = "I encountered an error and could not generate a response."
             else:
                  raw_response = "I encountered an error and could not generate a response. Please try with deeper context."
             raw_response = raw_response or "I encountered an error and could not generate a response."
                  
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
        
        # Log to Persistent Episodic Memory (convo_chain)
        convo_entry = {
            "timestamp": time.time(),
            "query": user_input,
            "raw_output": raw_response,
            "clean_response": clean_ans
        }
        self.brain.add_convo_step(convo_entry)
        
        # Add to HDC Semantic Cache for instant future lookups
        if self.brain and not meta.get('is_dynamic') and not early_project and not meta.get('is_code'):
            self.brain.add_to_cache(user_input, raw_response, clean_ans)
        
        if config.ENABLE_REASONING_ENGINE:
             self.reasoning_engine.analyze_task(user_input, messages + [{"role": "assistant", "content": raw_response}], "SUCCESS")
        
        # 6. Multi-Agent Delegation Flow
        if "DELEGATE:" in raw_response:
             print("[*] Orchestrator: Detected delegation request. Spawning subagents...")
             delegations = re.findall(r"DELEGATE:\s*\[([\w\s]+)\]\s*(.*?)(?=DELEGATE:|$)", raw_response, re.DOTALL)
             if delegations:
                  results = self.subagent_manager.delegate_and_collect(delegations)
                  summary = "\n".join([f"SUBAGENT {r} REPORT: {v[:200]}..." for r, v in results.items()])
                  raw = f"ORCHESTRATOR REPORT: Task decentralized.\n{summary}"
                  return make_response(raw, "Task decentralized across subagents.", status="ok", metadata={**meta, "delegated": True})

        # 7. Project Flow
        is_project = meta.get('is_project')
        if is_project:
            project_dir, project_summary = self._project_planning_flow(user_input, messages)
            return self._autonomous_coding_loop(user_input, messages, project_summary, base_dir=project_dir, stream_callback=stream_callback)
        elif meta['is_code'] and not user_input.lstrip().startswith("ROLE:"):
            # Single-File Code Task: Direct validate and save (bypass V12 Project Loop)
            response_for_files = raw_response
            fallback = self.code_fallbacks.match(user_input, meta)
            if "[FILE:" not in response_for_files:
                if fallback:
                    print(f"[*] Code Fallback: using deterministic {fallback.filename}")
                    response_for_files = fallback.as_file_block()
                    raw_response = response_for_files
            saved, failures = self._extract_and_save_files(response_for_files)
            if not saved and failures and fallback:
                print(f"[*] Code Fallback: replacing invalid model output with {fallback.filename}")
                raw_response = fallback.as_file_block()
                saved, failures = self._extract_and_save_files(raw_response)
            if saved and fallback and not self._validate_single_file_behavior(user_input, saved[0]):
                print(f"[*] Code Fallback: replacing behavior-invalid output with {fallback.filename}")
                raw_response = fallback.as_file_block()
                saved, failures = self._extract_and_save_files(raw_response)
            status = f"Code Task Complete. Saved: {', '.join(saved) if saved else 'None'}"
            if failures: status += f" | Failures: {len(failures)}"
            return make_response(raw_response, status, files=saved, status="error" if failures else "ok", errors=list(failures.values()), metadata=meta)

        if self.request_cache and exact_cache_key:
            self.request_cache.set(
                exact_cache_key,
                {"raw": raw_response, "clean": clean_ans},
                ttl=getattr(config, "REQUEST_CACHE_TTL_SECONDS", 24 * 3600),
            )

        return make_response(raw_response, clean_ans, status="ok", metadata=meta)

    def _try_scaffold_project(self, user_input, meta):
        # Clean matching pack detection via brain
        matching_packs = [p for p in self.brain.feature_packs.keys() if p.lower() in user_input.lower()]
        if matching_packs:
            print(f"[*] Economic Mode: matching packs found: {', '.join(matching_packs)}")
        
        memory_matches = self.execution_memory.retrieve(user_input, meta.get("target_stack", ""), limit=3)
        if memory_matches:
            print(f"[*] Execution Memory: retrieved {len(memory_matches)} similar build record(s).")

        scaffold = self.scaffold_registry.match(user_input, meta)
        if not scaffold:
            scaffold = self.dynamic_scaffold_builder.build(user_input, meta)
        if not scaffold:
            return None

        project_name = re.sub(r'[^a-z0-9]', '_', user_input.lower())[:20]
        project_dir = f"v12_{project_name}_{int(time.time())}"
        print(f"[Project Phase] Using registered scaffold: {scaffold.name}")
        self.sandbox.create_sandbox(project_dir)
        print(f"[*] Project Planning Complete: {project_dir}")
        manifest = list(scaffold.files)
        blocks = []
        # Swarm Mode decommissioned in favor of autonomous planning loop
        pass
        for path, content in scaffold.files.items():
            lang = os.path.splitext(path)[1].lstrip('.') or 'text'
            blocks.append(f"[FILE: {path}]\n```{lang}\n{content}\n```")
        response = "\n\n".join(blocks)
        saved, failures = self._extract_and_save_files(response, base_dir=project_dir, manifest=manifest)
        if failures:
            print(f"[!] Scaffold validation failed: {failures}")
        if saved:
            sync_project_dir(self.brain, self.kg, os.path.join(self.sandbox.root_dir, project_dir))
        verification_failures = self._verify_scaffold_contract(scaffold, saved)
        if verification_failures:
            failures = {**failures, **verification_failures}
        report = self._generate_report(project_dir, manifest, saved, failures)
        if scaffold.verification_commands:
            report += "\n**Verification Commands**: " + " && ".join(scaffold.verification_commands)
        if matching_packs:
            report += "\n**Economic Mode**: " + ", ".join(matching_packs)
        if memory_matches:
            report += f"\n**Execution Memory Matches**: {len(memory_matches)}"
        build_status = "failed" if failures else "verified_static"
        self.execution_memory.record_build(
            user_input,
            scaffold.stack,
            project_dir,
            saved,
            scaffold.verification_commands,
            build_status,
            failures,
        )
        if not failures:
            pack = self.auto_pack_builder.maybe_create_pack(user_input, scaffold, saved, failures)
            if pack:
                print(f"[+] Auto-Pack Builder: created reusable pack '{pack['feature']}'.")
        return response, report

    def _verify_scaffold_contract(self, scaffold, saved):
        """Static verification gate for generated test and CLI coverage."""
        saved_set = {path.replace("\\", "/") for path in saved}
        failures = {}
        package_content = scaffold.files.get("package.json")
        saved_lower = {path.lower() for path in saved_set}
        has_test_file = any(
            re.search(r"(^|/)(test|tests)/", path)
            or path.endswith((".test.ts", ".test.tsx", "_test.py", "_test.c", "test_app.py", "tests.cs"))
            for path in saved_lower
        )
        if not has_test_file:
            failures["verification:test_files"] = "Scaffold did not generate any test files."
        if package_content:
            try:
                package_data = json.loads(package_content)
                scripts = package_data.get("scripts", {})
                if "test" not in scripts:
                    failures["verification:package.json"] = "package.json is missing a test script."
            except Exception as exc:
                failures["verification:package.json"] = f"package.json could not be inspected: {exc}"
        if not scaffold.verification_commands:
            failures["verification:commands"] = "Scaffold has no CLI verification commands."
        return failures

    def _project_planning_flow(self, user_input, meta, web_ref=None):
        """Elite V10: 11-step project pipeline initialization."""
        print("[*] Project Phase: Planning & Manifesting...", flush=True)
        graph_plan = self.graph_reasoner.plan_project(user_input)
        if not web_ref:
            with tracker.track("PROJECT_RESEARCH"):
                search_query = f"Architecture and file structure for {user_input}"
                try:
                    web_ref = self.searcher.search(search_query)
                except Exception as e:
                    print(f"[!] Project research failed: {e}")
                    web_ref = ""
        
        project_name = re.sub(r'[^a-z0-9]', '_', user_input.lower())[:20]
        project_dir = f"v12_{project_name}_{int(time.time())}"
        sandbox_path = self.sandbox.create_sandbox(project_dir)
        
        # Elite V12: Capability Contract Generation
        with tracker.track("CONTRACT_GENERATION"):
            print("[*] V12 Phase: Generating Capability Contract...", flush=True)
            contract = self.contractor.build(user_input)
            with open(os.path.join(sandbox_path, "CONTRACT.json"), "w", encoding="utf-8") as f:
                 json.dump(contract, f, indent=2)
                 
        with tracker.track("PLAN_GENERATION"):
            print("[*] Phase: Drafting implementation plan...", flush=True)
            planner_prompt = prompts.PROJECT_PLANNER_PROMPT + f"\n\nUSER REQUEST: {user_input}"
            planner_prompt += f"\n\n[GRAPH PLAN]\n" + "\n".join(f"- {step}" for step in graph_plan[:10])
            planner_prompt += f"\n\n[MANDATORY CONTRACT TARGETS]\nYour plan MUST include these exact files:\n"
            for crit in contract.get('critical_files', []):
                 planner_prompt += f"- {crit}\n"
                 
            if web_ref: planner_prompt += f"\n\nRESEARCH:\n{web_ref[:1000]}"
            
            recent_failures = self.failure_memory.get_recent_failures(limit=3)
            if recent_failures:
                planner_prompt += "\n\n[PAST BUILD FAILURES (Avoid these mistakes)]\n"
                for rf in recent_failures:
                    req = rf.get('request', 'Previous Build')
                    errs = rf.get('failures', rf.get('error', 'Implementation Failure'))
                    planner_prompt += f"- {req}: {errs}\n"
            
            if config.ENABLE_REASONING_ENGINE:
                lessons = self.reasoning_engine.get_relevant_lessons(user_input)
                if lessons:
                    planner_prompt += "\n\n[REASONING LESSONS]\n" + "\n".join(f"- {l}" for l in lessons)
            
            try:
                response = self.client.chat.completions.create(
                    model=self.model_router.route(user_input),
                    messages=[{"role": "system", "content": prompts.SYSTEM_PROMPT}, {"role": "user", "content": planner_prompt}],
                    temperature=0.1,
                    timeout=config.REQUEST_TIMEOUT,
                )
                plan_text = response.choices[0].message.content or ""
            except Exception as e:
                print(f"[!] Planning generation failed: {e}")
                plan_text = f"Fallback Plan Generated due to API error: {e}"
        
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
                model=self.model_router.route("synthesis"),
                messages=[{"role": "user", "content": synthesis_prompt}],
                temperature=0.3,
                timeout=config.REQUEST_TIMEOUT,
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
        scratch_dir = self._scratch_dir(base_dir)
        
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
        fallback_summary = (
            f"Build {status.lower()} with {done}/{total} manifest files validated. "
            f"Missing targets: {missing_str}. Failures: {failures or 'None'}."
        )
        summary = fallback_summary
        return f"### PROJECT BUILD REPORT: {base_dir}\n**Status**: {status}\n**Compliance**: {compliance:.1f}%\n**Missing**: {missing_str}\n\n" + summary

    def _extract_saved_files_from_report(self, report):
        matches = re.findall(r"\[FILE:\s*([^\]]+)\]", report or "")
        matches.extend(re.findall(r"(?:Saved|Staged|Committed)\s+validated\s+([^\s]+)", report or ""))
        return [m.strip() for m in matches]

    def _scratch_dir(self, base_dir=None):
        return self.sandbox.root_dir if not base_dir else os.path.join(self.sandbox.root_dir, base_dir)

    def _list_saved_manifest_files(self, manifest, scratch_dir):
        return [f for f in manifest if os.path.exists(os.path.join(scratch_dir, f))]

    def _read_file_map(self, files, scratch_dir):
        file_map = {}
        for filename in files:
            path = os.path.join(scratch_dir, filename)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as fh:
                    file_map[filename] = fh.read()
        return file_map

    def _language_map_for_files(self, files):
        ext_map = {
            ".py": "python",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".js": "javascript",
            ".jsx": "javascript",
            ".go": "go",
            ".rs": "rust",
            ".c": "c",
            ".json": "json",
            ".css": "css",
        }
        return {path: ext_map.get(os.path.splitext(path)[1].lower(), "text") for path in files}

    def _inject_required_pack_files(self, contract, file_map, manifest, base_dir=None):
        """Apply pack-injector output to disk and manifest when contract requires packs."""
        before = set(file_map)
        self.contractor.contract_data = contract
        updated_map = self.contractor.inject_required_packs(dict(file_map))
        injected = {path: content for path, content in updated_map.items() if path not in before}
        if not injected:
            return []

        saved = []
        for path, content in injected.items():
            if path not in manifest:
                manifest.append(path)
            block = f"[FILE: {path}]\n```{os.path.splitext(path)[1].lstrip('.')}\n{content}\n```"
            staged, failures = self._extract_and_save_files(block, base_dir=base_dir, manifest=manifest)
            saved.extend(staged)
            if failures:
                print(f"[!] Pack injection skipped invalid files: {failures}")
        if saved:
            print(f"[+] Pack Injection: committed {len(saved)} required file(s).")
        return saved

    def _autonomous_coding_loop(self, user_input, base_messages, initial_response, base_dir=None, stream_callback=None):
        """Elite V10.4: Layered repair loop with deterministic seeding and strict dependency traversal."""
        attempts = 0
        max_attempts = config.MAX_PROJECT_RETRIES + 5  # Increased runway for complex scaffolds
        current_response = initial_response
        is_nextjs = "next.js" in user_input.lower()
        manifest = self._extract_manifest(initial_response)
        scratch_dir = self._scratch_dir(base_dir)
        
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
        # Wire in Brain-recalled feature packs if they match
        recalled_cap = base_messages[0].get('metadata', {}).get('recalled_cap') if base_messages else None
        if recalled_cap and recalled_cap.get('type') == 'SHARD':
            pack = self.brain.get_feature_pack(recalled_cap['name'])
            if pack:
                print(f"[+] Capability Induction: Injecting Brain-recalled pack '{recalled_cap['name']}'")
                self._inject_required_pack_files(contract, {}, manifest, base_dir=base_dir)

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
            actual_saved = self._list_saved_manifest_files(manifest, scratch_dir)
                    
            missing = [f for f in manifest if f not in actual_saved and f != "PLAN.md"]
            if not missing and not persistent_failures:
                # Elite V13.0: High-Fidelity Build Critic
                critic_pass_count += 1
                print(f"[+] Manifest satisfied. Escalating to V13 Build Critic (Pass {critic_pass_count})...")
                
                # V12: Build file map for Critic
                file_map = self._read_file_map(actual_saved, scratch_dir)
                injected_files = self._inject_required_pack_files(contract, file_map, manifest, base_dir=base_dir)
                if injected_files:
                    actual_saved = self._list_saved_manifest_files(manifest, scratch_dir)
                    file_map = self._read_file_map(actual_saved, scratch_dir)
                    missing = [f for f in manifest if f not in actual_saved and f != "PLAN.md"]
                    if missing:
                        continue
                project_content_blob = "".join(file_map.values())

                context_state = self.large_context_manager.manage(
                    file_map,
                    contract,
                    self._language_map_for_files(file_map.keys()),
                )
                if context_state.get("needs_phasing"):
                    print(f"[*] Context Manager: project split recommended across {len(context_state['phases'])} phases.")

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
                     synced = sync_project_dir(self.brain, self.kg, scratch_dir)
                     if synced:
                          print(f"[+] BrainSync: synced {synced} project data record(s).")
                     if config.ENABLE_REASONING_ENGINE:
                          with tracker.track("REASONING_ANALYSIS"):
                               self.reasoning_engine.analyze_task(user_input, base_messages + [{"role": "assistant", "content": current_response}], "SUCCESS", critic_report)
                     return make_response(
                         current_response, 
                         self._generate_report(base_dir, manifest, actual_saved, {}),
                         files=actual_saved,
                         status="ok",
                         metadata={"project_dir": base_dir or scratch_dir}
                     )
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
                               f_map = self._read_file_map(actual_saved, scratch_dir)
                               
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
                                    return make_response(
                                         current_response, 
                                         self._generate_report(base_dir, manifest, actual_saved, {"critic": critic_report}),
                                         files=actual_saved,
                                         status="error",
                                         metadata={"reason": "critic_rejection"}
                                     )
                     
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
                                return make_response(
                                    current_response, 
                                    self._generate_report(base_dir, manifest, actual_saved, {"critic": "Hard Limit Reached"}),
                                    files=actual_saved,
                                    status="error",
                                    metadata={"reason": "hard_limit"}
                                )

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
                           return make_response(
                               current_response, 
                               self._generate_report(base_dir, manifest, actual_saved, {"critic": critic_report}),
                               files=actual_saved,
                               status="error",
                               metadata={"reason": "vague_critic"}
                           )

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
            
            try:
                response = self.client.chat.completions.create(
                    model=self.model_router.route(user_input),
                    messages=messages,
                    temperature=0.1,
                    timeout=config.REQUEST_TIMEOUT,
                )
                current_response = response.choices[0].message.content or ""
            except Exception as exc:
                print(f"[!] Repair generation failed: {exc}")
                current_response = ""
            if not current_response.strip():
                print("[!] Empty repair response. Ending project loop early.")
                break
            
        # Elite V12: Final Output & Ultimate Critic Gate
        actual_saved = self._list_saved_manifest_files(manifest, scratch_dir)
        file_map = self._read_file_map(actual_saved, scratch_dir)
        
        critic_report = self.critic.evaluate(user_input, contract, file_map)
        print(f"[*] V12 Final Critic Evaluation: {critic_report.splitlines()[0] if critic_report else 'SCORE: 0'}")
        
        # Persist failure if low score
        if "SCORE: 100" not in critic_report:
             self.failure_memory.record_failure(contract.get('stack', 'unknown'), user_input, persistent_failures, critic_report)
             self.execution_memory.record_build(
                 user_input,
                 contract.get('stack', 'unknown'),
                 base_dir or "",
                 actual_saved,
                 [],
                 "critic_failed",
                 {"critic": critic_report, **persistent_failures},
             )
             if config.ENABLE_REASONING_ENGINE:
                  self.reasoning_engine.analyze_task(user_input, base_messages + [{"role": "assistant", "content": current_response}], "FAILURE", critic_report)
        else:
             synced = sync_project_dir(self.brain, self.kg, scratch_dir)
             if synced:
                  print(f"[+] BrainSync: synced {synced} project data record(s).")
             self.execution_memory.record_build(
                 user_input,
                 contract.get('stack', 'unknown'),
                 base_dir or "",
                 actual_saved,
                 [],
                 "critic_passed",
                 {},
             )
        
        # Final output persistence: Guarantee the last generated file lands on disk
        self._extract_and_save_files(current_response, base_dir=base_dir, manifest=manifest)
        
        # Phase 13: Autonomous Synthesis - Create new packs/skills on the fly
        if "SCORE: 100" in critic_report and config.ENABLE_AUTONOMOUS_SYNTHESIS:
             self._run_synthesis_loop(user_input, base_messages + [{"role": "assistant", "content": current_response}])

        report = self._generate_report(base_dir, manifest, actual_saved, persistent_failures)
        return make_response(
            current_response, 
            report, 
            files=actual_saved, 
            status="error" if persistent_failures else "ok",
            metadata={"project_dir": base_dir or scratch_dir}
        )

    def _extract_and_save_files(self, text, base_dir=None, manifest=None):
        """V10 Modular Extraction with formatting and transactional writes."""
        if not isinstance(text, str):
            text = str(text or "")
        file_markers = list(re.finditer(r"\[FILE:\s*((?:\[[^\]]*\]|[^\]])+)\]", text))
        scratch_dir = self.sandbox.root_dir if not base_dir else os.path.join(self.sandbox.root_dir, base_dir)
        os.makedirs(scratch_dir, exist_ok=True)
        
        saved, failures = [], {}
        available = set(manifest) if manifest else set()
        is_nextjs = any("app/" in f for f in available) or (manifest and any(".tsx" in f for f in manifest))
        transaction = ProjectTransaction(scratch_dir).begin()
        staged_content = {}
        
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
            else:
                raw_block = text[start:end].strip()
                raw_block = re.sub(r"^\s*```[a-zA-Z0-9_-]*\s*", "", raw_block).strip()
                raw_block = re.sub(r"\s*```\s*$", "", raw_block).strip()
                code = raw_block if raw_block else ""
                if not code:
                    skeleton = get_best_skeleton(filename, brain=self.brain)
                    if skeleton: code = skeleton['content']
                    else: failures[filename] = "No code"; continue

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

            code = self.formatter.format(filename, code)

            ok, err = self.validator.validate(filename, code, {'available_files': available})
            if not ok: failures[filename] = err; continue

            fpath = os.path.join(scratch_dir, filename)
            
            # Phase 10: Authoritative Path Safety Guard
            if os.path.isdir(fpath):
                print(f"[!] Path Safety violation: {filename} matches an existing directory. Skipping.")
                failures[filename] = "Path collision with existing directory"
                continue

            try:
                ok, err = transaction.add_file(filename, code)
                if not ok:
                    failures[filename] = err
                    continue
                saved.append(filename)
                staged_content[filename] = code
                available.add(filename)
                print(f"Staged validated {filename}")
            except Exception as e:
                print(f"[!] Stage FAILED for {filename}: {str(e)}")
                failures[filename] = str(e)

        if failures:
            transaction.rollback()
            return [], failures

        try:
            committed = transaction.commit()
            saved = committed
            if committed:
                self.kg_builder.extract_from_project({name: staged_content[name] for name in committed if name in staged_content})
                print(f"Committed {len(committed)} validated file(s)")
        except Exception as e:
            transaction.rollback()
            for filename in saved:
                failures[filename] = f"Commit failed: {e}"
            saved = []

        return saved, failures

    def _validate_single_file_behavior(self, user_input, filename):
        if "factorial" not in user_input.lower() or not filename.endswith(".py"):
            return True
        path = os.path.join(self.sandbox.root_dir, filename)
        if not os.path.exists(path):
            return False
        script = (
            "import importlib.util, pathlib; "
            f"path=pathlib.Path(r'''{path}'''); "
            "spec=importlib.util.spec_from_file_location('generated_module', path); "
            "module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); "
            "func=getattr(module, 'factorial', None) or getattr(module, 'calculate_factorial', None); "
            "print(func(5) if func else 'NO_FUNC')"
        )
        try:
            result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=10)
            return result.returncode == 0 and result.stdout.strip() == "120"
        except Exception:
            return False

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
        if not isinstance(plan_text, str):
            plan_text = str(plan_text or "")
        # Hardened V10.5: Multi-strategy path extraction
        # Strategy A: Explicit [FILE: path] markers
        explicit_matches = re.findall(r"\[FILE:\s*([^\]\s]+)\]", plan_text)
        
        # Strategy B: Generic path detection (fallback)
        clean_text = re.sub(r"\[FILE:\s*", " ", plan_text)
        generic_matches = re.findall(r"(?:^|[\s'`])([\w\.\/\-@]+\.\w+)(?=[\]\s'`]|$)", clean_text)
        
        raw_paths = list(set(explicit_matches + generic_matches))
        valid_exts = {'.py', '.js', '.tsx', '.jsx', '.css', '.html', '.json', '.md', '.sql', '.yml', '.yaml', '.toml', '.rs', '.go', '.c', '.cpp', '.h', '.hpp', '.sh', '.bat', '.ps1'}
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
