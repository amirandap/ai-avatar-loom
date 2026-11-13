"""Generate narration + avatar video with restart-safe job metadata."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .clients import ElevenLabsClient, HeyGenClient
from .config import Settings


def slugify(text: str) -> str:
    return (re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "video")[:65]


def generate_video(*, script: str, title: str, output_dir: Path, settings: Settings,
                   avatar_id: str | None = None, voice_id: str | None = None,
                   resolution: str = "1080p", aspect_ratio: str = "16:9",
                   eleven: ElevenLabsClient | None = None,
                   heygen: HeyGenClient | None = None) -> dict[str, Any]:
    settings.require("eleven_key", "heygen_key")
    avatar = avatar_id or settings.heygen_avatar_id
    voice = voice_id or settings.eleven_voice_id
    if not avatar or not voice:
        raise ValueError("HEYGEN_AVATAR_ID and ELEVENLABS_VOICE_ID are required")
    if resolution not in {"720p", "1080p"} or aspect_ratio not in {"16:9", "9:16"}:
        raise ValueError("Unsupported resolution / aspect_ratio")

    job_dir = output_dir / slugify(title)
    job_dir.mkdir(parents=True, exist_ok=True)
    audio_path, video_path = job_dir / "narration.mp3", job_dir / "video.mp4"
    metadata_path = job_dir / "job.json"
    if metadata_path.exists():
        raise FileExistsError(f"Job already exists: {metadata_path}. Use a unique title")

    eleven = eleven or ElevenLabsClient(settings.eleven_key)
    heygen = heygen or HeyGenClient(settings.heygen_key)
    job: dict[str, Any] = {
        "title": title, "avatar_id": avatar, "voice_id": voice,
        "resolution": resolution, "aspect_ratio": aspect_ratio,
        "state": "created", "script": script,
    }

    def save() -> None:
        metadata_path.write_text(json.dumps(job, indent=2, ensure_ascii=False) + "\n",
                                 encoding="utf-8")

    save()
    eleven.synthesize(script, voice, settings.eleven_model, audio_path)
    job["state"] = "audio_created"
    save()
    asset_id = heygen.upload_audio(audio_path)
    job["audio_asset_id"] = asset_id
    save()
    video_id = heygen.generate(asset_id, avatar, title, resolution, aspect_ratio)
    job["video_id"] = video_id
    job["state"] = "submitted"
    save()
    # Retry status without paying for another video: avatar-loom status --job job.json
    return job


def refresh_job(job_path: Path, settings: Settings, *, download: bool = True,
                heygen: HeyGenClient | None = None) -> dict[str, Any]:
    settings.require("heygen_key")
    job = json.loads(job_path.read_text(encoding="utf-8"))
    heygen = heygen or HeyGenClient(settings.heygen_key)
    data = heygen.status(job["video_id"])
    state = str(data.get("status", "pending")).lower()
    job["state"] = state
    job["video_url"] = data.get("video_url") or data.get("url")
    if download and state in ("completed", "success", "done") and job["video_url"]:
        target = job_path.parent / "video.mp4"
        if not target.is_file():
            heygen.download(job["video_url"], target)
        job["local_video"] = str(target)
    job_path.write_text(json.dumps(job, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    return job
