import os
from dataclasses import dataclass, field
from typing import Dict


def _load_dotenv(path: str = ".env") -> None:
    """Small .env loader to avoid making config depend on python-dotenv."""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


_load_dotenv()


def _first_env(*names: str, default: str = "") -> str:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


PROVIDER_BASE_URLS = {
    "local": "http://localhost:12345/v1",
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com",
    "deepseek": "https://api.deepseek.com/v1",
    "kimi": "https://api.moonshot.ai/v1",
    "nvidia": "https://integrate.api.nvidia.com/v1",
}


@dataclass(frozen=True)
class Settings:
    # API Configuration
    local_model_provider: str = field(default_factory=lambda: os.getenv("LOCAL_MODEL_PROVIDER", "local").lower())
    remote_model_provider: str = field(default_factory=lambda: os.getenv("REMOTE_MODEL_PROVIDER", "").lower())
    local_agent_model_provider: str = field(default_factory=lambda: os.getenv("LOCAL_AGENT_MODEL_PROVIDER", os.getenv("LOCAL_MODEL_PROVIDER", "local")).lower())
    remote_agent_model_provider: str = field(default_factory=lambda: os.getenv("REMOTE_AGENT_MODEL_PROVIDER", os.getenv("REMOTE_MODEL_PROVIDER", "")).lower())
    local_model_type: str = field(default_factory=lambda: _first_env("LOCAL_MODEL_TYPE", "MODEL_NAME", default="local-model"))
    remote_model_type: str = field(default_factory=lambda: os.getenv("REMOTE_MODEL_TYPE", ""))
    local_agent_model_type: str = field(default_factory=lambda: _first_env("LOCAL_AGENT_MODEL_TYPE", "LOCAL_LLM_TYPE", default="tinyllama"))
    remote_agent_model_type: str = field(default_factory=lambda: os.getenv("REMOTE_AGENT_MODEL_TYPE", ""))
    model_provider: str = field(init=False)
    agent_model_provider: str = field(init=False)
    model_name: str = field(init=False)
    agent_model_name: str = field(init=False)
    api_base_url: str = field(init=False)
    agent_api_base_url: str = field(init=False)
    api_key: str = field(init=False)
    agent_api_key: str = field(init=False)
    fast_model_name: str = field(init=False)
    specialized_models: Dict[str, str] = field(default_factory=lambda: {
        "nextjs": os.getenv("MODEL_NEXTJS", ""),
        "fastapi": os.getenv("MODEL_FASTAPI", ""),
        "rust": os.getenv("MODEL_RUST", ""),
        "go": os.getenv("MODEL_GO", ""),
        "php": os.getenv("MODEL_PHP", ""),
        "dotnet": os.getenv("MODEL_DOTNET", ""),
    })

    # Storage Configuration
    default_runtime_root: str = field(default_factory=lambda: os.getenv("DEFAULT_RUNTIME_ROOT", "E:/erasmus_cell_runtime"))
    default_model_cache_dir: str = field(default_factory=lambda: os.getenv("DEFAULT_MODEL_CACHE_DIR", "E:/models"))
    runtime_root: str = field(init=False)
    brain_storage_path: str = field(init=False)
    model_cache_dir: str = field(init=False)
    request_cache_path: str = field(init=False)
    sandbox_root: str = field(init=False)
    reasoning_lessons_storage: str = field(init=False)

    request_cache_enabled: bool = field(default_factory=lambda: _env_bool("REQUEST_CACHE_ENABLED", True))
    request_cache_max_bytes: int = field(default_factory=lambda: _env_int("REQUEST_CACHE_MAX_BYTES", 100_000_000))
    request_cache_ttl_seconds: int = field(default_factory=lambda: _env_int("REQUEST_CACHE_TTL_SECONDS", 24 * 3600))
    request_cache_version: str = field(default_factory=lambda: os.getenv("REQUEST_CACHE_VERSION", "v13"))
    task_queue_workers: int = field(default_factory=lambda: _env_int("TASK_QUEUE_WORKERS", 4))

    # Hypervector Configuration
    hv_dimensions: int = field(default_factory=lambda: _env_int("HV_DIMENSIONS", 10000))
    vector_search_threshold: float = field(default_factory=lambda: _env_float("VECTOR_SEARCH_THRESHOLD", 0.15))
    top_k_results: int = field(default_factory=lambda: _env_int("TOP_K_RESULTS", 3))

    # Agent Configuration
    max_history_len: int = field(default_factory=lambda: _env_int("MAX_HISTORY_LEN", 2))
    max_context_history_chars: int = field(default_factory=lambda: _env_int("MAX_CONTEXT_HISTORY_CHARS", 2000))
    max_retrieved_memories: int = field(default_factory=lambda: _env_int("MAX_RETRIEVED_MEMORIES", 1))
    max_tokens_generation: int = field(default_factory=lambda: _env_int("MAX_TOKENS_GENERATION", 1024))
    temperature: float = field(default_factory=lambda: _env_float("TEMPERATURE", 0.7))
    request_timeout: int = field(default_factory=lambda: _env_int("REQUEST_TIMEOUT", 300))
    reasoning_timeout: int = field(default_factory=lambda: _env_int("REASONING_TIMEOUT", 5))
    initial_turn_max_tokens: int = field(default_factory=lambda: _env_int("INITIAL_TURN_MAX_TOKENS", 512))

    cache_threshold: float = field(default_factory=lambda: _env_float("CACHE_THRESHOLD", 0.65))
    enable_prompt_compression: bool = field(default_factory=lambda: _env_bool("ENABLE_PROMPT_COMPRESSION", True))
    compression_enabled: bool = field(default_factory=lambda: _env_bool("COMPRESSION_ENABLED", True))
    compression_debug: bool = field(default_factory=lambda: _env_bool("COMPRESSION_DEBUG", True))

    enable_local_llm: bool = field(default_factory=lambda: _env_bool("ENABLE_LOCAL_LLM", False))
    use_local_llm_server: bool = field(default_factory=lambda: _env_bool("USE_LOCAL_LLM_SERVER", False))
    local_llm_server_type: str = field(default_factory=lambda: os.getenv("LOCAL_LLM_SERVER_TYPE", "lmstudio").lower())
    lmstudio_api_base_url: str = field(default_factory=lambda: os.getenv("LMSTUDIO_API_BASE_URL", "http://localhost:1234/v1"))
    ollama_api_base_url: str = field(default_factory=lambda: os.getenv("OLLAMA_API_BASE_URL", "http://localhost:11434"))
    local_llm_server_api_base_url: str = field(default_factory=lambda: os.getenv("LOCAL_LLM_SERVER_API_BASE_URL", ""))
    local_llm_server_api_key: str = field(default_factory=lambda: os.getenv("LOCAL_LLM_SERVER_API_KEY", "local"))
    enable_web_search: bool = field(default_factory=lambda: _env_bool("ENABLE_WEB_SEARCH", False))
    local_llm_type: str = field(init=False)
    sandbox_enforced: bool = field(default_factory=lambda: _env_bool("SANDBOX_ENFORCED", True))
    sandbox_retention_hours: int = field(default_factory=lambda: _env_int("SANDBOX_RETENTION_HOURS", 24))

    simple_query_limit: int = field(default_factory=lambda: _env_int("SIMPLE_QUERY_LIMIT", 15))
    dynamic_only_keywords: list[str] = field(default_factory=lambda: os.getenv(
        "DYNAMIC_ONLY_KEYWORDS",
        "latest,news,price,status,current,today,happening,update",
    ).split(","))
    force_deep_threshold: float = field(default_factory=lambda: _env_float("FORCE_DEEP_THRESHOLD", 0.25))

    operating_mode: str = field(default_factory=lambda: os.getenv("OPERATING_MODE", "FAST"))
    stop_sequences: list[str] = field(default_factory=lambda: ["\nYou:"])
    fast_mode_context_tokens: int = field(default_factory=lambda: _env_int("FAST_MODE_CONTEXT_TOKENS", 512))
    fast_mode_output_tokens: int = field(default_factory=lambda: _env_int("FAST_MODE_OUTPUT_TOKENS", 64))
    mid_mode_context_tokens: int = field(default_factory=lambda: _env_int("MID_MODE_CONTEXT_TOKENS", 1024))
    mid_mode_output_tokens: int = field(default_factory=lambda: _env_int("MID_MODE_OUTPUT_TOKENS", 256))
    deep_mode_context_tokens: int = field(default_factory=lambda: _env_int("DEEP_MODE_CONTEXT_TOKENS", 2048))
    deep_mode_output_tokens: int = field(default_factory=lambda: _env_int("DEEP_MODE_OUTPUT_TOKENS", 512))

    max_repair_history_tokens: int = field(default_factory=lambda: _env_int("MAX_REPAIR_HISTORY_TOKENS", 600))
    critic_report_limit: int = field(default_factory=lambda: _env_int("CRITIC_REPORT_LIMIT", 500))
    enable_autonomous_synthesis: bool = field(default_factory=lambda: _env_bool("ENABLE_AUTONOMOUS_SYNTHESIS", True))
    synthesis_threshold: float = field(default_factory=lambda: _env_float("SYNTHESIS_THRESHOLD", 0.8))
    association_recall_threshold: float = field(default_factory=lambda: _env_float("ASSOCIATION_RECALL_THRESHOLD", 0.35))
    max_project_retries: int = field(default_factory=lambda: _env_int("MAX_PROJECT_RETRIES", 8))
    max_critic_cycles: int = field(default_factory=lambda: _env_int("MAX_CRITIC_CYCLES", 3))

    enable_reasoning_engine: bool = field(default_factory=lambda: _env_bool("ENABLE_REASONING_ENGINE", True))
    max_reasoning_lessons_context: int = field(default_factory=lambda: _env_int("MAX_REASONING_LESSONS_CONTEXT", 3))
    reasoning_evaluation_threshold: int = field(default_factory=lambda: _env_int("REASONING_EVALUATION_THRESHOLD", 80))

    def __post_init__(self) -> None:
        model_provider = (self.remote_model_provider or "openai") if self.remote_model_type else self.local_model_provider
        agent_model_provider = (self.remote_agent_model_provider or self.remote_model_provider or "openai") if self.remote_agent_model_type else self.local_agent_model_provider
        model_name = self.remote_model_type or self.local_model_type
        agent_model_name = self.remote_agent_model_type or self.local_agent_model_type
        object.__setattr__(self, "model_provider", model_provider or "local")
        object.__setattr__(self, "agent_model_provider", agent_model_provider or self.model_provider)
        object.__setattr__(self, "model_name", model_name)
        object.__setattr__(self, "agent_model_name", agent_model_name)
        object.__setattr__(self, "api_base_url", self._resolve_base_url(self.model_provider, role_prefix="MODEL"))
        object.__setattr__(self, "agent_api_base_url", self._resolve_base_url(self.agent_model_provider, role_prefix="AGENT_MODEL"))
        object.__setattr__(self, "api_key", self._resolve_api_key(self.model_provider, role_prefix="MODEL"))
        object.__setattr__(self, "agent_api_key", self._resolve_api_key(self.agent_model_provider, role_prefix="AGENT_MODEL"))
        object.__setattr__(self, "fast_model_name", _first_env("FAST_MODEL_NAME", default=model_name))
        object.__setattr__(self, "local_llm_type", agent_model_name if not self.remote_agent_model_type else self.local_agent_model_type)

        runtime_root = os.getenv("ERASMUS_RUNTIME_ROOT", self.default_runtime_root)
        object.__setattr__(self, "runtime_root", runtime_root)
        object.__setattr__(self, "brain_storage_path", os.getenv(
            "BRAIN_STORAGE_PATH",
            os.path.join(runtime_root, "memories", "agent_brain.pt"),
        ))
        object.__setattr__(self, "model_cache_dir", os.getenv("MODEL_CACHE_DIR", self.default_model_cache_dir))
        object.__setattr__(self, "request_cache_path", os.getenv(
            "REQUEST_CACHE_PATH",
            os.path.join(runtime_root, "memories", "request_cache.json"),
        ))
        object.__setattr__(self, "sandbox_root", os.getenv("SANDBOX_ROOT", os.path.join(runtime_root, "sandboxes")))
        object.__setattr__(self, "reasoning_lessons_storage", os.getenv(
            "REASONING_LESSONS_STORAGE",
            os.path.join(runtime_root, "memories", "reasoning_lessons.json"),
        ))

    def _resolve_base_url(self, provider: str, role_prefix: str) -> str:
        legacy = "API_BASE_URL" if role_prefix == "MODEL" else "AGENT_API_BASE_URL"
        return _first_env(
            f"{role_prefix}_API_BASE_URL",
            f"{provider.upper()}_API_BASE_URL",
            legacy,
            default=PROVIDER_BASE_URLS.get(provider, PROVIDER_BASE_URLS["local"]),
        )

    def _resolve_api_key(self, provider: str, role_prefix: str) -> str:
        legacy = "API_KEY" if role_prefix == "MODEL" else "AGENT_API_KEY"
        return _first_env(
            f"{role_prefix}_API_KEY",
            f"{provider.upper()}_API_KEY",
            legacy,
            default="local" if provider == "local" else "",
        )


settings = Settings()

# Backwards-compatible module constants. Existing code imports config.X directly.
API_BASE_URL = settings.api_base_url
AGENT_API_BASE_URL = settings.agent_api_base_url
API_KEY = settings.api_key
AGENT_API_KEY = settings.agent_api_key
MODEL_PROVIDER = settings.model_provider
AGENT_MODEL_PROVIDER = settings.agent_model_provider
LOCAL_MODEL_TYPE = settings.local_model_type
REMOTE_MODEL_TYPE = settings.remote_model_type
LOCAL_AGENT_MODEL_TYPE = settings.local_agent_model_type
REMOTE_AGENT_MODEL_TYPE = settings.remote_agent_model_type
MODEL_NAME = settings.model_name
FAST_MODEL_NAME = settings.fast_model_name
AGENT_MODEL_NAME = settings.agent_model_name
SPECIALIZED_MODELS = settings.specialized_models

DEFAULT_RUNTIME_ROOT = settings.default_runtime_root
DEFAULT_MODEL_CACHE_DIR = settings.default_model_cache_dir
RUNTIME_ROOT = settings.runtime_root
BRAIN_STORAGE_PATH = settings.brain_storage_path
MODEL_CACHE_DIR = settings.model_cache_dir
REQUEST_CACHE_ENABLED = settings.request_cache_enabled
REQUEST_CACHE_PATH = settings.request_cache_path
REQUEST_CACHE_MAX_BYTES = settings.request_cache_max_bytes
REQUEST_CACHE_TTL_SECONDS = settings.request_cache_ttl_seconds
REQUEST_CACHE_VERSION = settings.request_cache_version
TASK_QUEUE_WORKERS = settings.task_queue_workers

HV_DIMENSIONS = settings.hv_dimensions
VECTOR_SEARCH_THRESHOLD = settings.vector_search_threshold
TOP_K_RESULTS = settings.top_k_results

MAX_HISTORY_LEN = settings.max_history_len
MAX_CONTEXT_HISTORY_CHARS = settings.max_context_history_chars
MAX_RETRIEVED_MEMORIES = settings.max_retrieved_memories
MAX_TOKENS_GENERATION = settings.max_tokens_generation
TEMPERATURE = settings.temperature
REQUEST_TIMEOUT = settings.request_timeout
REASONING_TIMEOUT = settings.reasoning_timeout
INITIAL_TURN_MAX_TOKENS = settings.initial_turn_max_tokens
CACHE_THRESHOLD = settings.cache_threshold

ENABLE_PROMPT_COMPRESSION = settings.enable_prompt_compression
COMPRESSION_ENABLED = settings.compression_enabled
COMPRESSION_DEBUG = settings.compression_debug

ENABLE_LOCAL_LLM = settings.enable_local_llm
USE_LOCAL_LLM_SERVER = settings.use_local_llm_server
LOCAL_LLM_SERVER_TYPE = settings.local_llm_server_type
LMSTUDIO_API_BASE_URL = settings.lmstudio_api_base_url
OLLAMA_API_BASE_URL = settings.ollama_api_base_url
LOCAL_LLM_SERVER_API_BASE_URL = settings.local_llm_server_api_base_url
LOCAL_LLM_SERVER_API_KEY = settings.local_llm_server_api_key
ENABLE_WEB_SEARCH = settings.enable_web_search
LOCAL_LLM_TYPE = settings.local_llm_type
SANDBOX_ENFORCED = settings.sandbox_enforced
SANDBOX_ROOT = settings.sandbox_root
SANDBOX_RETENTION_HOURS = settings.sandbox_retention_hours

SIMPLE_QUERY_LIMIT = settings.simple_query_limit
DYNAMIC_ONLY_KEYWORDS = settings.dynamic_only_keywords
FORCE_DEEP_THRESHOLD = settings.force_deep_threshold
OPERATING_MODE = settings.operating_mode
STOP_SEQUENCES = settings.stop_sequences
FAST_MODE_CONTEXT_TOKENS = settings.fast_mode_context_tokens
FAST_MODE_OUTPUT_TOKENS = settings.fast_mode_output_tokens
MID_MODE_CONTEXT_TOKENS = settings.mid_mode_context_tokens
MID_MODE_OUTPUT_TOKENS = settings.mid_mode_output_tokens
DEEP_MODE_CONTEXT_TOKENS = settings.deep_mode_context_tokens
DEEP_MODE_OUTPUT_TOKENS = settings.deep_mode_output_tokens

MAX_REPAIR_HISTORY_TOKENS = settings.max_repair_history_tokens
CRITIC_REPORT_LIMIT = settings.critic_report_limit
ENABLE_AUTONOMOUS_SYNTHESIS = settings.enable_autonomous_synthesis
SYNTHESIS_THRESHOLD = settings.synthesis_threshold
ASSOCIATION_RECALL_THRESHOLD = settings.association_recall_threshold
MAX_PROJECT_RETRIES = settings.max_project_retries
MAX_CRITIC_CYCLES = settings.max_critic_cycles

ENABLE_REASONING_ENGINE = settings.enable_reasoning_engine
REASONING_LESSONS_STORAGE = settings.reasoning_lessons_storage
MAX_REASONING_LESSONS_CONTEXT = settings.max_reasoning_lessons_context
REASONING_EVALUATION_THRESHOLD = settings.reasoning_evaluation_threshold
