import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

from reviewdistill.paths import (
    HomePathError,
    comments_path,
    data_location,
    find_project_root,
    home_dir,
    move_home,
    use_home,
)


def test_locator_path_is_isolated_from_real_home(tmp_path):
    from reviewdistill.paths import locator_path

    assert locator_path().resolve().is_relative_to(tmp_path.resolve())


def test_home_dir_defaults_when_locator_missing():
    from reviewdistill import paths as paths_mod

    assert not paths_mod.locator_path().is_file()
    assert paths_mod.home_dir() == paths_mod.Path.home() / ".reviewdistill"


def test_blank_locator_falls_through_to_default(tmp_path, monkeypatch):
    locator = _locator_only(tmp_path, monkeypatch)
    locator.parent.mkdir(parents=True)
    locator.write_text("  \n", encoding="utf-8")
    from reviewdistill import paths as paths_mod

    assert home_dir() == paths_mod.Path.home() / ".reviewdistill"


def test_use_home_writes_isolated_locator(tmp_path):
    from reviewdistill.paths import locator_path

    dest = tmp_path / "Documents" / "reviewdistill"
    use_home(dest)
    assert locator_path().resolve().is_relative_to(tmp_path.resolve())
    assert locator_path().read_text(encoding="utf-8").strip() == str(dest.resolve())


def test_home_dir_uses_locator(tmp_path, monkeypatch):
    _locator_only(tmp_path, monkeypatch)
    dest = use_home(tmp_path / "rd")
    assert home_dir() == dest
    assert comments_path() == dest / "comments.jsonl"


def test_data_location_uses_resolved_home(tmp_path, monkeypatch):
    _locator_only(tmp_path, monkeypatch)
    dest = use_home(tmp_path / "rd")
    loc = data_location()
    assert "home_env" not in loc
    assert loc["home"] == str(dest)
    assert loc["comments"] == str(dest / "comments.jsonl")
    assert loc["file_url"] == dest.resolve().as_uri()


def test_find_project_root_walks_up(tmp_path):
    repo = tmp_path / "paper"
    nested = repo / "src" / "tex"
    nested.mkdir(parents=True)
    (repo / ".reviewdistill").mkdir()
    (repo / ".reviewdistill" / "config.yaml").write_text("project:\n  name: demo\n")
    assert find_project_root(nested) == repo


def test_find_project_root_missing_returns_none(tmp_path):
    assert find_project_root(tmp_path) is None


def _locator_only(tmp_path, monkeypatch):
    locator = tmp_path / "config" / "reviewdistill" / "home"
    monkeypatch.setattr("reviewdistill.paths.locator_path", lambda: locator)
    return locator


def test_use_home_persists_folder(tmp_path, monkeypatch):
    _locator_only(tmp_path, monkeypatch)
    dest = tmp_path / "Documents" / "reviewdistill"
    used = use_home(dest)
    assert used == dest.resolve()
    assert dest.is_dir()
    assert home_dir() == dest.resolve()
    assert comments_path() == dest.resolve() / "comments.jsonl"


def test_env_does_not_override_locator(tmp_path, monkeypatch):
    _locator_only(tmp_path, monkeypatch)
    used = use_home(tmp_path / "from-cli")
    monkeypatch.setenv("REVIEWDISTILL_HOME", str(tmp_path / "from-env"))
    assert home_dir() == used
    assert home_dir() != tmp_path / "from-env"


def test_move_home_copies_folder_then_uses_it(tmp_path, monkeypatch):
    _locator_only(tmp_path, monkeypatch)
    src = use_home(tmp_path / "old-home")
    (src / "comments.jsonl").write_text("{}\n")
    (src / "config.yaml").write_text("llm: {}\n")
    dest = tmp_path / "backup" / "reviewdistill"
    moved = move_home(dest)
    assert moved == dest.resolve()
    assert (dest / "comments.jsonl").read_text() == "{}\n"
    assert (dest / "config.yaml").read_text() == "llm: {}\n"
    assert (src / "comments.jsonl").read_text() == "{}\n"
    assert home_dir() == dest.resolve()


def test_move_home_refuses_nonempty_destination(tmp_path, monkeypatch):
    _locator_only(tmp_path, monkeypatch)
    src = use_home(tmp_path / "old-home")
    (src / "comments.jsonl").write_text("{}\n")
    dest = tmp_path / "taken"
    dest.mkdir()
    (dest / "other.txt").write_text("no")
    with pytest.raises(HomePathError, match="already has files"):
        move_home(dest)


def test_move_home_refuses_destination_inside_home(tmp_path, monkeypatch):
    _locator_only(tmp_path, monkeypatch)
    src = use_home(tmp_path / "old-home")
    with pytest.raises(HomePathError, match="outside the current home"):
        move_home(src / "backup")


def test_move_home_refuses_empty_destination_already_inside_home(tmp_path, monkeypatch):
    _locator_only(tmp_path, monkeypatch)
    src = use_home(tmp_path / "old-home")
    dest = src / "backup"
    dest.mkdir()
    with pytest.raises(HomePathError, match="outside the current home"):
        move_home(dest)


def test_move_home_refuses_when_store_is_busy(tmp_path, monkeypatch):
    _locator_only(tmp_path, monkeypatch)
    src = use_home(tmp_path / "old-home")
    (src / "comments.jsonl").write_text("{}\n")
    lock = src / ".lock"
    proc = subprocess.Popen(
        [
            sys.executable,
            "-c",
            (
                "import fcntl, time\n"
                f"fp = open({str(lock)!r}, 'a+')\n"
                "fcntl.flock(fp, fcntl.LOCK_EX)\n"
                "time.sleep(30)\n"
            ),
        ]
    )
    try:
        from reviewdistill.paths import home_is_busy

        for _ in range(50):
            if home_is_busy(src):
                break
            time.sleep(0.05)
        with pytest.raises(HomePathError, match="Stop reviewdistill ui"):
            move_home(tmp_path / "new-home")
    finally:
        proc.kill()
        proc.wait()


def test_move_home_skips_lock_tmp_and_staging(tmp_path, monkeypatch):
    _locator_only(tmp_path, monkeypatch)
    src = use_home(tmp_path / "old-home")
    (src / "comments.jsonl").write_text("{}\n")
    (src / ".lock").write_text("held")
    (src / "comments.jsonl.tmp").write_text("partial\n")
    staging = src / ".commit"
    staging.mkdir()
    (staging / "COMMIT").write_text("ok\n")
    dest = tmp_path / "backup" / "reviewdistill"
    move_home(dest)
    assert (dest / "comments.jsonl").read_text() == "{}\n"
    assert not (dest / ".lock").exists()
    assert not (dest / "comments.jsonl.tmp").exists()
    assert not (dest / ".commit").exists()


def test_move_home_applies_pending_commit_before_copy(tmp_path, monkeypatch):
    _locator_only(tmp_path, monkeypatch)
    src = use_home(tmp_path / "old-home")
    from reviewdistill.db.models import Project, ProofreadingComment
    from reviewdistill.db.session import get_session

    with get_session() as session:
        session.add(Project(id="p1", name="old", root_path="/tmp/paper"))
        session.add(
            ProofreadingComment(
                id="c1",
                project_id="p1",
                source_type="latex_command",
                source_command="myremark",
                file_path="main.tex",
                line_number=1,
                raw_text="old",
                fingerprint="fp",
                status="active",
            )
        )
        session.commit()
    staging = src / ".commit"
    staging.mkdir()
    (staging / "projects.jsonl").write_text(
        (src / "projects.jsonl").read_text(encoding="utf-8").replace('"old"', '"new"'),
        encoding="utf-8",
    )
    (staging / "comments.jsonl").write_text(
        (src / "comments.jsonl").read_text(encoding="utf-8").replace('"old"', '"new"'),
        encoding="utf-8",
    )
    (staging / "COMMIT").write_text("ok\n", encoding="utf-8")
    dest = tmp_path / "backup" / "reviewdistill"
    move_home(dest)
    assert not (dest / ".commit").exists()
    with get_session() as session:
        assert session.get(Project, "p1").name == "new"
        assert session.get(ProofreadingComment, "c1").raw_text == "new"


def test_move_home_rechecks_destination_after_lock(tmp_path, monkeypatch):
    import fcntl

    _locator_only(tmp_path, monkeypatch)
    src = use_home(tmp_path / "old-home")
    (src / "comments.jsonl").write_text("{}\n")
    dest = tmp_path / "new-home"
    real_flock = fcntl.flock

    def flock(fp, flags):
        if flags == fcntl.LOCK_EX | fcntl.LOCK_NB:
            dest.mkdir(parents=True, exist_ok=True)
            (dest / "sneak.txt").write_text("taken\n", encoding="utf-8")
        return real_flock(fp, flags)

    monkeypatch.setattr("reviewdistill.paths.fcntl.flock", flock)
    with pytest.raises(HomePathError, match="already has files"):
        move_home(dest)


def test_move_home_holds_lock_during_copy(tmp_path, monkeypatch):
    _locator_only(tmp_path, monkeypatch)
    src = use_home(tmp_path / "old-home")
    (src / "comments.jsonl").write_text("{}\n")
    original = shutil.copytree
    busy_during_copy = {"value": None}

    def wrapped(src_dir, dest_dir, **kwargs):
        root = Path(__file__).resolve().parents[1]
        env = {**os.environ, "PYTHONPATH": str(root) + os.pathsep + os.environ.get("PYTHONPATH", "")}
        check = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "from pathlib import Path\n"
                    "from reviewdistill.paths import home_is_busy\n"
                    f"raise SystemExit(0 if home_is_busy(Path({str(Path(src_dir).resolve())!r})) else 1)\n"
                ),
            ],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        busy_during_copy["value"] = check.returncode
        return original(src_dir, dest_dir, **kwargs)

    monkeypatch.setattr("reviewdistill.paths.shutil.copytree", wrapped)
    move_home(tmp_path / "new-home")
    assert busy_during_copy["value"] == 0, "store must stay locked while copying"


def test_move_home_wraps_copy_errors(tmp_path, monkeypatch):
    _locator_only(tmp_path, monkeypatch)
    src = use_home(tmp_path / "old-home")
    (src / "comments.jsonl").write_text("{}\n")

    def boom(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("reviewdistill.paths.shutil.copytree", boom)
    with pytest.raises(HomePathError, match="Could not copy"):
        move_home(tmp_path / "new-home")


def test_use_home_rejects_blank(tmp_path, monkeypatch):
    _locator_only(tmp_path, monkeypatch)
    with pytest.raises(HomePathError, match="Choose a folder"):
        use_home("  ")


def test_open_data_folder_invokes_file_manager(tmp_path, monkeypatch):
    from reviewdistill.paths import open_data_folder

    _locator_only(tmp_path, monkeypatch)
    dest = use_home(tmp_path / "rd")
    opened: list[Path] = []
    monkeypatch.setattr(
        "reviewdistill.paths._open_in_file_manager",
        lambda path: opened.append(path),
    )
    assert open_data_folder() == dest.resolve()
    assert opened == [dest.resolve()]


def test_choose_data_folder_returns_picked_path(tmp_path, monkeypatch):
    from reviewdistill.paths import choose_data_folder

    _locator_only(tmp_path, monkeypatch)
    use_home(tmp_path / "rd")
    picked = tmp_path / "picked"
    picked.mkdir()
    monkeypatch.setattr(
        "reviewdistill.paths._choose_in_file_manager",
        lambda _initial: picked,
    )
    assert choose_data_folder() == picked.resolve()


def test_choose_data_folder_returns_none_when_cancelled(tmp_path, monkeypatch):
    from reviewdistill.paths import choose_data_folder

    _locator_only(tmp_path, monkeypatch)
    use_home(tmp_path / "rd")
    monkeypatch.setattr(
        "reviewdistill.paths._choose_in_file_manager",
        lambda _initial: None,
    )
    assert choose_data_folder() is None
