"""Local-only development token server for the Virtual Camera control panel.

Never expose on a public network. The API secret stays on the server, not in JS.
"""
from __future__ import annotations

import json
import os
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

PORT = int(os.getenv("AVATAR_CAM_TOKEN_PORT", "8765"))
FRONTEND_ORIGIN = os.getenv("AVATAR_CAM_FRONTEND_ORIGIN", "http://localhost:5173")


def make_token() -> dict[str, str]:
    from livekit import api

    api_key = os.environ["LIVEKIT_API_KEY"]
    api_secret = os.environ["LIVEKIT_API_SECRET"]
    server_url = os.environ["LIVEKIT_URL"]
    agent_name = os.getenv("LIVEKIT_AGENT_NAME", "ai-avatar-loom")
    room_name = f"avatar-cam-{secrets.token_hex(6)}"
    token = (
        api.AccessToken(api_key, api_secret)
        .with_identity(f"operator-{secrets.token_hex(4)}")
        .with_name("Operador de cámara virtual")
        .with_grants(api.VideoGrants(room_join=True, room=room_name, can_publish=True, can_subscribe=True))
        .with_room_config(
            api.RoomConfiguration(agents=[api.RoomAgentDispatch(agent_name=agent_name)])
        )
        .to_jwt()
    )
    return {"serverUrl": server_url, "token": token, "roomName": room_name}


class Handler(BaseHTTPRequestHandler):
    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", FRONTEND_ORIGIN)
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Vary", "Origin")

    def do_OPTIONS(self) -> None:
        if self.headers.get("Origin") != FRONTEND_ORIGIN:
            self.send_error(403, "Origin not allowed")
            return
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:
        if urlparse(self.path).path != "/token":
            self.send_error(404)
            return
        if self.headers.get("Origin") != FRONTEND_ORIGIN:
            self.send_error(403, "Origin not allowed")
            return
        try:
            body = json.dumps(make_token()).encode("utf-8")
        except (KeyError, ValueError) as exc:
            self.send_error(500, f"Invalid LiveKit configuration: {exc}")
            return
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    print(f"Token server: http://127.0.0.1:{PORT} (local only)")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
