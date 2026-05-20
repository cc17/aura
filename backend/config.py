from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM
    default_model: str = "openai/doubao-1-5-pro-32k-250115"
    supervisor_model: str = "openai/doubao-1-5-pro-32k-250115"
    lite_model: str = "openai/doubao-1-5-lite-32k-250115"
    embedding_model: str = ""  # e.g. "openai/doubao-embedding-large-text-250515"; empty = skip embedding
    ark_api_key: str = ""
    ark_api_base: str = "https://ark.cn-beijing.volces.com/api/v3"
    max_tool_rounds: int = 5
    serper_api_key: str = ""

    # Database (PostgreSQL + pgvector)
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/aura"

    # Auth
    secret_key: str = "change-me-to-a-random-secret"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days
    admin_token: str = ""  # set AURA_ADMIN_TOKEN in .env to enable admin dashboard

    # Memory / context management
    context_max_tokens: int = 25_000
    summarize_threshold: int = 30
    archive_after_days: int = 30

    # Reflection loop
    reflection_score_threshold: int = 7   # 0–10; below this triggers a retry
    reflection_max_loops: int = 3         # hard cap on retry iterations

    # KV cache TTLs (seconds)
    llm_cache_supervisor_ttl: int = 300   # 5 min — routing calls
    llm_cache_reflection_ttl: int = 600   # 10 min — quality evaluation calls
    tool_cache_search_ttl: int = 1800     # 30 min — web search / URL scrape

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    model_config = {"env_prefix": "AURA_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
