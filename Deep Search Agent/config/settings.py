"""
config/settings.py
──────────────────
Centralised configuration using Pydantic Settings.
All values are loaded from environment variables / .env file.
"""
# pydantic settings automatically reads environment variables and .env files , no manual needed 
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    # ── LLM ──────────────────────────────────────────────────
    groq_api_key: str = Field(..., env="GROQ_API_KEY")
    groq_model: str = Field("llama-3.3-70b-versatile", env="GROQ_MODEL")
    groq_fast_model: str = Field("llama-3.1-8b-instant", env="GROQ_FAST_MODEL")

    # ── Web Search ────────────────────────────────────────────
    tavily_api_key: str = Field(..., env="TAVILY_API_KEY")
    tavily_search_depth: str = Field("advanced", env="TAVILY_SEARCH_DEPTH")
    tavily_max_results: int = Field(7, env="TAVILY_MAX_RESULTS")

    # ── Vector DB ─────────────────────────────────────────────
    chroma_persist_dir: str = Field("./data/vector_db", env="CHROMA_PERSIST_DIR")
    chroma_collection_it: str = Field("it_sector_docs", env="CHROMA_COLLECTION_IT")
    chroma_collection_pharma: str = Field("pharma_sector_docs", env="CHROMA_COLLECTION_PHARMA")

    # ── Financial APIs ────────────────────────────────────────
    alpha_vantage_api_key: str = Field("", env="ALPHA_VANTAGE_API_KEY")

    # ── Research Params ───────────────────────────────────────
    min_research_steps: int = Field(5, env="MIN_RESEARCH_STEPS")
    max_research_steps: int = Field(20, env="MAX_RESEARCH_STEPS")
    research_timeout_seconds: int = Field(300, env="RESEARCH_TIMEOUT_SECONDS")

    # ── Output ────────────────────────────────────────────────
    reports_dir: str = Field("./data/reports", env="REPORTS_DIR")
    log_level: str = Field("INFO", env="LOG_LEVEL")

    # ── API Server ────────────────────────────────────────────
    api_host: str = Field("0.0.0.0", env="API_HOST")
    api_port: int = Field(8000, env="API_PORT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

# lru means settings is created once and reuseed forever . Every file that calls get_settings gets the same object 
@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
