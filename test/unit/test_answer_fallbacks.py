import unittest

from core.answer_fallbacks import factual_fallback


class TestAnswerFallbacks(unittest.TestCase):
    def test_http_prompt_variants_are_caught(self):
        prompts = [
            "What is HTTP?",
            "What does HTTP stand for?",
            "http stand for",
            "Define HTTP",
        ]

        for prompt in prompts:
            answer = factual_fallback(prompt)
            self.assertIsNotNone(answer, prompt)
            self.assertIn("HyperText Transfer Protocol", answer)


if __name__ == "__main__":
    unittest.main()
