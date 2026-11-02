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
