"""HTTP adapters for xAI, ElevenLabs and HeyGen official APIs.

Note: remote API contracts, quotas and media generation costs can change.
"""
from __future__ import annotations

import time
import mimetypes
from pathlib import Path
from typing import Any

import httpx


class APIError(RuntimeError):
    pass


def _check(response: httpx.Response, provider: str) -> httpx.Response:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        # No keys are logged. Cap the error body to avoid leaking remote content.
        raise APIError(f"{provider} HTTP {response.status_code}: {response.text[:400]}") from exc
    return response


def _data(raw: dict[str, Any]) -> dict[str, Any]:
    data = raw.get("data")
    return data if isinstance(data, dict) else raw


class XAIClient:
    def __init__(self, api_key: str, model: str = "grok-4.3", http: httpx.Client | None = None):
        self.api_key, self.model = api_key, model
        self.http = http or httpx.Client(timeout=100)

    def draft(self, brief: str, target_seconds: int = 90, style: str = "natural") -> str:
        if not brief.strip():
            raise ValueError("The brief cannot be blank")
        response = _check(
            self.http.post(
                "https://api.x.ai/v1/responses",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "input": [
                        {"role": "system", "content": (
                            "Redactas guiones para videos tipo Loom, en primera persona y en español "
                            "natural dominicano sin clichés. Devuelve solamente el texto para ser "
                            "pronunciado en voz alta, sin Markdown, acotaciones ni efectos. No inventes "
                            "resultados, cifras o experiencias personales. Si no hay datos, evítalos."
                        )},
                        {"role": "user", "content": (
                            f"Objetivo y hechos:\n{brief}\n\nDuración aproximada: "
                            f"{target_seconds} segundos. Estilo: {style}. "
                            "Inicio directo, desarrollo útil y cierre breve."
                        )},
                    ],
                },
            ),
            "xAI",
        ).json()
        parts: list[str] = []
        for item in response.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text" and content.get("text"):
                    parts.append(content["text"])
        result = "\n".join(parts).strip()
        if not result:
            raise APIError("xAI returned no readable output_text")
        return result


class ElevenLabsClient:
    def __init__(self, api_key: str, http: httpx.Client | None = None):
        self.api_key = api_key
        self.http = http or httpx.Client(timeout=180)

    def clone_voice(self, name: str, recordings: list[Path]) -> str:
        if not name.strip() or not recordings:
            raise ValueError("Voice clone requires a name and audio recordings")
        # Keep files open for the whole multipart request.
        from contextlib import ExitStack
        with ExitStack() as stack:
            files = [("files", (p.name, stack.enter_context(p.open("rb")),
                             mimetypes.guess_type(p.name)[0] or "application/octet-stream"))
                     for p in recordings]
            response = _check(
                self.http.post(
                    "https://api.elevenlabs.io/v1/voices/add",
                    headers={"xi-api-key": self.api_key},
                    data={"name": name}, files=files,
                ),
                "ElevenLabs",
            )
        voice_id = response.json().get("voice_id")
        if not voice_id:
            raise APIError("ElevenLabs did not return a voice_id")
        return voice_id

    def synthesize(self, script: str, voice_id: str, model: str, target: Path) -> Path:
        if len(script) > 9000:
            raise ValueError("Script exceeds 9000 chars; split into separate Looms")
        if not script.strip() or not voice_id:
            raise ValueError("Script and cloned voice ID are required")
        response = _check(
            self.http.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                params={"output_format": "mp3_44100_128"},
                headers={"xi-api-key": self.api_key, "Content-Type": "application/json"},
                json={"text": script, "model_id": model},
            ),
            "ElevenLabs",
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(response.content)
        return target


class HeyGenClient:
    def __init__(self, api_key: str, http: httpx.Client | None = None):
        self.api_key = api_key
        self.http = http or httpx.Client(timeout=120)

    @property
    def headers(self) -> dict[str, str]:
        return {"X-Api-Key": self.api_key}

    def upload_audio(self, path: Path) -> str:
        with path.open("rb") as stream:
            response = _check(
                self.http.post(
                    "https://api.heygen.com/v3/assets",
                    headers=self.headers,
                    files={"file": (path.name, stream, "audio/mpeg")},
                ),
                "HeyGen upload",
            )
        raw = response.json()
        d = _data(raw)
        asset_id = d.get("asset_id") or d.get("id") or d.get("asset", {}).get("id")
        if not asset_id:
            raise APIError(f"HeyGen upload did not include an asset id: {str(raw)[:300]}")
        return str(asset_id)

    def generate(self, asset_id: str, avatar_id: str, title: str, resolution: str,
                 aspect_ratio: str) -> str:
        payload = {
            "type": "avatar", "avatar_id": avatar_id, "audio_asset_id": asset_id,
            "title": title, "resolution": resolution, "aspect_ratio": aspect_ratio,
        }
        response = _check(
            self.http.post(
                "https://api.heygen.com/v3/videos",
                headers={**self.headers, "Content-Type": "application/json"},
                json=payload,
            ),
            "HeyGen generate",
        )
        d = _data(response.json())
        video_id = d.get("video_id") or d.get("id")
        if not video_id:
            raise APIError("HeyGen did not return a video_id")
        return str(video_id)

    def status(self, video_id: str) -> dict[str, Any]:
        response = _check(
            self.http.get(f"https://api.heygen.com/v3/videos/{video_id}", headers=self.headers),
            "HeyGen status",
        )
        return _data(response.json())

    def await_video(self, video_id: str, poll_seconds: int = 30,
                    max_minutes: int = 30) -> dict[str, Any]:
        deadline = time.monotonic() + max_minutes * 60
        while True:
            data = self.status(video_id)
            state = str(data.get("status", "")).lower()
            if state in ("completed", "success", "done"):
                if not (data.get("video_url") or data.get("url")):
                    raise APIError("Video marked completed without downloadable video_url")
                return data
            if state in ("failed", "error"):
                raise APIError("HeyGen video failed: " + str(data.get("failure_message") or data))
            if time.monotonic() >= deadline:
                raise TimeoutError(f"HeyGen video {video_id} still {state or 'pending'}; check later")
            time.sleep(poll_seconds)

    def download(self, url: str, target: Path) -> Path:
        if not url.startswith("https://"):
            raise ValueError("Expected HTTPS video URL")
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_suffix(target.suffix + ".part")
        with self.http.stream("GET", url, follow_redirects=True, timeout=300) as response:
            _check(response, "HeyGen video download")
            with partial.open("wb") as stream:
                for chunk in response.iter_bytes():
                    stream.write(chunk)
        partial.replace(target)
        return target
