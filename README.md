# Lucida CLI (0.1.0 development preview)

Terminal frontend of [Lucida API](https://github.com/jerrecode/lucida-api). Linux and Windows targets; Windows runtime has not yet been independently tested. Does **not** advertise full lucida.to support.

Install from repository: on Linux `./install.sh`; on Windows PowerShell `./install.ps1`. These create an isolated `.venv` and fetch compatible API source. For local sibling checkouts set `LUCIDA_API_SOURCE=../lucida-api` first. Manual alternative: create and activate a venv, install API from source then `python -m pip install -e .`.

Available operations:

```
lucida version
lucida doctor
lucida providers
lucida search "artist title"
lucida demo
lucida --json jobs
lucida recover --confirm-inactive  # only after all instances have stopped
lucida download https://your-trusted-host.example/audio.wav --allow-host your-trusted-host.example
```

Search uses MusicBrainz metadata only and returns no audio or download authorization. Only URLs that you are authorized to access may be used. No website-specific bypasses. For a controlled **local** HTTP test server add `--local-test`. Standard output carries command results; failures are reported on standard error. `--json` is a global flag placed before the command. Each failed job is journaled; no restart/resume command exists yet.

Tests: `PYTHONPATH=../lucida-api/src:src python -m pytest -q tests`.

Roadmap: [API implementation plan](https://github.com/jerrecode/lucida-api/blob/main/IMPLEMENTATION_PLAN.md).
