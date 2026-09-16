import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SPEC = DOCS / "spec"

REQUIRED = [
    "README.md",
    "overview.md",
    "workflow.md",
    "taxonomy.md",
    "extract.md",
    "ui.md",
    "cli-and-export.md",
    "storage.md",
    "data-schema.md",
    "comment-identity.md",
]

REMOVED = [
    DOCS / "spec.md",
    DOCS / "data-schema.md",
    DOCS / "comment-identity.md",
]


def test_old_spec_paths_are_gone():
    for path in REMOVED:
        assert not path.exists(), path


def test_spec_files_exist():
    for name in REQUIRED:
        assert (SPEC / name).is_file(), name


def test_spec_files_have_local_headings():
    for path in SPEC.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            assert not re.match(r"## \d+\. ", line), f"{path.name}: {line}"
        assert "⸻" not in text, path.name


def test_spec_readme_is_the_roadmap():
    text = (SPEC / "README.md").read_text(encoding="utf-8")
    for name in REQUIRED:
        if name == "README.md":
            continue
        assert name in text, name


def test_inbound_links_point_at_spec_dir():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    internals = (ROOT / "website" / "docs" / "internals.md").read_text(encoding="utf-8")
    extract = (ROOT / "website" / "docs" / "extract.md").read_text(encoding="utf-8")
    website = (ROOT / "website" / "README.md").read_text(encoding="utf-8")
    incremental = (ROOT / "reviewdistill" / "extraction" / "incremental.py").read_text(
        encoding="utf-8"
    )
    assert "docs/spec.md" not in readme
    assert "docs/spec/README.md" in readme
    assert "docs/spec/data-schema.md" in readme
    assert "docs/spec/comment-identity.md" in readme
    assert "/docs/spec.md" not in internals
    assert "/docs/spec/README.md" in internals
    assert "/docs/spec/data-schema.md" in internals
    assert "/docs/spec/comment-identity.md" in internals
    spec_extract = (SPEC / "extract.md").read_text(encoding="utf-8")
    spec_cli = (SPEC / "cli-and-export.md").read_text(encoding="utf-8")
    spec_taxonomy = (SPEC / "taxonomy.md").read_text(encoding="utf-8")
    assert "docs/spec.md" not in extract
    assert "docs/spec/extract.md" in extract
    assert "website/docs/extract.md" not in spec_extract
    assert "data-schema.md" in spec_extract
    assert "review-taxonomy.yaml" in spec_cli
    assert "extra notes from the reviewer" not in spec_taxonomy
    assert "`notes` is not a field" in spec_taxonomy
    assert "spec.md" not in website
    assert "docs/spec/" in website
    assert "docs/comment-identity.md" not in incremental
    assert "docs/spec/comment-identity.md" in incremental


def test_spec_extract_states_harvest_matching():
    text = (SPEC / "extract.md").read_text(encoding="utf-8")
    assert "spaces or tabs" in text
    assert r"\%" in text
    assert r"\notmyremark" in text
    assert r"% \command{" in text
    assert "empty lines dropped" in text
    assert "live configured argument" in text
    assert r"\caption" in text
    assert "commented-out body" in text
    assert "heading after `}`" in text
    assert r"\label" in text
    assert "0..length" in text
    schema = (SPEC / "data-schema.md").read_text(encoding="utf-8")
    assert "live configured argument" in schema
    assert "spaces or tabs" in schema
    assert "context_offset" in (SPEC / "taxonomy.md").read_text(encoding="utf-8")
    overview = (SPEC / "overview.md").read_text(encoding="utf-8")
    shipped = overview.split("Classification uses", 1)[0]
    assert "* severity or importance" not in shipped


def test_website_extract_and_cli_match_export_and_normalize():
    extract = (ROOT / "website" / "docs" / "extract.md").read_text(encoding="utf-8")
    cli = (ROOT / "website" / "docs" / "cli.md").read_text(encoding="utf-8")
    assert "empty lines dropped" in extract
    assert "spaces or tabs" in extract
    assert "review-taxonomy.yaml" in cli
