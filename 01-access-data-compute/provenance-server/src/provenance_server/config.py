"""Application configuration via environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PROVENANCE_", env_file=".env", extra="ignore")

    # Service identity
    service_id: str = "provenance-server-default"
    service_name: str = "GA4GH Provenance Server"
    service_description: str = "Beacon-style API for workflow provenance and data elements"
    service_version: str = "0.1.0"
    site: str = "local"

    # Database
    database_url: str = "sqlite+aiosqlite:///./provenance.db"

    # Federation
    # Comma-separated list of peer node base URLs, e.g.
    # "http://node-b:8001,http://node-c:8002"
    peer_nodes: str = ""

    def get_peer_nodes(self) -> list[str]:
        return [n.strip() for n in self.peer_nodes.split(",") if n.strip()]


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
