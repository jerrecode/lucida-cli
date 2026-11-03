"""Terminal frontend. No provider or filesystem business logic lives here."""
from __future__ import annotations
import argparse
import asyncio
import json
import os
import platform
import sys
from pathlib import Path
from urllib.parse import urlsplit
from lucida_api import API_VERSION, Config, Job, LucidaClient, LucidaError


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="lucida", description="Provider-driven media toolkit (pre-release)")
    root.add_argument("--json", action="store_true", help="Machine-readable output")
    sub = root.add_subparsers(dest="command", required=True)
    sub.add_parser("version")
    sub.add_parser("doctor")
    sub.add_parser("providers")
    search = sub.add_parser("search", help="MusicBrainz metadata search (no audio acquisition)")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=10)
    jobs = sub.add_parser("jobs")
    jobs.add_argument("--limit", type=int, default=100)
    recover = sub.add_parser("recover", help="Mark orphaned jobs interrupted; all other instances must be closed")
    recover.add_argument("--confirm-inactive", action="store_true", required=False)
    retry = sub.add_parser("retry", help="Retry a failed/interrupted job from scratch")
    retry.add_argument("job_id")
    retry.add_argument("--allow-host", action="append", default=[], metavar="HOST")
    retry.add_argument("--local-test", action="store_true")
    batch = sub.add_parser("batch", help="Read up to 1000 authorized URLs, one per line")
    batch.add_argument("source_file", type=Path)
    batch.add_argument("--allow-host", action="append", default=[], metavar="HOST")
    batch.add_argument("--local-test", action="store_true")
    batch.add_argument("--concurrency", type=int, default=2)
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
                     allow_private=getattr(args, "local_test", False),
                     max_concurrent=getattr(args, "concurrency", 2))
        api = LucidaClient(cfg)
        if args.command == "version":
            render(api.version(), args.json)
        elif args.command == "doctor":
            render({"python": sys.version.split()[0], "os": platform.platform(),
                    "api": API_VERSION, "state_dir": str(cfg.state_dir),
                    "output_dir": str(cfg.output_dir), "provider_count": len(api.providers())}, args.json)
        elif args.command == "providers":
            render(api.providers(), args.json)
        elif args.command == "recover":
            count = api.recover_interrupted(confirm_no_active_workers=args.confirm_inactive)
            render({"marked_interrupted": count}, args.json)
        elif args.command == "search":
            render([x.to_dict() for x in asyncio.run(api.search(args.query, args.limit))], args.json)
        elif args.command == "jobs":
            render([j.to_dict() for j in api.jobs(args.limit)], args.json)
        elif args.command == "retry":
            result = asyncio.run(api.retry(args.job_id))
            render(result.to_dict(), args.json)
        elif args.command == "batch":
            if not args.source_file.is_file():
                raise ValueError("Batch file does not exist")
            if args.source_file.stat().st_size > 1024 * 1024:
                raise ValueError("Batch file exceeds 1 MiB")
            sources = [line.strip() for line in args.source_file.read_text(encoding="utf-8-sig").splitlines()
                       if line.strip() and not line.lstrip().startswith("#")]
            if not 1 <= len(sources) <= 1000:
                raise ValueError("Batch requires between 1 and 1000 entries")
            async def process_batch():
                queue = asyncio.Queue(maxsize=cfg.max_concurrent * 2)
                results = [None] * len(sources)
                async def produce():
                    for index, source in enumerate(sources):
                        await queue.put((index, source))
                    for _ in range(cfg.max_concurrent):
                        await queue.put(None)
                async def consume():
                    while True:
                        work = await queue.get()
                        if work is None:
                            return
                        index, source = work
                        parsed = urlsplit(source)
                        filename = (f"sample-{index + 1:04d}.wav" if source == "sample://tone"
                                    else parsed.path.rsplit("/", 1)[-1] or f"download-{index + 1:04d}.audio")
                        try:
                            job = await api.acquire(source, filename)
                            results[index] = {"source": source, "job": job.to_dict()}
                        except (LucidaError, OSError, ValueError) as exc:
                            results[index] = {"source": source, "error": str(exc),
                                              "code": getattr(exc, "code", "runtime_error")}
                await asyncio.gather(produce(), *(consume() for _ in range(cfg.max_concurrent)))
                return results
            batch_result = asyncio.run(process_batch())
            render(batch_result, args.json)
            return 2 if any("error" in item for item in batch_result) else 0
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
    except (LucidaError, OSError, ValueError, RuntimeError, UnicodeError) as exc:
        print(json.dumps({"error": str(exc), "code": getattr(exc, "code", "runtime_error")})
              if args.json else f"Error: {exc}", file=sys.stderr)
        return 2


def main():
    raise SystemExit(run())

if __name__ == "__main__":
    main()
