"""Runtime configuration loaded from agent-service/.env."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


class DeepSeekConfigurationError(RuntimeError):
    """Raised when generation is requested without an API key."""


@dataclass(frozen=True)
class Settings:
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str
    deepseek_temperature: float

    @property
    def deepseek_configured(self) -> bool:
        return bool(self.deepseek_api_key)


def get_settings() -> Settings:
    return Settings(
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", "").strip(),
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"),
        deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        deepseek_temperature=float(os.getenv("DEEPSEEK_TEMPERATURE", "0.2")),
    )
