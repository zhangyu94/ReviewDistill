from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urlparse, urlunparse


@dataclass(frozen=True)
class GitMetadata:
    repository: str | None
    commit_hash: str | None
    remote_url: str | None


def sanitize_remote_url(url: str | None) -> str | None:
    if not url:
        return None
    return _strip_userinfo(url)


def read_git_metadata(root: Path) -> GitMetadata:
    remote = _git(root, ["remote", "get-url", "origin"])
    return GitMetadata(
        repository=_git(root, ["rev-parse", "--show-toplevel"]),
        commit_hash=_git(root, ["rev-parse", "HEAD"]),
        remote_url=sanitize_remote_url(remote),
    )


def context_permalink(
    remote_url: str | None,
    commit: str | None,
    file_path: str,
    line_number: int,
) -> str | None:
    if not remote_url or not commit:
        return None
    url = _https_repo_url(remote_url)
    if url is None:
        return None
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    host = (parsed.hostname or "").lower()
    file_part = quote(file_path, safe="/")
    if host == "github.com" or host.endswith(".github.com"):
        return f"{url}/blob/{commit}/{file_part}#L{line_number}"
    if host == "gitlab.com" or host.endswith(".gitlab.com"):
        return f"{url}/-/blob/{commit}/{file_part}#L{line_number}"
    return url


def _strip_userinfo(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https", "ssh"} or not parsed.hostname:
        return url
    if parsed.password is None and parsed.username in {None, "", "git"}:
        return url
    host = parsed.hostname
    if parsed.port:
        host = f"{host}:{parsed.port}"
    return urlunparse(parsed._replace(netloc=host))


def _https_repo_url(remote_url: str) -> str | None:
    url = remote_url.strip()
    if url.startswith("git@"):
        host_path = url[4:]
        if ":" not in host_path:
            return None
        host, path = host_path.split(":", 1)
        url = f"https://{host}/{path}"
    url = _strip_userinfo(url).removesuffix(".git")
    return url.rstrip("/") or None


def _git(root: Path, args: list[str]) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None
