"""Configurazione centralizzata — legge le variabili dal file .env."""

from __future__ import annotations

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


def _clean_empty_env_vars() -> None:
    """Rimuove le variabili d'ambiente impostate a stringa vuota.

    Claude Code imposta ANTHROPIC_API_KEY="" nell'ambiente di sistema,
    e pydantic-settings la usa al posto del valore nel file .env.
    Rimuovendola, pydantic-settings legge correttamente dal .env.
    """
    for key in list(os.environ):
        if os.environ[key] == "" and key in (
            "ANTHROPIC_API_KEY",
            "BEEHIIV_API_KEY",
            "BEEHIIV_PUBLICATION_ID",
            "SUPABASE_URL",
            "SUPABASE_KEY",
        ):
            del os.environ[key]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Anthropic (Claude)
    anthropic_api_key: str
    anthropic_model: str = "claude-sonnet-4-6"

    # Beehiiv
    beehiiv_api_key: str
    beehiiv_publication_id: str

    # Supabase
    supabase_url: str
    supabase_key: str

    # Newsletter
    newsletter_name: str = "Mondo Certificati"

    # Scraping
    scrape_max_pages: int = 5
    scrape_timeout_ms: int = 30_000
    scrape_cache_path: str = "cache/certificates.json"


def get_settings() -> Settings:
    """Singleton lazy — valida le variabili d'ambiente solo quando serve."""
    global _settings
    if _settings is None:
        _clean_empty_env_vars()
        _settings = Settings()  # type: ignore[call-arg]
    return _settings


_settings: Settings | None = None
