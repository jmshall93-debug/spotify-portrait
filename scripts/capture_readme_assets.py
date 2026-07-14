"""Capture README screenshots from a running Spotify Portrait app.

Usage:
    .\\.venv\\Scripts\\python.exe -m streamlit run app.py --server.port 8501 --server.headless true
    .\\.venv\\Scripts\\python.exe scripts\\capture_readme_assets.py

Or pass --start to launch Streamlit automatically.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
URL = "http://localhost:8501"
VIEWPORT = {"width": 1280, "height": 900}
PY = Path(sys.executable)


def _wait_for_server(timeout: int = 60) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urlopen(URL, timeout=2):
                return
        except Exception:
            time.sleep(1)
    raise RuntimeError(f"Streamlit did not respond at {URL}")


def _wait_for_app(page) -> None:
    page.goto(URL, wait_until="networkidle", timeout=60_000)
    page.wait_for_selector(".hero-title", timeout=30_000)
    page.wait_for_function(
        '() => document.querySelectorAll(\'[data-testid="stPlotlyChart"]\').length === 3',
        timeout=30_000,
    )
    page.wait_for_timeout(2000)


def _clip_region(page, start_selector: str, end_selector: str | None, path: Path, pad: int = 12) -> None:
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(400)
    bounds = page.evaluate(
        """
        ({ startSelector, endSelector, pad }) => {
            const start = document.querySelector(startSelector);
            if (!start) return null;

            let bottom = start.getBoundingClientRect().bottom;
            if (endSelector) {
                const end = document.querySelector(endSelector);
                if (end) bottom = end.getBoundingClientRect().bottom;
            }

            const y = Math.max(0, start.getBoundingClientRect().top - pad);
            return {
                x: 0,
                y,
                width: window.innerWidth,
                height: Math.max(80, bottom - y + pad),
            };
        }
        """,
        {"startSelector": start_selector, "endSelector": end_selector, "pad": pad},
    )
    if not bounds:
        raise RuntimeError(f"Could not locate region starting at {start_selector!r}")
    page.screenshot(path=str(path), clip=bounds)


def _capture_hero(page) -> None:
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(400)
    bounds = page.evaluate(
        """
        (pad) => {
            const start = document.querySelector('.hero-caption') || document.querySelector('.hero-title');
            const mood = [...document.querySelectorAll('.section-label-tight')]
                .find(el => el.textContent.trim() === 'Mood fingerprint');
            if (!start || !mood) return null;

            let bottom = mood.getBoundingClientRect().bottom;
            let node = mood.nextElementSibling;
            while (node) {
                if (node.classList.contains('section-label') || node.classList.contains('library-context-label')) {
                    break;
                }
                bottom = Math.max(bottom, node.getBoundingClientRect().bottom);
                node = node.nextElementSibling;
            }

            const y = Math.max(0, start.getBoundingClientRect().top - pad);
            return {
                x: 0,
                y,
                width: window.innerWidth,
                height: Math.max(120, bottom - y + pad),
            };
        }
        """,
        12,
    )
    if not bounds:
        raise RuntimeError("Hero region not found")
    page.screenshot(path=str(ASSETS / "hero.png"), clip=bounds)


def _capture_composition(page) -> None:
    page.locator(".section-label", has_text="Top genres").first.scroll_into_view_if_needed()
    page.wait_for_timeout(1200)
    bounds = page.evaluate(
        """
        (pad) => {
            const labels = [...document.querySelectorAll('.section-label')];
            const start = labels.find(el => el.textContent.trim() === 'Top genres');
            const charts = document.querySelectorAll('[data-testid="stPlotlyChart"]');
            const chart = charts[0];
            if (!start || !chart) return null;

            const y = Math.max(0, start.getBoundingClientRect().top - pad);
            const bottom = chart.getBoundingClientRect().bottom;
            return {
                x: 0,
                y,
                width: window.innerWidth,
                height: Math.max(120, bottom - y + pad),
            };
        }
        """,
        12,
    )
    if not bounds:
        raise RuntimeError("Composition region not found")
    page.screenshot(path=str(ASSETS / "composition.png"), clip=bounds)


def _capture_structure(page) -> None:
    page.locator(".section-label", has_text="Structure").first.scroll_into_view_if_needed()
    page.locator('[data-testid="stPlotlyChart"]').nth(2).scroll_into_view_if_needed()
    page.wait_for_timeout(1200)
    bounds = page.evaluate(
        """
        (pad) => {
            const labels = [...document.querySelectorAll('.section-label')];
            const start = labels.find(el => el.textContent.trim() === 'Structure');
            const charts = document.querySelectorAll('[data-testid="stPlotlyChart"]');
            const endChart = charts[2];
            if (!start || !endChart) return null;

            const y = Math.max(0, start.getBoundingClientRect().top + window.scrollY - pad);
            const bottom = endChart.getBoundingClientRect().bottom + window.scrollY + pad;
            return {
                x: 0,
                y,
                width: window.innerWidth,
                height: Math.max(120, bottom - y),
            };
        }
        """,
        12,
    )
    if not bounds:
        raise RuntimeError("Structure region not found")

    source_path = ASSETS / "_structure-source.png"
    page.screenshot(path=str(source_path), full_page=True)
    scale = 2
    with Image.open(source_path) as image:
        crop = (
            0,
            int(bounds["y"] * scale),
            min(image.width, int(bounds["width"] * scale)),
            int((bounds["y"] + bounds["height"]) * scale),
        )
        image.crop(crop).save(ASSETS / "structure.png")
    source_path.unlink(missing_ok=True)


def _capture_full_report(page) -> None:
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(500)
    container = page.locator(".block-container")
    box = container.bounding_box()
    if not box:
        raise RuntimeError("Could not locate the report column")

    page.evaluate(
        """
        () => {
            const main = document.querySelector('[data-testid="stMain"]');
            const app = document.querySelector('.stApp');
            if (!main || !app) return;
            const reportHeight = main.scrollHeight;
            main.style.height = `${reportHeight}px`;
            main.style.overflow = 'visible';
            app.style.height = `${reportHeight}px`;
            app.style.overflow = 'visible';
        }
        """
    )
    page.wait_for_timeout(1000)

    source_path = ASSETS / "_full-report-source.png"
    page.screenshot(path=str(source_path), full_page=True)

    scale = 2
    with Image.open(source_path) as image:
        left = max(0, int((box["x"] - 16) * scale))
        right = min(image.width, int((box["x"] + box["width"] + 16) * scale))
        report = image.crop((left, 0, right, image.height))
        report.thumbnail((1200, 2400), Image.Resampling.LANCZOS)
        report.save(ASSETS / "full-report.png")

    source_path.unlink(missing_ok=True)


def capture() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport=VIEWPORT, device_scale_factor=2)
        _wait_for_app(page)
        _capture_hero(page)
        _capture_composition(page)
        _capture_structure(page)
        _capture_full_report(page)
        browser.close()

    for name in ("hero.png", "composition.png", "structure.png", "full-report.png"):
        path = ASSETS / name
        if not path.exists():
            raise RuntimeError(f"Missing capture: {path}")
        print(f"wrote {path} ({path.stat().st_size:,} bytes)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture Spotify Portrait README assets.")
    parser.add_argument(
        "--start",
        action="store_true",
        help="Start Streamlit on port 8501 before capturing.",
    )
    args = parser.parse_args()

    streamlit_proc = None
    if args.start:
        streamlit_proc = subprocess.Popen(
            [
                str(PY),
                "-m",
                "streamlit",
                "run",
                "app.py",
                "--server.port",
                "8501",
                "--server.headless",
                "true",
            ],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _wait_for_server()

    try:
        capture()
    finally:
        if streamlit_proc is not None:
            streamlit_proc.terminate()
            streamlit_proc.wait(timeout=10)


if __name__ == "__main__":
    main()
