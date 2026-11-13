"""Centralized configuration without embedding secrets in the repository."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


@dataclass(frozen=True)
class Settings:
    xai_key: str
    xai_model: str
    eleven_key: str
    eleven_voice_id: str
    eleven_model: str
    heygen_key: str
    heygen_avatar_id: str

    @classmethod
    def load(cls) -> "Settings":
        load_dotenv()
        return cls(
            xai_key=env("XAI_API_KEY"),
            xai_model=env("XAI_MODEL", "grok-4.3"),
            eleven_key=env("ELEVENLABS_API_KEY"),
            eleven_voice_id=env("ELEVENLABS_VOICE_ID"),
            eleven_model=env("ELEVENLABS_MODEL", "eleven_multilingual_v2"),
            heygen_key=env("HEYGEN_API_KEY"),
            heygen_avatar_id=env("HEYGEN_AVATAR_ID"),
        )

    def require(self, *keys: str) -> None:
        missing = [key for key in keys if not getattr(self, key)]
        if missing:
            raise ValueError("Missing environment values: " + ", ".join(missing))
