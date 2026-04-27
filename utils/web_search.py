"""Unified web search with simple and deep research modes."""
import re
from typing import Dict, List, Optional

try:
    from ddgs import DDGS
except Exception:  # pragma: no cover - exercised when optional dependency is absent
    DDGS = None


class WebSearcher:
    """Search facade used by the agent and tests.

    It combines the original fast snippet lookup with the richer V2 query
    classification/vectorization flow so there is only one web-search module.
    """

    def __init__(self, brain=None):
        self.ddgs = DDGS() if DDGS else None
        self.brain = brain
        self.search_history = []
        self.simple_keywords = [
            "what is", "who is", "define", "meaning", "capital of",
            "where is", "when was", "how many", "price of", "current",
        ]
        self.research_keywords = [
            "analyze", "compare", "explain", "how to", "best practices",
            "architecture", "design", "strategy", "implementation", "research",
        ]

    def classify_query(self, query: str) -> str:
        query_lower = query.lower()
        if any(keyword in query_lower for keyword in self.simple_keywords):
            return "SIMPLE"
        if any(keyword in query_lower for keyword in self.research_keywords):
            return "DEEP"
        if len(query.split()) > 10:
            return "DEEP"
        return "SIMPLE"

    def search(self, query: str, max_results: int = 2, deep_mode: bool = False) -> Optional[str]:
        mode = "DEEP" if deep_mode else self.classify_query(query)
        if mode == "SIMPLE":
            return self.simple_search(query, max_results=max_results)
        result = self.deep_search(query, brain=self.brain)
        summary = f"Deep Research: {result['reasoning']}\n"
        summary += f"Sources Found: {len(result['sources'])}\n"
        summary += "Key Findings:\n"
        for finding in result["findings"][:3]:
            summary += f"- {finding['title']}\n  {finding['snippet'][:200]}...\n"
        return summary

    def simple_search(self, query: str, max_results: int = 3) -> Optional[str]:
        if not self.ddgs:
            print("[!] Search unavailable: optional dependency 'ddgs' is not installed.")
            return None
        try:
            results = list(self.ddgs.text(query, max_results=max_results))
            if not results:
                return None
            best = results[0]
            snippet = best.get("body", "")
            factual_answer = self._extract_factual_answer(query, snippet)
            if self.brain:
                self._vectorize_search_result(query, factual_answer or snippet, best.get("href", ""))
            if factual_answer:
                return factual_answer
            return self._format_snippets(results)
        except Exception as exc:
            print(f"[!] Search error: {exc}")
            return None

    def deep_search(self, query: str, max_iterations: int = 3, brain=None) -> Dict:
        print(f"[*] Engaging Deep Research Mode for: {query}")
        findings = []
        sources = []
        vectorized_count = 0
        cot_steps = []
        current_query = query
        active_brain = brain or self.brain

        for iteration in range(max_iterations):
            print(f"[*] Research iteration {iteration + 1}/{max_iterations}...")
            if not self.ddgs:
                print("[!] Deep search unavailable: optional dependency 'ddgs' is not installed.")
                break
            try:
                results = list(self.ddgs.text(current_query, max_results=3))
                if not results:
                    break
                for result in results:
                    title = result.get("title", "Unknown")
                    body = result.get("body", "")
                    url = result.get("href", "")
                    if url not in sources:
                        sources.append(url)
                        findings.append({"title": title, "snippet": body[:400], "url": url})
                        if active_brain and body:
                            self._vectorize_search_result(query, body, url, brain=active_brain)
                            vectorized_count += 1
                if iteration < max_iterations - 1:
                    follow_up = self._generate_follow_up_query(query, findings)
                    cot_steps.append({
                        "iteration": iteration + 1,
                        "query": follow_up,
                        "found_sources": len(results),
                    })
                    current_query = follow_up
            except Exception as exc:
                print(f"[!] Deep search iteration error: {exc}")
                break

        return {
            "query": query,
            "sources": sources,
            "findings": findings,
            "vectorized": vectorized_count,
            "chain_of_thought": cot_steps,
            "reasoning": f"Found {len(sources)} sources across {len(cot_steps)} research iterations",
        }

    def _format_snippets(self, results: List[Dict]) -> Optional[str]:
        snippets = []
        for result in results:
            body = result.get("body", "")
            if len(body) > 10:
                snippets.append(
                    f"Source: {result.get('title')}\n"
                    f"URL: {result.get('href', 'No URL available')}\n"
                    f"Content: {body[:500]}"
                )
        return "\n\n".join(snippets) if snippets else None

    def _extract_factual_answer(self, question: str, snippet: str) -> str:
        question_lower = question.lower()
        if question_lower.startswith("what is"):
            matches = re.findall(r"([^.!?]*\bis\b[^.!?]*)", snippet)
            if matches:
                return matches[0].strip()
        elif question_lower.startswith("capital of"):
            words = snippet.split()
            if words:
                return " ".join(words[:3]).strip(".,;:")
        elif question_lower.startswith("where is"):
            matches = re.findall(r"located in ([^,.\n]+)", snippet, re.IGNORECASE)
            if matches:
                return f"Located in {matches[0]}"
        sentences = re.split(r"[.!?]", snippet)
        return sentences[0].strip() if sentences and sentences[0] else snippet[:150]

    def _generate_follow_up_query(self, original_query: str, findings: List[Dict]) -> str:
        if not findings:
            return original_query + " explained"
        follow_ups = [
            f"{original_query} implementation",
            f"best practices for {original_query}",
            f"{original_query} examples",
            f"advanced {original_query} techniques",
        ]
        return follow_ups[len(findings) % len(follow_ups)]

    def _vectorize_search_result(self, query: str, content: str, url: str, brain=None) -> None:
        active_brain = brain or self.brain
        if not active_brain or not content:
            return
        try:
            doc_text = f"[SEARCH: {query}]\nURL: {url}\nContent: {content[:500]}"
            active_brain.add_document(doc_text)
            triggers = [query, f"research on {query}", f"about {query}"]
            if url:
                triggers.append(url.split("/")[-1])
            feature_name = f"search_{query.replace(' ', '_')[:20]}"
            active_brain.add_capability_association(
                name=feature_name,
                cap_type="RESEARCH",
                trigger_sentences=triggers,
            )
            domain = url.split("/")[2] if "://" in url else url
            print(f"[+] Vectorized search result for '{query}' from {domain}")
        except Exception as exc:
            print(f"[!] Vectorization error: {exc}")
