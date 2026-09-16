import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "website" / "captures"))

from isolate import capture_environ  # noqa: E402


def test_capture_environ_home_is_under_work(tmp_path):
    env = capture_environ(tmp_path)
    home = Path(env["HOME"])
    assert home == tmp_path / "home"
    assert home.is_dir()
    assert home.resolve().is_relative_to(tmp_path.resolve())


def test_capture_environ_does_not_touch_real_locator(tmp_path, monkeypatch):
    env = capture_environ(tmp_path)
    monkeypatch.setenv("HOME", env["HOME"])
    monkeypatch.setattr("reviewdistill.paths.Path.home", lambda: Path(env["HOME"]))
    from reviewdistill.paths import home_dir, locator_path

    assert locator_path() == Path(env["HOME"]) / ".config" / "reviewdistill" / "home"
    assert home_dir() == Path(env["HOME"]) / ".reviewdistill"


def test_capture_environ_hides_blake2_hashlib_noise(tmp_path):
    env = capture_environ(tmp_path)
    result = subprocess.run(
        [sys.executable, "-c", "import reviewdistill.cli.app"],
        env=env,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "blake2" not in result.stderr
    assert "blake2" not in result.stdout


def test_capture_readme_documents_isolation_and_fixtures():
    text = (ROOT / "website" / "captures" / "README.md").read_text(encoding="utf-8")
    assert "HOME" in text
    assert "REVIEWDISTILL_HOME" in text
    assert "fixtures/starter" in text
    assert "fixtures/paper" in text


def test_capture_runner_rebuilds_client():
    text = (ROOT / "website" / "captures" / "run.py").read_text(encoding="utf-8")
    assert "client_build.py" in text
    shots = (ROOT / "website" / "captures" / "ui_shots.py").read_text(encoding="utf-8")
    assert "Show comments in a project file tree" in shots


def test_first_paper_vhs_uses_starter_tex():
    captures = ROOT / "website" / "captures"
    tape = (captures / "tapes" / "first-paper.tape").read_text(encoding="utf-8")
    starter = (captures / "fixtures" / "starter" / "main.tex").read_text(encoding="utf-8")
    guide = (ROOT / "website" / "docs" / "first-paper.md").read_text(encoding="utf-8")
    runner = (captures / "run.py").read_text(encoding="utf-8")
    assert "--name paper-01" in tape
    assert "--name paper-01" in guide
    assert "--name demo" not in tape
    assert starter.count(r"\myremark{") == 1
    assert starter.strip() in guide
    assert "copytree(STARTER" in runner
    assert "_run_vhs(first_tape" in runner
