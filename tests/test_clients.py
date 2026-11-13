import json
from pathlib import Path

import httpx

from avatar_loom.clients import ElevenLabsClient, HeyGenClient, XAIClient


def test_xai_responses_request():
    def handler(req):
        payload = json.loads(req.content)
        assert req.url.path == "/v1/responses"
        assert payload["model"] == "grok-4.3"
        assert req.headers["authorization"] == "Bearer secret"
        return httpx.Response(200, json={"output": [
            {"content": [{"type": "output_text", "text": "Hola equipo"}]}
        ]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert XAIClient("secret", http=client).draft("Explicar reunión") == "Hola equipo"


def test_eleven_tts(tmp_path: Path):
    def handler(req):
        assert req.url.path.endswith("/voice_1")
        assert req.headers["xi-api-key"] == "secret"
        assert json.loads(req.content)["text"] == "Hola"
        return httpx.Response(200, content=b"mp3 bytes")
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        target = tmp_path / "narration.mp3"
        ElevenLabsClient("secret", http=client).synthesize(
            "Hola", "voice_1", "eleven_multilingual_v2", target
        )
        assert target.read_bytes() == b"mp3 bytes"


def test_heygen_upload_generate_and_status(tmp_path: Path):
    def handler(req):
        if req.url.path == "/v3/assets":
            assert b"narration.mp3" in req.content
            return httpx.Response(200, json={"data": {"id": "asset_1"}})
        if req.url.path == "/v3/videos" and req.method == "POST":
            payload = json.loads(req.content)
            assert payload["audio_asset_id"] == "asset_1"
            assert payload["avatar_id"] == "avatar_1"
            return httpx.Response(200, json={"data": {"video_id": "vid_1"}})
        if req.url.path == "/v3/videos/vid_1":
            return httpx.Response(200, json={"status": "completed", "video_url": "https://cdn.example.org/clip.mp4"})
        raise AssertionError(f"Unexpected HTTP call {req.method} {req.url}")
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        api = HeyGenClient("secret", http=client)
        f = tmp_path / "narration.mp3"
        f.write_bytes(b"audio")
        asset_id = api.upload_audio(f)
        vid = api.generate(asset_id, "avatar_1", "test", "1080p", "16:9")
        assert vid == "vid_1"
        assert api.status(vid)["status"] == "completed"
