"""Terminal frontend. No provider or filesystem business logic lives here."""
from __future__ import annotations
import argparse
import asyncio
import json
import os
import platform
import sys
from lucida_api import API_VERSION, Config, Job, LucidaClient, LucidaError


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="lucida", description="Provider-driven media toolkit (pre-release)")
    root.add_argument("--json", action="store_true", help="Machine-readable output")
    sub = root.add_subparsers(dest="command", required=True)
    sub.add_parser("version")
    sub.add_parser("doctor")
    sub.add_parser("providers")
    jobs = sub.add_parser("jobs")
    jobs.add_argument("--limit", type=int, default=100)
    sub.add_parser("demo", help="Generate an offline WAV test file")
    dl = sub.add_parser("download", help="Only explicitly authorized direct audio URLs")
    dl.add_argument("url")
    dl.add_argument("--filename")
    dl.add_argument("--allow-host", action="append", default=[], metavar="HOST",
                    help="Explicitly trust this host; use only for authorized sources")
    dl.add_argument("--local-test", action="store_true", help="Allow HTTP/private IPs for isolated testing")
    sub.add_parser("serve", help="Run optional loopback REST server; requires API server extra")
    return root


def render(value, structured: bool) -> None:
    if structured:
        print(json.dumps(value, ensure_ascii=False, indent=2))
    elif isinstance(value, list):
        for item in value:
            print(" | ".join(f"{k}: {v}" for k, v in item.items()))
    elif isinstance(value, dict):
        for key, val in value.items():
            print(f"{key}: {val}")
    else:
        print(value)


def run(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "serve":
            from lucida_api.server import main as serve
            serve()
            return 0
        cfg = Config(allowed_hosts=tuple(getattr(args, "allow_host", ())),
                     allow_private=getattr(args, "local_test", False))
        api = LucidaClient(cfg)
        if args.command == "version":
            render(api.version(), args.json)
        elif args.command == "doctor":
            render({"python": sys.version.split()[0], "os": platform.platform(),
                    "api": API_VERSION, "state_dir": str(cfg.state_dir),
                    "output_dir": str(cfg.output_dir), "provider_count": len(api.providers())}, args.json)
        elif args.command == "providers":
            render(api.providers(), args.json)
        elif args.command == "jobs":
            render([j.to_dict() for j in api.jobs(args.limit)], args.json)
        elif args.command in ("demo", "download"):
            def progress(job: Job):
                if not args.json and sys.stderr.isatty():
                    print(f"\r{job.state} {job.transferred} bytes", file=sys.stderr, end="", flush=True)
            source = "sample://tone" if args.command == "demo" else args.url
            filename = None if args.command == "demo" else args.filename
            result = asyncio.run(api.acquire(source, filename, progress))
            if not args.json and sys.stderr.isatty():
                print(file=sys.stderr)
            render(result.to_dict(), args.json)
        return 0
    except (LucidaError, OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({"error": str(exc), "code": getattr(exc, "code", "runtime_error")})
              if args.json else f"Error: {exc}", file=sys.stderr)
        return 2


def main():
    raise SystemExit(run())

if __name__ == "__main__":
    main()
