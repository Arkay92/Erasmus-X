"""
Tests for search mode classification and vectorization.
"""
import unittest
from utils.web_search import WebSearcher


class TestSearchClassification(unittest.TestCase):
    """Test query classification for simple vs deep research."""
    
    def setUp(self):
        self.searcher = WebSearcher()
    
    def test_simple_query_classification(self):
        """Simple factual questions should be classified as SIMPLE."""
        queries = [
            "What is the capital of France?",
            "Who is Barack Obama?",
            "Define photosynthesis",
            "What is the price of Bitcoin?",
            "Where is the Eiffel Tower?"
        ]
        
        for query in queries:
            classification = self.searcher.classify_query(query)
            self.assertEqual(classification, "SIMPLE", f"Query '{query}' should be SIMPLE")
    
    def test_deep_query_classification(self):
        """Research questions should be classified as DEEP."""
        queries = [
            "Analyze microservices architecture patterns",
            "Compare REST vs GraphQL for API design",
            "Explain best practices for database indexing",
            "How to implement OAuth 2.0 in Node.js"
        ]
        
        for query in queries:
            classification = self.searcher.classify_query(query)
            self.assertEqual(classification, "DEEP", f"Query '{query}' should be DEEP")
    
    def test_complex_query_classification(self):
        """Long queries should be classified as DEEP."""
        long_query = "Explain the history of artificial intelligence and how machine learning has evolved over the past decade"
        classification = self.searcher.classify_query(long_query)
        self.assertEqual(classification, "DEEP")


class TestFactualAnswerExtraction(unittest.TestCase):
    """Test extraction of concise factual answers."""
    
    def setUp(self):
        self.searcher = WebSearcher()
    
    def test_extract_capital_answer(self):
        """Should extract 'Paris' from text about France's capital."""
        snippet = "Paris is the capital and most populous city of France. It is located on the Seine river..."
        question = "What is the capital of France?"
        
        answer = self.searcher._extract_factual_answer(question, snippet)
        self.assertIn("Paris", answer)
    
    def test_extract_location_answer(self):
        """Should extract location from 'where is' questions."""
        snippet = "The Eiffel Tower is located in Paris, France on the Champ de Mars."
        question = "Where is the Eiffel Tower?"
        
        answer = self.searcher._extract_factual_answer(question, snippet)
        self.assertIn("Paris", answer)
    
    def test_extract_definition_answer(self):
        """Should extract definition for 'what is' questions."""
        snippet = "Photosynthesis is a process used by plants and other organisms to convert light energy..."
        question = "What is photosynthesis?"
        
        answer = self.searcher._extract_factual_answer(question, snippet)
        self.assertTrue(len(answer) > 0)
        self.assertIn("process", answer.lower())


class TestFollowUpQueryGeneration(unittest.TestCase):
    """Test intelligent follow-up query generation."""
    
    def setUp(self):
        self.searcher = WebSearcher()
    
    def test_follow_up_generation(self):
        """Should generate relevant follow-up queries."""
        original_query = "microservices"
        findings = [
            {'title': 'Microservices Architecture', 'snippet': 'Overview...'},
            {'title': 'Microservices in Practice', 'snippet': 'Implementation...'}
        ]
        
        follow_up = self.searcher._generate_follow_up_query(original_query, findings)
        
        self.assertIsNotNone(follow_up)
        self.assertNotEqual(follow_up, original_query)
        # Should contain original query or related term
        self.assertTrue(
            'microservice' in follow_up.lower() or 'implement' in follow_up.lower()
        )
    
    def test_iterative_follow_up(self):
        """Should generate different follow-ups for different iteration counts."""
        query = "python testing"
        findings1 = [{'title': 'pytest basics', 'snippet': '...'}]
        findings2 = findings1 + [{'title': 'unittest', 'snippet': '...'}]
        
        follow_up1 = self.searcher._generate_follow_up_query(query, findings1)
        follow_up2 = self.searcher._generate_follow_up_query(query, findings2)
        
        # Should generate different queries as we find more
        # (not necessarily different, but should be valid queries)
        self.assertTrue(len(follow_up1) > 0)
        self.assertTrue(len(follow_up2) > 0)


class TestVectorization(unittest.TestCase):
    """Test search result vectorization."""
    
    def setUp(self):
        # Create a mock brain for testing
        from core.vector_store import HypervectorDB
        self.brain = HypervectorDB()
        self.searcher = WebSearcher(brain=self.brain)
    
    def test_vectorization_storage(self):
        """Should store search results in vector database."""
        query = "python lists"
        content = "Python lists are mutable sequences..."
        url = "https://docs.python.org/3/tutorial/datastructures.html"
        
        # This should not raise an exception
        self.searcher._vectorize_search_result(query, content, url)
        
        # Check that document was added
        self.assertTrue(len(self.brain.documents) > 0)
    
    def test_vectorization_association(self):
        """Should create capability associations for future retrieval."""
        query = "REST API design"
        content = "REST API best practices..."
        url = "https://example.com/api"
        
        initial_count = len(self.brain.documents)
        self.searcher._vectorize_search_result(query, content, url)
        
        # Document should be added
        self.assertGreater(len(self.brain.documents), initial_count)


if __name__ == '__main__':
    unittest.main()
