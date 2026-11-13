import ast
from pathlib import Path


def test_virtual_camera_python_sources_parse():
    project = Path(__file__).resolve().parents[1]
    for name in ("virtual_cam/token_server.py", "livekit_agent/agent.py"):
        ast.parse((project / name).read_text(encoding="utf-8"))


def test_livekit_token_has_dispatch_and_minimal_grants():
    source = (Path(__file__).resolve().parents[1] / "virtual_cam/token_server.py").read_text()
    assert "RoomAgentDispatch" in source
    assert "127.0.0.1" in source
    assert "api.VideoGrants" in source
    assert "no-store" in source


def test_frontend_discloses_avatar_identity():
    html = (Path(__file__).resolve().parents[1] / "virtual_cam/index.html").read_text()
    assert "ASISTENTE DE IA" in html
