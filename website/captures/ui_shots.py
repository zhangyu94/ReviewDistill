from __future__ import annotations

import shutil
from pathlib import Path

SITE = Path(__file__).resolve().parents[1]
IMG = SITE / "static" / "img"
VIDEO = SITE / "static" / "video"

VIEWPORT = {"width": 1360, "height": 680}
SCALE = 2
ZOOM = "1.22"


def _show_list(page) -> None:
    page.get_by_role("button", name="Show a list of comments for scanning").click()


def _open(page, base_url: str) -> None:
    page.goto(base_url, wait_until="networkidle")
    page.get_by_text("Label Taxonomy").wait_for()
    page.evaluate(f"() => {{ document.documentElement.style.zoom = '{ZOOM}'; }}")
    page.evaluate(
        """() => {
          const cards = document.querySelectorAll('.ch-workbench-card');
          if (cards.length >= 2) {
            cards[0].style.flex = '0.78';
            cards[1].style.flex = '1.22';
          }
        }"""
    )
    _show_list(page)
    page.get_by_role("button", name="Show comments in a project file tree").wait_for()


def _context(browser, **extra):
    return browser.new_context(
        viewport=VIEWPORT,
        color_scheme="light",
        device_scale_factor=SCALE,
        **extra,
    )


def _record_assign(page) -> None:
    page.get_by_text("The same span is called a vocal bout and a call packet.").click()
    page.wait_for_timeout(1800)
    page.get_by_text("Choose a label…").click()
    page.wait_for_timeout(2000)
    option = page.get_by_role("option", name="Inconsistent terms")
    option.evaluate("el => el.scrollIntoView({block: 'nearest'})")
    option.click()
    page.get_by_text("Choose a label…").wait_for(state="hidden")
    page.wait_for_timeout(3000)


def capture(base_url: str) -> None:
    from playwright.sync_api import sync_playwright

    IMG.mkdir(parents=True, exist_ok=True)
    VIDEO.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = _context(browser)
        page = context.new_page()
        _open(page, base_url)
        page.screenshot(path=str(IMG / "workbench.png"))

        page.get_by_role(
            "button",
            name="Show one comment at a time with context and location",
        ).click()
        page.get_by_text("Demonstrate is too strong here.").click()
        page.get_by_title("Show details for Overclaiming").click()
        page.screenshot(path=str(IMG / "inspector.png"))

        _show_list(page)
        page.get_by_title("Download a review skill").click()
        page.get_by_role("heading", name="Export").wait_for()
        page.screenshot(path=str(IMG / "export-dialog.png"))
        page.get_by_role("button", name="Close").click()
        context.close()
        browser.close()

        browser = p.chromium.launch()
        video_dir = VIDEO / "_record"
        video_dir.mkdir(parents=True, exist_ok=True)
        context = _context(
            browser,
            record_video_dir=str(video_dir),
            record_video_size=VIEWPORT,
        )
        page = context.new_page()
        _open(page, base_url)
        _record_assign(page)
        video = page.video
        context.close()
        dest = VIDEO / "assign-label.webm"
        if video is not None:
            video.save_as(str(dest))
        browser.close()
        shutil.rmtree(video_dir, ignore_errors=True)
