"""CLI entry point; all paid API calls require explicit user commands."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .clients import ElevenLabsClient, XAIClient
from .config import Settings
from .pipeline import generate_video, refresh_job


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="avatar-loom", description="AI talking-head Loom producer")
    sub = p.add_subparsers(dest="command", required=True)

    draft = sub.add_parser("draft", help="Write a first-person script with Grok")
    draft.add_argument("--brief", type=Path, required=True)
    draft.add_argument("--output", type=Path, required=True)
    draft.add_argument("--seconds", type=int, default=90)
    draft.add_argument("--style", default="natural")

    clone = sub.add_parser("clone-voice", help="Clone your own voice from recordings")
    clone.add_argument("--name", required=True)
    clone.add_argument("--audio", type=Path, nargs="+", required=True)
    clone.add_argument("--consent", action="store_true", help="Confirm this is your voice or authorized")

    generate = sub.add_parser("generate", help="Create a narration and submit avatar MP4")
    generate.add_argument("--script", type=Path, required=True)
    generate.add_argument("--title", required=True)
    generate.add_argument("--output-dir", type=Path, default=Path("output"))
    generate.add_argument("--avatar-id")
    generate.add_argument("--voice-id")
    generate.add_argument("--resolution", choices=["720p", "1080p"], default="1080p")
    generate.add_argument("--aspect-ratio", choices=["16:9", "9:16"], default="16:9")

    batch = sub.add_parser("batch", help="Submit videos from a JSON manifest")
    batch.add_argument("--manifest", type=Path, required=True)
    batch.add_argument("--output-dir", type=Path, default=Path("output"))

    status = sub.add_parser("status", help="Check existing job; download MP4 if completed")
    status.add_argument("--job", type=Path, required=True)

    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    settings = Settings.load()
    try:
        if args.command == "draft":
            settings.require("xai_key")
            text = XAIClient(settings.xai_key, settings.xai_model).draft(
                args.brief.read_text(encoding="utf-8"), args.seconds, args.style)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(text + "\n", encoding="utf-8")
            print(f"Script saved: {args.output}")
        elif args.command == "clone-voice":
            settings.require("eleven_key")
            if not args.consent:
                raise ValueError("Pass --consent to confirm voice ownership and authorization")
            for sample in args.audio:
                if not sample.is_file():
                    raise FileNotFoundError(sample)
            voice_id = ElevenLabsClient(settings.eleven_key).clone_voice(args.name, args.audio)
            print(f"Voice ID: {voice_id}\nAdd ELEVENLABS_VOICE_ID={voice_id} to your local .env")
        elif args.command == "generate":
            job = generate_video(
                script=args.script.read_text(encoding="utf-8"), title=args.title,
                output_dir=args.output_dir, settings=settings, avatar_id=args.avatar_id,
                voice_id=args.voice_id, resolution=args.resolution,
                aspect_ratio=args.aspect_ratio)
            print(json.dumps(job, ensure_ascii=False, indent=2))
            print("Submitted. Use: avatar-loom status --job <output_dir>/<title-slug>/job.json")
        elif args.command == "batch":
            data = json.loads(args.manifest.read_text(encoding="utf-8"))
            entries = data["videos"] if isinstance(data, dict) else data
            if not isinstance(entries, list):
                raise ValueError("Manifest must contain a 'videos' array")
            for index, item in enumerate(entries, 1):
                # Relative script paths are resolved from the manifest's directory.
                script_path = (args.manifest.parent / item["script"]).resolve()
                print(f"[{index}/{len(entries)}] Submitting {item['title']}", flush=True)
                generate_video(
                    script=script_path.read_text(encoding="utf-8"),
                    title=item["title"], output_dir=args.output_dir, settings=settings,
                    avatar_id=item.get("avatar_id"), voice_id=item.get("voice_id"),
                    aspect_ratio=item.get("aspect_ratio", "16:9"),
                    resolution=item.get("resolution", "1080p"))
            print("All jobs submitted. Use 'status' for each job to fetch completed MP4s.")
        elif args.command == "status":
            print(json.dumps(refresh_job(args.job, settings), ensure_ascii=False, indent=2))
        return 0
    except (ValueError, FileNotFoundError, FileExistsError, KeyError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
