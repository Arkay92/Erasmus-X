"""
Context Manager - Intelligent context window management for large projects.

Implements hierarchical summarization, smart pruning, phase-based splitting,
and local LLM-based reasoning for handling projects larger than token limits.
"""

import re
import json
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import hashlib
from collections import defaultdict


class Relevance(Enum):
    CRITICAL = 1.0      # Core business logic
    HIGH = 0.8          # Important dependencies
    MEDIUM = 0.5        # Supporting code
    LOW = 0.2           # Utilities, helpers
    MINIMAL = 0.05      # Comments, formatting


@dataclass
class FileSummary:
    """Hierarchical summary of a code file."""
    path: str
    language: str
    loc: int  # Lines of code
    
    # Hierarchy levels
    summary_full: str = ""
    summary_medium: str = ""  # 50% of full
    summary_brief: str = ""   # 20% of full
    
    relevance: float = 0.5
    key_entities: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    patterns: List[str] = field(default_factory=list)


@dataclass
class ProjectPhase:
    """Represents a generation phase for large projects."""
    phase_num: int
    name: str
    files: List[str]
    dependencies: List[int] = field(default_factory=list)  # Phase numbers
    estimated_tokens: int = 0
    description: str = ""
    order: int = 0


class HierarchicalSummarizer:
    """Summarizes code at multiple levels for context efficiency."""
    
    def __init__(self, local_llm=None):
        self.local_llm = local_llm
        self.file_cache = {}
    
    def summarize_file(self, path: str, content: str, language: str) -> FileSummary:
        """Create hierarchical summary of a single file."""
        
        # Check cache
        cache_key = hashlib.md5(content.encode()).hexdigest()
        if cache_key in self.file_cache:
            return self.file_cache[cache_key]
        
        summary = FileSummary(path=path, language=language, loc=len(content.split('\n')))
        
        # Extract structural elements
        summary.key_entities = self._extract_entities(content, language)
        summary.dependencies = self._extract_dependencies(content, language)
        summary.exports = self._extract_exports(content, language)
        summary.patterns = self._detect_patterns(content, language)
        
        # Generate hierarchical summaries
        full_summary = self._generate_full_summary(content, language, summary)
        summary.summary_full = full_summary
        summary.summary_medium = self._reduce_summary(full_summary, 0.5)
        summary.summary_brief = self._reduce_summary(full_summary, 0.2)
        
        self.file_cache[cache_key] = summary
        return summary
    
    def _extract_entities(self, content: str, language: str) -> List[str]:
        """Extract key entities (functions, classes, types)."""
        entities = []
        
        if language in ['python', 'py']:
            # Python: class/def names
            classes = re.findall(r'^class\s+(\w+)', content, re.MULTILINE)
            functions = re.findall(r'^def\s+(\w+)', content, re.MULTILINE)
            entities = classes + functions
        
        elif language in ['typescript', 'ts', 'javascript', 'js']:
            # TS/JS: export/class/function
            classes = re.findall(r'(?:export\s+)?class\s+(\w+)', content)
            functions = re.findall(r'(?:export\s+)(?:async\s+)?function\s+(\w+)', content)
            const_funcs = re.findall(r'export\s+const\s+(\w+)\s*=', content)
            entities = classes + functions + const_funcs
        
        elif language == 'go':
            # Go: func/type
            funcs = re.findall(r'^func\s+\(?[^)]*\)?\s*(\w+)', content, re.MULTILINE)
            types = re.findall(r'^type\s+(\w+)', content, re.MULTILINE)
            entities = funcs + types
        
        elif language == 'rust':
            # Rust: fn/struct/impl
            funcs = re.findall(r'fn\s+(\w+)', content)
            structs = re.findall(r'struct\s+(\w+)', content)
            impls = re.findall(r'impl\s+(\w+)', content)
            entities = funcs + structs + impls
        
        return list(set(entities))[:10]  # Top 10
    
    def _extract_dependencies(self, content: str, language: str) -> List[str]:
        """Extract external dependencies."""
        deps = []
        
        if language in ['python', 'py']:
            imports = re.findall(r'^(?:from|import)\s+([a-zA-Z0-9_.]+)', content, re.MULTILINE)
            deps = [imp.split('.')[0] for imp in imports]
        
        elif language in ['typescript', 'ts', 'javascript', 'js']:
            imports = re.findall(r"import\s+[^;]+from\s+['\"]([^'\"]+)['\"]", content)
            deps = [imp.split('/')[0] for imp in imports]
        
        elif language == 'go':
            imports = re.findall(r'import\s+[(\"]([^\")\s]+)', content)
            deps = imports
        
        elif language == 'rust':
            uses = re.findall(r'use\s+([a-zA-Z0-9_:]+)', content)
            deps = uses
        
        return list(set(deps))[:5]  # Top 5
    
    def _extract_exports(self, content: str, language: str) -> List[str]:
        """Extract public exports."""
        exports = []
        
        if language in ['typescript', 'ts', 'javascript', 'js']:
            exports = re.findall(r'export\s+(?:default\s+)?(?:class|function|const|type|interface)\s+(\w+)', content)
        
        elif language == 'go':
            # Capitalized names are exported in Go
            exports = re.findall(r'(?:func|type|var|const)\s+([A-Z]\w*)', content)
        
        elif language == 'rust':
            exports = re.findall(r'pub\s+(?:fn|struct|enum)\s+(\w+)', content)
        
        return exports[:5]
    
    def _detect_patterns(self, content: str, language: str) -> List[str]:
        """Detect architectural patterns."""
        patterns = []
        
        # Common patterns
        if 'class ' in content and 'def __init__' in content:
            patterns.append('OOP')
        if 'async ' in content or 'await ' in content:
            patterns.append('Async')
        if re.search(r'@\w+\(', content):
            patterns.append('Decorators')
        if re.search(r'lambda\s+', content):
            patterns.append('FunctionalProgramming')
        if re.search(r'(try|except|catch)', content):
            patterns.append('ErrorHandling')
        if re.search(r'(test_|_test\.py|\.test\.|describe\()', content):
            patterns.append('Tests')
        
        return patterns
    
    def _generate_full_summary(self, content: str, language: str, metadata: FileSummary) -> str:
        """Generate comprehensive summary."""
        lines = content.split('\n')
        
        # Get meaningful lines (skip blanks, comments)
        meaningful = [l for l in lines if l.strip() and not l.strip().startswith('#') and not l.strip().startswith('/')]
        
        summary_lines = []
        summary_lines.append(f"File: {metadata.path} ({language})")
        summary_lines.append(f"Size: {metadata.loc} lines")
        
        if metadata.key_entities:
            summary_lines.append(f"Entities: {', '.join(metadata.key_entities[:5])}")
        
        if metadata.dependencies:
            summary_lines.append(f"Dependencies: {', '.join(metadata.dependencies[:3])}")
        
        if metadata.patterns:
            summary_lines.append(f"Patterns: {', '.join(metadata.patterns[:3])}")
        
        if metadata.exports:
            summary_lines.append(f"Exports: {', '.join(metadata.exports[:3])}")
        
        # Extract code structure
        if meaningful:
            # First meaningful line
            summary_lines.append(f"\nCore: {meaningful[0][:80]}")
        
        return "\n".join(summary_lines)
    
    def _reduce_summary(self, full_summary: str, ratio: float) -> str:
        """Reduce summary to a fraction of original length."""
        lines = full_summary.split('\n')
        target_count = max(1, int(len(lines) * ratio))
        return '\n'.join(lines[:target_count])
    
    def summarize_project(self, files: Dict[str, str], language_map: Dict[str, str]) -> Dict[str, FileSummary]:
        """Summarize entire project."""
        summaries = {}
        
        for path, content in files.items():
            language = language_map.get(path, 'unknown')
            summaries[path] = self.summarize_file(path, content, language)
        
        return summaries


class RelevanceScorer:
    """Scores relevance of files for context pruning."""
    
    def __init__(self, contract: Dict[str, Any]):
        self.contract = contract
        self.stack = contract.get('stack', '').split('|')
        self.features = contract.get('features', [])
    
    def score_file(self, path: str, summary: FileSummary) -> float:
        """Score a file's relevance to the project contract."""
        score = 0.5  # Base score
        
        # Path-based relevance
        if any(part in path.lower() for part in ['api', 'route', 'controller']):
            score += 0.2 if 'api' in self.features else 0.05
        
        if any(part in path.lower() for part in ['db', 'model', 'schema']):
            score += 0.2 if 'database' in self.features else 0.05
        
        if any(part in path.lower() for part in ['test']):
            score += 0.1 if 'testing' in self.features else 0.02
        
        if any(part in path.lower() for part in ['component', 'page', 'layout']):
            score += 0.15 if 'ui' in self.features else 0.05
        
        # Dependency relevance
        key_deps = {'prisma', 'fastapi', 'flask', 'express', 'nextjs', 'react'}
        if any(dep in summary.dependencies for dep in key_deps):
            score += 0.2
        
        # Pattern relevance
        if 'Tests' in summary.patterns and 'testing' in self.features:
            score += 0.1
        
        return min(score, 1.0)
    
    def score_files(self, summaries: Dict[str, FileSummary]) -> Dict[str, float]:
        """Score all files."""
        return {path: self.score_file(path, summary) for path, summary in summaries.items()}


class ProjectPhaseBuilder:
    """Splits large projects into manageable phases."""
    
    def __init__(self, token_limit: int = 8000):
        self.token_limit = token_limit
        self.tokens_per_line = 0.25  # Rough estimate
    
    def build_phases(self, 
                    files: Dict[str, str],
                    contract: Dict[str, Any]) -> List[ProjectPhase]:
        """Split project into phases based on token budget."""
        
        phases = []
        
        # Group files by category
        groups = self._group_files_by_category(files.keys())
        
        # Create phases with dependencies
        phase_map = {}
        phase_num = 0
        
        for category, file_list in groups.items():
            tokens = sum(len(content.split('\n')) * self.tokens_per_line 
                        for path, content in files.items() if path in file_list)
            
            if tokens > self.token_limit:
                # Split this category into sub-phases
                sub_phases = self._split_large_category(file_list, files, category)
                for i, sub_phase_files in enumerate(sub_phases):
                    phase = ProjectPhase(
                        phase_num=phase_num,
                        name=f"{category.capitalize()} - Part {i+1}",
                        files=sub_phase_files,
                        estimated_tokens=int(tokens / len(sub_phases))
                    )
                    phases.append(phase)
                    phase_map[category] = phase_num
                    phase_num += 1
            else:
                phase = ProjectPhase(
                    phase_num=phase_num,
                    name=category.capitalize(),
                    files=file_list,
                    estimated_tokens=int(tokens)
                )
                phases.append(phase)
                phase_map[category] = phase_num
                phase_num += 1
        
        # Add dependency ordering
        phases = self._add_phase_dependencies(phases)
        
        return phases
    
    def _group_files_by_category(self, file_paths: List[str]) -> Dict[str, List[str]]:
        """Group files by functional category."""
        groups = defaultdict(list)
        
        for path in file_paths:
            if 'test' in path.lower():
                groups['tests'].append(path)
            elif any(x in path.lower() for x in ['schema', 'model', 'db']):
                groups['database'].append(path)
            elif any(x in path.lower() for x in ['api', 'route', 'endpoint']):
                groups['api'].append(path)
            elif any(x in path.lower() for x in ['component', 'page', 'layout']):
                groups['ui'].append(path)
            elif 'config' in path.lower() or 'env' in path.lower():
                groups['config'].append(path)
            else:
                groups['utilities'].append(path)
        
        return groups
    
    def _split_large_category(self, files: List[str], 
                             file_content: Dict[str, str],
                             category: str) -> List[List[str]]:
        """Split category if too large."""
        if len(files) <= 3:
            return [files]
        
        # Divide into chunks of 2-3 files
        chunk_size = 3
        chunks = []
        for i in range(0, len(files), chunk_size):
            chunks.append(files[i:i+chunk_size])
        
        return chunks
    
    def _add_phase_dependencies(self, phases: List[ProjectPhase]) -> List[ProjectPhase]:
        """Add dependency relationships between phases."""
        
        phase_categories = {
            'config': [],
            'database': [],
            'api': [],
            'ui': [],
            'tests': []
        }
        
        for phase in phases:
            # Extract category from phase name
            name_lower = phase.name.lower()
            for cat in phase_categories:
                if cat in name_lower:
                    phase_categories[cat].append(phase.phase_num)
                    break
        
        # Set up dependencies: tests depend on everything, ui depends on api, etc
        for phase in phases:
            name_lower = phase.name.lower()
            
            if 'test' in name_lower:
                # Tests depend on all other phases
                phase.dependencies = [p.phase_num for p in phases if p.phase_num != phase.phase_num]
            
            elif 'ui' in name_lower:
                # UI depends on API and config
                phase.dependencies = phase_categories.get('api', []) + phase_categories.get('config', [])
            
            elif 'api' in name_lower:
                # API depends on database and config
                phase.dependencies = phase_categories.get('database', []) + phase_categories.get('config', [])
            
            elif 'database' in name_lower:
                # Database depends on config
                phase.dependencies = phase_categories.get('config', [])
        
        return phases


class ContextAnalyzer:
    """Analyzes and manages context for large projects."""
    
    def __init__(self, local_llm=None, max_context_tokens: int = 8000):
        self.local_llm = local_llm
        self.max_context_tokens = max_context_tokens
        self.summarizer = HierarchicalSummarizer(local_llm)
    
    def analyze_project(self, 
                       files: Dict[str, str],
                       contract: Dict[str, Any],
                       language_map: Dict[str, str]) -> Dict[str, Any]:
        """Comprehensive analysis of project for smart context management."""
        
        analysis = {
            'total_files': len(files),
            'total_tokens': 0,
            'summaries': {},
            'scores': {},
            'phases': [],
            'recommendations': []
        }
        
        # Generate summaries
        summaries = self.summarizer.summarize_project(files, language_map)
        analysis['summaries'] = summaries
        
        # Score relevance
        scorer = RelevanceScorer(contract)
        scores = scorer.score_files(summaries)
        analysis['scores'] = scores
        
        # Calculate total tokens
        total_tokens = sum(len(content.split('\n')) * 0.25 for content in files.values())
        analysis['total_tokens'] = int(total_tokens)
        
        # Build phases if needed
        if total_tokens > self.max_context_tokens:
            phase_builder = ProjectPhaseBuilder(self.max_context_tokens)
            phases = phase_builder.build_phases(files, contract)
            analysis['phases'] = phases
            analysis['recommendations'].append(
                f"Project exceeds context limit ({int(total_tokens)} tokens). "
                f"Split into {len(phases)} phases."
            )
        
        # Recommend pruning
        if total_tokens > self.max_context_tokens * 0.8:
            pruned_context = self.prune_context(files, summaries, scores, ratio=0.6)
            analysis['pruned_tokens'] = int(pruned_context['total_tokens'])
            analysis['pruned_files'] = list(pruned_context['files'].keys())
            analysis['recommendations'].append(
                f"Context pruning recommended: reduce to {len(pruned_context['files'])} files"
            )
        
        return analysis
    
    def prune_context(self, files: Dict[str, str], 
                     summaries: Dict[str, FileSummary],
                     scores: Dict[str, float],
                     ratio: float = 0.6) -> Dict[str, Any]:
        """Intelligently prune context to fit token limit."""
        
        # Sort by relevance
        sorted_files = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        # Select top files by relevance to reach target ratio
        target_count = max(1, int(len(files) * ratio))
        selected = dict(sorted_files[:target_count])
        
        pruned_context = {
            'files': {path: files[path] for path in selected.keys()},
            'total_tokens': sum(len(files[path].split('\n')) * 0.25 for path in selected.keys()),
            'removed_files': [path for path in files.keys() if path not in selected]
        }
        
        return pruned_context
    
    def get_context_for_generation(self, files: Dict[str, str],
                                   contract: Dict[str, Any],
                                   language_map: Dict[str, str],
                                   phase: Optional[int] = None) -> str:
        """Build optimized context string for LLM generation."""
        
        context_parts = []
        
        # Analyze project
        analysis = self.analyze_project(files, contract, language_map)
        
        # Start with contract
        context_parts.append("=" * 60)
        context_parts.append("PROJECT CONTRACT")
        context_parts.append("=" * 60)
        context_parts.append(json.dumps(contract, indent=2))
        
        # Add phase information if project split
        if analysis['phases']:
            context_parts.append("\n" + "=" * 60)
            context_parts.append(f"GENERATION PHASE {phase or 1}/{len(analysis['phases'])}")
            context_parts.append("=" * 60)
            
            if phase is not None:
                current_phase = analysis['phases'][phase]
                context_parts.append(f"Phase: {current_phase.name}")
                context_parts.append(f"Files: {', '.join(current_phase.files)}")
                if current_phase.dependencies:
                    context_parts.append(f"Depends on phases: {current_phase.dependencies}")
        
        # Add summaries (hierarchical based on relevance)
        context_parts.append("\n" + "=" * 60)
        context_parts.append("PROJECT STRUCTURE")
        context_parts.append("=" * 60)
        
        # Use brief summaries for low-relevance files
        for path, score in sorted(analysis['scores'].items(), key=lambda x: x[1], reverse=True)[:15]:
            summary = analysis['summaries'][path]
            if score >= 0.7:
                context_parts.append(f"\n[FULL] {summary.summary_full}")
            elif score >= 0.4:
                context_parts.append(f"\n[MEDIUM] {summary.summary_medium}")
            else:
                context_parts.append(f"\n[BRIEF] {summary.summary_brief}")
        
        # Add recommendations
        if analysis['recommendations']:
            context_parts.append("\n" + "=" * 60)
            context_parts.append("RECOMMENDATIONS")
            context_parts.append("=" * 60)
            context_parts.extend(analysis['recommendations'])
        
        return '\n'.join(context_parts)


class ContextManager:
    """Main context manager orchestrator."""
    
    def __init__(self, local_llm=None, max_context_tokens: int = 8000):
        self.analyzer = ContextAnalyzer(local_llm, max_context_tokens)
        self.local_llm = local_llm
    
    def manage(self, files: Dict[str, str],
              contract: Dict[str, Any],
              language_map: Dict[str, str]) -> Dict[str, Any]:
        """Main entry point for context management."""
        
        analysis = self.analyzer.analyze_project(files, contract, language_map)
        
        result = {
            'needs_phasing': len(analysis['phases']) > 0,
            'phases': analysis['phases'],
            'total_files': analysis['total_files'],
            'total_tokens': analysis['total_tokens'],
            'has_pruning': 'pruned_files' in analysis,
            'pruned_files': analysis.get('pruned_files', []),
            'recommendations': analysis['recommendations']
        }
        
        return result
    
    def get_generation_context(self, files: Dict[str, str],
                               contract: Dict[str, Any],
                               language_map: Dict[str, str],
                               phase: Optional[int] = None) -> str:
        """Get optimized context for generation."""
        return self.analyzer.get_context_for_generation(files, contract, language_map, phase)
    
    def should_split_project(self, files: Dict[str, str]) -> bool:
        """Check if project should be split into phases."""
        total_tokens = sum(len(content.split('\n')) * 0.25 for content in files.values())
        return total_tokens > self.analyzer.max_context_tokens
