"""Realtime Grok voice agent with optional LemonSlice video avatar.

Run: python livekit_agent/agent.py dev
Requires LiveKit credentials, xAI, ElevenLabs, and LemonSlice.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from livekit import agents
from livekit.agents import Agent, AgentServer, AgentSession, inference
from livekit.plugins import elevenlabs, lemonslice, xai

load_dotenv()
if not os.environ.get("ELEVEN_API_KEY") and os.environ.get("ELEVENLABS_API_KEY"):
    os.environ["ELEVEN_API_KEY"] = os.environ["ELEVENLABS_API_KEY"]

DEFAULT_PROMPT = (
    "Eres un asistente de IA identificado como tal, autorizado por su propietario. "
    "No te hagas pasar por una persona real ni declares experiencias personales inexistentes. "
    "Si participas en una entrevista, declara que eres un asistente de IA y confirma "
    "que el entrevistador acepta ese formato. Si no lo acepta, detén la participación. "
    "Responde con precisión, brevedad y naturalidad; no inventes hechos."
)


def system_prompt() -> str:
    path = os.getenv("LIVEKIT_SYSTEM_PROMPT_FILE")
    return Path(path).read_text(encoding="utf-8") if path else DEFAULT_PROMPT


class Presenter(Agent):
    def __init__(self):
        super().__init__(instructions=system_prompt())


server = AgentServer()


@server.rtc_session(agent_name=os.getenv("LIVEKIT_AGENT_NAME", "ai-avatar-loom"))
async def presenter_session(ctx: agents.JobContext):
    voice_id = os.getenv("ELEVENLABS_VOICE_ID")
    if not voice_id:
        raise RuntimeError("Missing ELEVENLABS_VOICE_ID")

    session = AgentSession(
        stt=inference.STT(model="deepgram/nova-3", language="es"),
        llm=xai.responses.LLM(model=os.getenv("XAI_MODEL", "grok-4.3")),
        tts=elevenlabs.TTS(voice_id=voice_id, model=os.getenv("ELEVENLABS_MODEL", "eleven_multilingual_v2")),
    )

    avatar_id = os.getenv("LEMONSLICE_AGENT_ID")
    avatar_url = os.getenv("LEMONSLICE_IMAGE_URL")
    if not avatar_id and not avatar_url:
        raise RuntimeError("Set LEMONSLICE_AGENT_ID or LEMONSLICE_IMAGE_URL")
    if avatar_id and avatar_url:
        raise RuntimeError("Set only one LemonSlice avatar source")

    avatar_kwargs = {"agent_id": avatar_id} if avatar_id else {"agent_image_url": avatar_url}
    avatar = lemonslice.AvatarSession(
        **avatar_kwargs,
        agent_prompt="Actitud profesional y cordial; movimientos naturales, sin gesticular excesivamente.",
    )
    await avatar.start(session, room=ctx.room)
    await avatar.wait_for_join()
    await session.start(room=ctx.room, agent=Presenter())
    await session.generate_reply(instructions="Saluda e identifícate claramente como asistente de IA.")


if __name__ == "__main__":
    agents.cli.run_app(server)
