import unittest
from unittest.mock import patch

from core import config
from core.local_llm import LocalLLM


class TestLocalLLMServerMode(unittest.TestCase):
    def tearDown(self):
        LocalLLM._instance = None

    def test_lmstudio_server_mode_uses_openai_compatible_endpoint(self):
        LocalLLM._instance = None
        with patch.object(config, "USE_LOCAL_LLM_SERVER", True), \
             patch.object(config, "LOCAL_LLM_SERVER_TYPE", "lmstudio"), \
             patch.object(config, "LOCAL_LLM_SERVER_API_BASE_URL", "http://localhost:1234/v1"), \
             patch.object(config, "LOCAL_LLM_SERVER_API_KEY", "local"):
            llm = LocalLLM(model_name="qwen")
            with patch.object(llm, "_post_json", return_value={"choices": [{"message": {"content": "pong"}}]}) as post:
                result = llm.generate("ping", max_new_tokens=8)

        self.assertEqual(result, "pong")
        self.assertEqual(post.call_args.args[0], "http://localhost:1234/v1/chat/completions")
        self.assertEqual(post.call_args.args[1]["model"], "qwen")

    def test_ollama_server_mode_uses_generate_endpoint(self):
        LocalLLM._instance = None
        with patch.object(config, "USE_LOCAL_LLM_SERVER", True), \
             patch.object(config, "LOCAL_LLM_SERVER_TYPE", "ollama"), \
             patch.object(config, "LOCAL_LLM_SERVER_API_BASE_URL", ""), \
             patch.object(config, "OLLAMA_API_BASE_URL", "http://localhost:11434"):
            llm = LocalLLM(model_name="llama3")
            with patch.object(llm, "_post_json", return_value={"response": "pong"}) as post:
                result = llm.generate("ping", max_new_tokens=8)

        self.assertEqual(result, "pong")
        self.assertEqual(post.call_args.args[0], "http://localhost:11434/api/generate")
        self.assertEqual(post.call_args.args[1]["model"], "llama3")


if __name__ == "__main__":
    unittest.main()
