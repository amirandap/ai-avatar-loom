from pathlib import Path

import pytest

from avatar_loom.config import Settings
from avatar_loom.pipeline import generate_video, refresh_job, slugify


SETTINGS = Settings("xai", "grok-4.3", "11", "voice_1", "eleven_multilingual_v2", "hey", "avatar_1")


class FakeEleven:
    def synthesize(self, script, voice_id, model, target):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"synthetic-mp3")
        return target


class FakeHeygen:
    def upload_audio(self, path):
        assert path.read_bytes() == b"synthetic-mp3"
        return "asset_1"

    def generate(self, asset_id, avatar_id, title, resolution, aspect_ratio):
        assert (asset_id, avatar_id) == ("asset_1", "avatar_1")
        return "video_123"

    def status(self, video_id):
        assert video_id == "video_123"
        return {"status": "completed", "video_url": "https://example.org/video.mp4"}

    def download(self, url, target):
        target.write_bytes(b"mp4")
        return target


def test_slugify():
    assert slugify("Reporte: Enero 2026!") == "reporte-enero-2026"


def test_create_and_fetch(tmp_path: Path):
    job = generate_video(script="Hola", title="Demo", output_dir=tmp_path,
                         settings=SETTINGS, eleven=FakeEleven(), heygen=FakeHeygen())
    assert job["video_id"] == "video_123"
    job_path = tmp_path / "demo" / "job.json"
    assert job_path.exists()
    completed = refresh_job(job_path, SETTINGS, heygen=FakeHeygen())
    assert completed["state"] == "completed"
    assert (tmp_path / "demo" / "video.mp4").read_bytes() == b"mp4"
    with pytest.raises(FileExistsError):
        generate_video(script="Hola", title="Demo", output_dir=tmp_path,
                       settings=SETTINGS, eleven=FakeEleven(), heygen=FakeHeygen())


def test_missing_voice(tmp_path):
    settings = Settings("xai", "grok-4.3", "11", "", "eleven_multilingual_v2", "hey", "avatar")
    with pytest.raises(ValueError, match="VOICE_ID"):
        generate_video(script="Hola", title="Demo", output_dir=tmp_path,
                       settings=settings, eleven=FakeEleven(), heygen=FakeHeygen())
