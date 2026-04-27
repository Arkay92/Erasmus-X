import re
from core import config
from core.task_metadata import TaskMetadata, is_dynamic_query

class TaskRouter:
    def __init__(self, brain, local_llm):
        self.brain = brain
        self.local_llm = local_llm

    def route(self, user_input):
        """Classifies intent and determines operating mode."""
        intent, confidence = self.brain.classify_intent(user_input)
        single_file_code = self._is_single_file_code_request(user_input)
        is_project = False if single_file_code else self._is_project_like(user_input, intent, confidence)
        is_code = self._is_code_like(user_input, is_project) or single_file_code
        target_stack = self._detect_stack(user_input)
        language = self._detect_language(user_input)
        dynamic = is_dynamic_query(user_input)
        
        # 1. Complexity Check (Gating)
        mode = config.OPERATING_MODE
        if self._is_complex_reasoning(user_input, intent, confidence) or is_project:
            mode = "DEEP"

        return TaskMetadata(
            intent=intent,
            confidence=confidence,
            mode=mode,
            is_code=is_code,
            is_project=is_project,
            is_dynamic=dynamic,
            target_stack=target_stack,
            language=language,
        ).as_dict()

    def _is_code_like(self, text, is_project=False):
        if is_project:
            return False
        lower = text.lower()
        code_phrases = (
            'write code', 'source code', 'code in a', '[file:', 'implement a',
            'implement the', 'return complete code', 'save it to'
        )
        if any(phrase in lower for phrase in code_phrases):
            return True

        action_terms = ('write', 'create', 'build', 'make', 'implement', 'generate', 'scaffold')
        if not any(re.search(rf"\b{re.escape(term)}\b", lower) for term in action_terms):
            return False

        code_terms = (
            'script', 'algorithm', 'function', 'class', 'struct',
            'interface', 'component', 'route', 'api'
        )
        return any(re.search(rf"\b{re.escape(term)}\b", lower) for term in code_terms)

    def _is_single_file_code_request(self, text):
        lower = text.lower()
        has_code_unit = any(k in lower for k in ['function', 'struct', 'interface', 'class', 'script'])
        has_file_instruction = '[file:' in lower or 'appropriate file' in lower or 'save it to' in lower
        has_project_marker = any(k in lower for k in ['project', 'multi-file', 'multiple files', 'application', 'dashboard'])
        return has_code_unit and has_file_instruction and not has_project_marker

    def _is_project_like(self, text, intent=None, confidence=0):
        lower = text.lower()
        build_verbs = ('create', 'build', 'make', 'scaffold', 'generate')
        project_targets = (
            'project', 'application', 'dashboard', 'website',
            'next.js', 'nextjs', 'react', 'express', 'fastapi', 'rest api',
            'full-stack', 'full stack', 'multiple files', 'bot', 'worker', 'tool',
            'service', 'cli', 'webhook', 'booking', 'business', 'saas', 'crm',
            'marketplace', 'appointments'
        )
        has_project_target = any(t in lower for t in project_targets) or bool(re.search(r'\bapp\b', lower))
        if intent == "PROJECT" and confidence > 0.35 and has_project_target:
            return True
        return any(v in lower for v in build_verbs) and has_project_target

    def _detect_stack(self, text):
        lower = text.lower()
        if "next.js" in lower or "nextjs" in lower or "app router" in lower:
            if "prisma" in lower:
                return "nextjs-app-router|prisma|typescript"
            return "nextjs-app-router|typescript"
        if "react" in lower:
            return "react|typescript"
        if "express" in lower:
            return "express|typescript"
        if "fastapi" in lower:
            return "fastapi|python"
        return "generic"

    def _detect_language(self, text):
        lower = text.lower()
        language_terms = {
            "python": "python",
            "typescript": "typescript",
            "javascript": "javascript",
            "rust": "rust",
            "go": "go",
            "golang": "go",
            "c function": "c",
            "php": "php",
            ".net": "csharp",
            "dotnet": "csharp",
            "c#": "csharp",
        }
        for token, language in language_terms.items():
            if token in lower:
                return language
        return None

    def _is_complex_reasoning(self, text, intent, confidence):
        """Heuristic for complexity escalation."""
        if any(k in text.lower() for k in ['complex', 'architecture', 'system', 'refactor', 'debug', 'project']):
            return True
        if intent == "PROJECT" and confidence > 0.3:
            return True
        if len(text.split()) > config.SIMPLE_QUERY_LIMIT:
            return True
        return False

class ExecutionController:
    def __init__(self, client):
        self.client = client

    def enforce_contract(self, user_input, response_text, task_metadata):
        """Ensures the response matches the task type requirements."""
        response_text = response_text or ""
        if "DELEGATE:" in response_text:
            return True, "Delegation contract satisfied"

        if user_input.lstrip().startswith("ROLE:"):
            return True, "Subagent status contract satisfied"

        if task_metadata.get('is_code') and "[FILE:" not in response_text:
            return False, "Code task detected but no [FILE:] tags found. You must implement the source code."
        
        if task_metadata.get('is_project') and "PLAN.md" not in response_text and "[FILE:" not in response_text:
             return False, "Project request detected. You must provide a plan or implement files."
             
        return True, "Contract satisfied"
