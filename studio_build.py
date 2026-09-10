"""Build the Studio SPA into ``reviewdistill/web/static`` during packaging.

``pip install`` from a PyPI wheel does not run this; the wheel already contains
the files. A git clone / editable install / ``python -m build`` does, and needs
Node ≥ 22 and pnpm. Set ``SKIP_STUDIO_BUILD=1`` for a Python-only install.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from setuptools.command.build_py import build_py as _build_py
from setuptools.command.editable_wheel import editable_wheel as _editable_wheel
from setuptools.command.sdist import sdist as _sdist

ROOT = Path(__file__).resolve().parent
_KEEP_IN_STATIC = frozenset({"README.md", ".gitignore"})
_built_this_process = False


class StudioBuildError(RuntimeError):
    pass


def should_build_studio(root: Path | None = None) -> bool:
    base = ROOT if root is None else root
    if os.environ.get("SKIP_STUDIO_BUILD") == "1":
        return False
    return (base / "studio" / "package.json").is_file()


def copy_dist_to_packaged(dist: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for child in dest.iterdir():
        if child.name in _KEEP_IN_STATIC:
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    for child in dist.iterdir():
        target = dest / child.name
        if child.is_dir():
            shutil.copytree(child, target)
        else:
            shutil.copy2(child, target)


def build_studio_assets(root: Path | None = None) -> None:
    global _built_this_process
    base = ROOT if root is None else root
    if not should_build_studio(base):
        return
    if _built_this_process and root is None:
        return
    pnpm = shutil.which("pnpm")
    if pnpm is None:
        raise StudioBuildError(
            "Studio UI build needs Node ≥ 22 and pnpm on PATH. "
            "Install them, or set SKIP_STUDIO_BUILD=1 for a Python-only install."
        )
    studio = base / "studio"
    subprocess.run(
        [pnpm, "--dir", str(studio), "install", "--frozen-lockfile"],
        cwd=base,
        check=True,
    )
    subprocess.run([pnpm, "--dir", str(studio), "build"], cwd=base, check=True)
    dist = studio / "dist"
    if not (dist / "index.html").is_file():
        raise StudioBuildError(f"Studio build did not produce {dist / 'index.html'}")
    copy_dist_to_packaged(dist, base / "reviewdistill" / "web" / "static")
    if root is None:
        _built_this_process = True
        print(f"Studio assets → {base / 'reviewdistill' / 'web' / 'static'}", flush=True)


class build_py(_build_py):
    def run(self) -> None:
        build_studio_assets()
        super().run()


class sdist(_sdist):
    def run(self) -> None:
        build_studio_assets()
        super().run()


class editable_wheel(_editable_wheel):
    def run(self) -> None:
        build_studio_assets()
        super().run()


def main() -> None:
    try:
        build_studio_assets()
    except StudioBuildError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
