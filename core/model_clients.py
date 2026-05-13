import json
import urllib.error
import urllib.request
from types import SimpleNamespace

from openai import OpenAI

from core import config


OPENAI_COMPATIBLE_PROVIDERS = {"local", "openai", "deepseek", "kimi", "nvidia"}


def create_model_client(role: str = "main"):
    """Create a chat-completions client for the configured provider."""
    provider = config.MODEL_PROVIDER
    api_key = config.API_KEY
    base_url = config.API_BASE_URL
    if role == "agent":
        provider = config.AGENT_MODEL_PROVIDER
        api_key = config.AGENT_API_KEY
        base_url = config.AGENT_API_BASE_URL

    if provider == "anthropic":
        return AnthropicChatClient(api_key=api_key, base_url=base_url, timeout=config.REQUEST_TIMEOUT)
    if provider in OPENAI_COMPATIBLE_PROVIDERS:
        return OpenAI(api_key=api_key or "local", base_url=base_url, timeout=config.REQUEST_TIMEOUT)
    raise ValueError(f"Unsupported model provider '{provider}'. Use local, openai, anthropic, deepseek, or kimi.")


class AnthropicChatClient:
    """Small adapter that exposes Anthropic through the OpenAI chat-completions shape."""

    def __init__(self, api_key: str, base_url: str = "https://api.anthropic.com", timeout: int = 300):
        self.chat = SimpleNamespace(completions=_AnthropicChatCompletions(api_key, base_url, timeout))


class _AnthropicChatCompletions:
    def __init__(self, api_key: str, base_url: str, timeout: int):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def create(self, model: str, messages: list[dict], temperature: float = 0.1, max_tokens: int | None = None, timeout: int | None = None, **_kwargs):
        system_parts = []
        anthropic_messages = []
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            if role == "system":
                system_parts.append(str(content))
            else:
                anthropic_messages.append({
                    "role": "assistant" if role == "assistant" else "user",
                    "content": str(content),
                })

        payload = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": max_tokens or config.MAX_TOKENS_GENERATION,
            "temperature": temperature,
        }
        if system_parts:
            payload["system"] = "\n\n".join(system_parts)

        request = urllib.request.Request(
            f"{self.base_url}/v1/messages",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "content-type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout or self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Anthropic API error {exc.code}: {body}") from exc

        text_parts = [
            block.get("text", "")
            for block in data.get("content", [])
            if block.get("type") == "text"
        ]
        text = "\n".join(part for part in text_parts if part)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
            raw=data,
        )
