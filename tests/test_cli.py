from pathlib import Path
from lucida_cli.main import run


def test_demo_and_jobs(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LUCIDA_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("LUCIDA_OUTPUT_DIR", str(tmp_path / "music"))
    assert run(["--json", "demo"]) == 0
    output = capsys.readouterr().out
    assert '"state": "completed"' in output
    assert (tmp_path / "music" / "sample-tone.wav").is_file()
    assert run(["--json", "jobs"]) == 0
    assert '"source": "sample://tone"' in capsys.readouterr().out
    assert run(["--json", "demo"]) == 2
    assert 'file_conflict' in capsys.readouterr().err


def test_version_and_providers(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LUCIDA_HOME", str(tmp_path / "state"))
    assert run(["version"]) == 0
    assert "0.1.0" in capsys.readouterr().out
    assert run(["--json", "providers"]) == 0
    assert '"name": "direct-http"' in capsys.readouterr().out


def test_batch_bounded_and_json(tmp_path, monkeypatch, capsys):
    import json
    monkeypatch.setenv("LUCIDA_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("LUCIDA_OUTPUT_DIR", str(tmp_path / "music"))
    sources = tmp_path / "batch.txt"
    sources.write_text("# sample\nsample://tone\nsample://tone\nsample://tone\n")
    assert run(["--json", "batch", str(sources), "--concurrency", "2"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert len(result) == 3
    assert all(r["job"]["state"] == "completed" for r in result)
    assert len(list((tmp_path / "music").glob("*.wav"))) == 3
    assert run(["--json", "batch", str(sources)]) == 2  # cannot overwrite
    failed = json.loads(capsys.readouterr().out)
    assert all(r["code"] == "file_conflict" for r in failed)


def test_retry_cli_failed_job(tmp_path, monkeypatch, capsys):
    from lucida_api import LucidaClient, Config, JobState
    from lucida_api.models import Job
    monkeypatch.setenv("LUCIDA_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("LUCIDA_OUTPUT_DIR", str(tmp_path / "music"))
    client = LucidaClient(Config())
    client.store.add(Job("previous", "sample://tone", str(tmp_path / "music" / "retry.wav"),
                         JobState.FAILED))
    assert run(["--json", "retry", "previous"]) == 0
    assert '"state": "completed"' in capsys.readouterr().out
    assert (tmp_path / "music" / "retry.wav").is_file()
