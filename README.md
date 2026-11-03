# Lucida CLI (0.1.0 development preview)

Terminal frontend of [Lucida API](https://github.com/jerrecode/lucida-api). Linux and Windows targets; command unit tests and wheel packaging pass Ubuntu and Windows CI, while real-user shell and installer validation remain pending. Does **not** advertise full lucida.to support.

Install from repository: on Linux `./install.sh`; on Windows PowerShell `./install.ps1`. These create an isolated `.venv` and fetch compatible API source. For local sibling checkouts set `LUCIDA_API_SOURCE=../lucida-api` first. Manual alternative: create and activate a venv, install API from source then `python -m pip install -e .`.

Available operations:

```
lucida version
lucida doctor
lucida providers
lucida search "artist title"
lucida demo
lucida --json jobs
lucida --json batch tracks.txt --concurrency 2 --allow-host your-trusted-host.example
lucida retry JOB_ID --allow-host your-trusted-host.example
lucida resume JOB_ID --allow-host your-trusted-host.example
lucida download https://your-trusted-host.example/audio.wav --allow-host your-trusted-host.example --sha256 EXPECTED_64_HEX
lucida recover --confirm-inactive  # only after all instances have stopped
lucida download https://your-trusted-host.example/audio.wav --allow-host your-trusted-host.example
```

Search uses MusicBrainz metadata only and returns no audio or download authorization. Only URLs that you are authorized to access may be used. No website-specific bypasses. For a controlled **local** HTTP test server add `--local-test`. Standard output carries command results; failures are reported on standard error. `--json` is a global flag placed before the command. `batch` accepts up to 1000 nonblank lines (one authorized URL or `sample://tone` per line), runs a bounded number of parallel transfers, and returns a nonzero exit status if any entry failed. Retries are explicitly from scratch and require the same output directory and source trust arguments. Limited HTTP partial-byte resume is available through `resume` when the original response had a strong ETag and the remote server returns a consistent `206 Partial Content` response. Optional `--sha256` verifies the complete file before publication. There is no arbitrary pause or cross-process cancellation command yet. Existing files are never overwritten.

Tests: `PYTHONPATH=../lucida-api/src:src python -m pytest -q tests`.

Roadmap: [API implementation plan](https://github.com/jerrecode/lucida-api/blob/main/IMPLEMENTATION_PLAN.md).
