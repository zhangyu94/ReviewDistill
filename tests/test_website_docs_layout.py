from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "website" / "docs"


def _sidebars() -> str:
    return (ROOT / "website" / "sidebars.ts").read_text(encoding="utf-8")


def _config() -> str:
    return (ROOT / "website" / "docusaurus.config.ts").read_text(encoding="utf-8")


REQUIRED = [
    "intro.md",
    "install.md",
    "first-paper.md",
    "labeling.mdx",
    "export.md",
    "workbench.md",
    "cli.md",
    "extract.md",
    "llm.md",
    "history.md",
    "data.md",
    "internals.md",
]

REMOVED = ["workflow.md", "ui.md", "workbench.mdx"]

BANNED = [
    "Distill human proofreading",
    "Who it is for",
    "you still choose",
    "it does not replace your judgment",
]


def test_removed_pages_are_gone():
    for name in REMOVED:
        assert not (DOCS / name).exists(), name


def test_required_pages_exist():
    for name in REQUIRED:
        assert (DOCS / name).is_file(), name


def test_sidebar_has_guide_and_reference():
    sidebars = _sidebars()
    assert "label: 'Guide'" in sidebars
    assert "label: 'Reference'" in sidebars
    assert "'first-paper'" in sidebars
    assert "'workbench'" in sidebars
    assert "'workflow'" not in sidebars
    reference = sidebars.split("label: 'Reference'", 1)[1]
    assert reference.index("'cli'") < reference.index("'workbench'")


def test_tagline_and_footer():
    config = _config()
    assert (
        "Distill the comments you write in a LaTeX paper into a reusable agent skill to save your proofreading time."
        in config
    )
    assert "to: '/docs/intro'" in config
    assert "to: '/docs/workbench'" in config
    assert "/docs/workflow" not in config
    assert "/docs/ui'" not in config
    assert "MIT License" not in config
    assert "Built with Docusaurus" not in config


def test_intro_states_reuse_motivation():
    text = (DOCS / "intro.md").read_text(encoding="utf-8").lower()
    assert "reuse" in text
    assert "skill" in text


def test_install_requires_python_not_node():
    text = (DOCS / "install.md").read_text(encoding="utf-8")
    lead = text.split("```", 1)[0]
    assert "Python ≥ 3.11" in lead
    assert "workbench" not in lead.lower()
    assert "Node" not in lead
    assert "pnpm" not in lead
    assert 'pip install -e ".[dev]"' not in text
    assert "pip install -e ." in text
    assert "Internals" not in text
    internals = (DOCS / "internals.md").read_text(encoding="utf-8")
    assert "Node" in internals
    assert "pnpm" in internals


def test_first_paper_shows_complete_starter_tex():
    text = (DOCS / "first-paper.md").read_text(encoding="utf-8")
    assert r"\documentclass{article}" in text
    assert r"\begin{document}" in text
    assert r"\end{document}" in text
    assert r"\newcommand{\myremark}[1]{#1}" in text
    assert r"\myremark{Demonstrate is too strong here.}" in text
    assert "main.tex" in text


def test_first_paper_describes_extract_result():
    text = (DOCS / "first-paper.md").read_text(encoding="utf-8")
    assert "1 added" in text
    assert "unlabeled" in text.lower()
    assert "--name paper-01" in text


def test_first_paper_tape_matches_one_remark_starter():
    tape = (ROOT / "website" / "captures" / "tapes" / "first-paper.tape").read_text(
        encoding="utf-8"
    )
    starter = (ROOT / "website" / "captures" / "fixtures" / "starter" / "main.tex").read_text(
        encoding="utf-8"
    )
    runner = (ROOT / "website" / "captures" / "run.py").read_text(encoding="utf-8")
    assert "--name paper-01" in tape
    assert "--name demo" not in tape
    assert starter.count(r"\myremark{") == 1
    assert "copytree(STARTER" in runner


def test_export_describes_ui_and_cli():
    text = (DOCS / "export.md").read_text(encoding="utf-8")
    assert "From the UI" in text
    assert "From the terminal" in text
    assert "reviewdistill export" in text


def test_labeling_clip_states_what_you_are_watching():
    text = (DOCS / "labeling.mdx").read_text(encoding="utf-8")
    assert "vocal bout" in text
    assert "Inconsistent terms" in text
    assert "loop" not in text
    shots = (ROOT / "website" / "captures" / "ui_shots.py").read_text(encoding="utf-8")
    assert "The same span is called a vocal bout and a call packet." in shots
    assert "wait_for_timeout(2000)" in shots


def test_homepage_does_not_stress_local_first():
    home = (
        ROOT / "website" / "src" / "components" / "HomepageFeatures" / "index.tsx"
    ).read_text(encoding="utf-8")
    assert "stay on your computer" not in home


def test_homepage_steps_include_extract():
    home = (
        ROOT / "website" / "src" / "components" / "HomepageFeatures" / "index.tsx"
    ).read_text(encoding="utf-8")
    comment = home.index("Comment in the paper")
    extract = home.index("reviewdistill extract")
    label = home.index("Label in the UI")
    export = home.index("Export a skill")
    assert comment < extract < label < export
    assert "col--3" in home
    assert "col--12" not in home
    assert "reviewdistill init" in home
    assert "reviewdistill ui" in home


def test_labeling_defines_leaf():
    text = (DOCS / "labeling.mdx").read_text(encoding="utf-8")
    assert "no children" in text


def test_extract_guide_uses_starter_command():
    text = (DOCS / "extract.md").read_text(encoding="utf-8")
    assert r"\yzc" not in text
    assert r"\myremark" in text


def test_first_paper_says_ui_opens_the_url():
    text = (DOCS / "first-paper.md").read_text(encoding="utf-8")
    assert "reviewdistill ui" in text
    assert "127.0.0.1:8765" in text
    ui = text.index("reviewdistill ui")
    url = text.index("127.0.0.1:8765")
    assert ui < url or "opens" in text.lower() or "serves" in text.lower()


def test_docs_voice_avoids_banned_phrases():
    for path in DOCS.glob("*"):
        if path.suffix not in {".md", ".mdx"}:
            continue
        text = path.read_text(encoding="utf-8")
        for phrase in BANNED:
            assert phrase not in text, f"{path.name}: {phrase}"


def test_pages_workflow_deploys_website_build():
    text = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
    assert "website/build" in text
    assert "actions/upload-pages-artifact@v3" in text
    assert "actions/deploy-pages@v4" in text
    assert "pnpm build" in text
    assert "pages: write" in text
    assert "id-token: write" in text
