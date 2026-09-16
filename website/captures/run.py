#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

CAPTURES = Path(__file__).resolve().parent
SITE = CAPTURES.parent
REPO = SITE.parent
STATIC_VIDEO = SITE / "static" / "video"
FIXTURE = CAPTURES / "fixtures" / "paper"  # Playwright stills
STARTER = CAPTURES / "fixtures" / "starter"  # first-paper.gif; match Guide tex
PORT = 18765
BASE = f"http://127.0.0.1:{PORT}"

sys.path.insert(0, str(CAPTURES))
from isolate import capture_environ  # noqa: E402
from seed import seed_demo_http  # noqa: E402
from ui_shots import capture as capture_ui  # noqa: E402


def _venv_bin() -> Path:
    return Path(sys.executable).parent


def _wait_api(env: dict[str, str]) -> None:
    deadline = time.time() + 30
    last = None
    while time.time() < deadline:
        try:
            response = httpx.get(f"{BASE}/api/inbox", timeout=1)
            if response.status_code == 200:
                return
            last = response.status_code
        except httpx.HTTPError as exc:
            last = exc
        time.sleep(0.2)
    raise RuntimeError(f"UI did not become ready at {BASE}: {last}")


def _write_tape(src: Path, output: Path) -> Path:
    # Absolute Output: first-paper VHS cwd is the paper copy, not tapes/.
    text = src.read_text(encoding="utf-8").replace(
        "Output PLACEHOLDER",
        f'Output "{output}"',
    )
    dest = src.parent / f".{src.name}"
    dest.write_text(text, encoding="utf-8")
    return dest


def _run_vhs(tape: Path, cwd: Path, env: dict[str, str]) -> None:
    local = cwd / tape.name.lstrip(".")
    if local.resolve() != tape.resolve():
        shutil.copy(tape, local)
    subprocess.run(["vhs", str(local)], cwd=cwd, env=env, check=True)


def main() -> int:
    try:
        import playwright  # noqa: F401
    except ImportError:
        print("Install Playwright: pip install playwright && playwright install chromium", file=sys.stderr)
        return 1

    subprocess.run(
        [sys.executable, str(REPO / "client_build.py")],
        cwd=REPO,
        check=True,
    )

    env_base = None
    with tempfile.TemporaryDirectory(prefix="rd-docs-capture-") as tmp:
        work = Path(tmp)
        env = capture_environ(work)
        env["PATH"] = str(_venv_bin()) + ":" + env.get("PATH", "")
        env_base = env["HOME"]

        paper = work / "paper"
        shutil.copytree(FIXTURE, paper)
        subprocess.run(
            ["reviewdistill", "init", "--name", "demo", "--command", "myremark"],
            cwd=paper,
            env=env,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["reviewdistill", "extract"],
            cwd=paper,
            env=env,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        proc = subprocess.Popen(
            ["reviewdistill", "ui", "--host", "127.0.0.1", "--port", str(PORT)],
            cwd=paper,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            _wait_api(env)
            seed_demo_http(BASE)
            capture_ui(BASE)
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()

        vhs = shutil.which("vhs", path=env["PATH"])
        if not vhs:
            print("Skipping VHS (vhs not on PATH)")
            return 0

        STATIC_VIDEO.mkdir(parents=True, exist_ok=True)
        install_out = STATIC_VIDEO / "install.gif"
        first_out = STATIC_VIDEO / "first-paper.gif"
        install_tape = _write_tape(CAPTURES / "tapes" / "install.tape", install_out)
        first_tape = _write_tape(CAPTURES / "tapes" / "first-paper.tape", first_out)
        try:
            _run_vhs(install_tape, work, env)
            vhs_paper = work / "vhs-paper"
            shutil.copytree(STARTER, vhs_paper)
            _run_vhs(first_tape, vhs_paper, env)
        finally:
            install_tape.unlink(missing_ok=True)
            first_tape.unlink(missing_ok=True)

    print(f"Capture HOME was {env_base}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
