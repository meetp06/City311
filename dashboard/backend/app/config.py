"""Central configuration loaded from environment variables.

Everything is designed so the system runs fully in MOCK_MODE without any
real vendor credentials. When MOCK_MODE is false, the adapters attempt real
calls and surface clearly-marked TODOs where final SDK wiring is required.
"""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    """Application settings sourced from the environment."""

    def __init__(self) -> None:
        # Core
        self.mock_mode: bool = _as_bool(os.getenv("MOCK_MODE"), default=True)
        self.public_base_url: str = os.getenv(
            "PUBLIC_BASE_URL", "http://localhost:7860"
        )
        self.service_name: str = "municipal-311-assistant"

        # AWS Bedrock Nova Sonic
        self.aws_access_key_id: str | None = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key: str | None = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_region: str = os.getenv("AWS_REGION", "us-east-1")
        self.aws_bedrock_model_id: str = os.getenv(
            "AWS_BEDROCK_MODEL_ID", "amazon.nova-sonic-v1:0"
        )

        # NVIDIA NIM
        self.nvidia_api_key: str | None = os.getenv("NVIDIA_API_KEY")

        # Cekura
        self.cekura_api_key: str | None = os.getenv("CEKURA_API_KEY")
        self.cekura_base_url: str = os.getenv(
            "CEKURA_BASE_URL", "https://api.cekura.ai"
        )

    @property
    def media_stream_url(self) -> str:
        """Public wss:// URL Twilio should stream media to."""
        base = self.public_base_url.replace("https://", "wss://").replace(
            "http://", "ws://"
        )
        return f"{base}/twilio/media"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
