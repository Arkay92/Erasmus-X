from ddgs import DDGS

class WebSearcher:
    def __init__(self):
        self.ddgs = DDGS()

    def search(self, query, max_results=3):
        print(f"\n[Headless Search] Exploring internet for context on: '{query}'...")
        try:
            results = list(self.ddgs.text(query, max_results=max_results))
            snippets = []
            for r in results:
                snippets.append(f"Source: {r.get('title')}\nContent: {r.get('body', '')[:400]}...")
            
            if snippets:
                print(f"[Headless Search] Found {len(snippets)} relevant documents!")
                return "\n\n".join(snippets)
            else:
                print("[Headless Search] No results returned by API.")
                return None
        except Exception as e:
            print(f"[Search Failed]: {e}")
            return None
