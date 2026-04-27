import os
import unittest
from unittest.mock import patch

from core import config
from core.config import Settings
from core.model_clients import AnthropicChatClient, create_model_client


class TestModelConfig(unittest.TestCase):
    def test_remote_model_overrides_local_model(self):
        with patch.dict(os.environ, {
            "LOCAL_MODEL_TYPE": "local-code-model",
            "REMOTE_MODEL_TYPE": "gpt-4.1-mini",
            "REMOTE_MODEL_PROVIDER": "openai",
            "OPENAI_API_KEY": "test-key",
        }, clear=False):
            settings = Settings()

        self.assertEqual(settings.model_name, "gpt-4.1-mini")
        self.assertEqual(settings.model_provider, "openai")
        self.assertEqual(settings.api_key, "test-key")

    def test_remote_agent_model_overrides_local_agent_model(self):
        with patch.dict(os.environ, {
            "LOCAL_AGENT_MODEL_TYPE": "tinyllama",
            "REMOTE_AGENT_MODEL_TYPE": "claude-3-5-haiku-latest",
            "REMOTE_AGENT_MODEL_PROVIDER": "anthropic",
            "ANTHROPIC_API_KEY": "anthropic-key",
        }, clear=False):
            settings = Settings()

        self.assertEqual(settings.agent_model_name, "claude-3-5-haiku-latest")
        self.assertEqual(settings.agent_model_provider, "anthropic")
        self.assertEqual(settings.agent_api_key, "anthropic-key")

    def test_provider_base_urls_are_resolved(self):
        with patch.dict(os.environ, {
            "REMOTE_MODEL_TYPE": "deepseek-chat",
            "REMOTE_MODEL_PROVIDER": "deepseek",
            "DEEPSEEK_API_KEY": "deepseek-key",
        }, clear=False):
            settings = Settings()

        self.assertEqual(settings.api_base_url, "https://api.deepseek.com/v1")
        self.assertEqual(settings.api_key, "deepseek-key")

    def test_anthropic_client_adapter_can_be_selected(self):
        with patch.object(config, "AGENT_MODEL_PROVIDER", "anthropic"), \
             patch.object(config, "AGENT_API_KEY", "key"), \
             patch.object(config, "AGENT_API_BASE_URL", "https://api.anthropic.com"):
            client = create_model_client("agent")

        self.assertIsInstance(client, AnthropicChatClient)

    def test_local_llm_server_options_are_configurable(self):
        with patch.dict(os.environ, {
            "USE_LOCAL_LLM_SERVER": "true",
            "LOCAL_LLM_SERVER_TYPE": "ollama",
            "OLLAMA_API_BASE_URL": "http://127.0.0.1:11434",
        }, clear=False):
            settings = Settings()

        self.assertTrue(settings.use_local_llm_server)
        self.assertEqual(settings.local_llm_server_type, "ollama")
        self.assertEqual(settings.ollama_api_base_url, "http://127.0.0.1:11434")

    def test_local_llm_server_defaults_to_python_loader_mode(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()

        self.assertFalse(settings.use_local_llm_server)
        self.assertEqual(settings.local_llm_server_type, "lmstudio")


if __name__ == "__main__":
    unittest.main()
