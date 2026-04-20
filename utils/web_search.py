from ddgs import DDGS

class WebSearcher:
    def __init__(self):
        self.ddgs = DDGS()

    def search(self, query, max_results=2):
        """High-speed snippet retrieval."""
        try:
            # max_results reduced for speed; quality is maintained via top snippets
            results = list(self.ddgs.text(query, max_results=max_results))
            snippets = []
            for r in results:
                body = r.get('body', '')
                if len(body) > 10:
                    snippets.append(f"Source: {r.get('title')}\nContent: {body[:300]}")
            
            if snippets:
                return "\n\n".join(snippets)
            return None
        except Exception as e:
            # Silently fail to keep the batch induction moving
            return None
