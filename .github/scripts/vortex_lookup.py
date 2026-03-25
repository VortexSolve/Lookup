#!/usr/bin/env python3
import os
import sys
import time
import tempfile
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

GAUTH_URL = "https://www.gauthmath.com/"

# ✅ Robust selectors (no fragile class names)
TEXT_INPUT_SELECTOR = 'input[type="search"]'
FILE_INPUT_SELECTOR = 'input[type="file"]'
ANSWER_SELECTOR_CANDIDATES = [
    'div[class*="AnswerStructure"]',
    'div:has-text("Answer")',
    'div:has-text("Solution")',
    'main'
]

# ---------------------------------------------------------------------------
# HTML → Markdown (same as yours, unchanged for brevity)
# ---------------------------------------------------------------------------
import re, html as html_module

def html_to_markdown(html: str) -> str:
    text = re.sub(r"<[^>]+>", "", html)
    text = html_module.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clear_browser_storage(page):
    try:
        page.context.clear_cookies()
        page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
    except:
        pass


def human_delay():
    time.sleep(1.2)


def wait_for_any_selector(page, selectors, timeout=90000):
    start = time.time()
    while time.time() - start < timeout / 1000:
        for sel in selectors:
            if page.locator(sel).count() > 0:
                return sel
        time.sleep(1)
    raise PlaywrightTimeoutError("No answer selector found")


def debug_dump(page, name="debug"):
    path = f"/tmp/vortex_{name}.png"
    page.screenshot(path=path, full_page=True)
    print(f"[Vortex] Debug screenshot saved: {path}")


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def open_gauth(page):
    print("[Vortex] Opening Gauth...")
    page.goto(GAUTH_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_load_state("networkidle")

    clear_browser_storage(page)
    page.reload(wait_until="domcontentloaded")

    # Try closing popups if present
    try:
        page.click('button:has-text("Accept")', timeout=3000)
    except:
        pass


def search_text(page, question):
    open_gauth(page)

    print("[Vortex] Waiting for search input...")
    page.wait_for_selector(TEXT_INPUT_SELECTOR, timeout=60000)

    page.click(TEXT_INPUT_SELECTOR)
    page.fill(TEXT_INPUT_SELECTOR, question)
    human_delay()
    page.keyboard.press("Enter")

    return get_answer(page)


def search_image(page, image_path):
    open_gauth(page)

    print("[Vortex] Looking for upload input...")

    # Try clicking upload button first (UI sometimes hides input)
    try:
        page.click('button:has-text("Upload")', timeout=5000)
    except:
        pass

    page.wait_for_selector(FILE_INPUT_SELECTOR, timeout=60000, state="attached")

    page.set_input_files(FILE_INPUT_SELECTOR, image_path)

    return get_answer(page)


def get_answer(page):
    print("[Vortex] Waiting for answer...")

    try:
        selector = wait_for_any_selector(page, ANSWER_SELECTOR_CANDIDATES)
    except PlaywrightTimeoutError:
        debug_dump(page, "no_answer")
        raise RuntimeError("Timed out waiting for answer")

    time.sleep(3)

    html = page.inner_html(selector)
    return html_to_markdown(html)


# ---------------------------------------------------------------------------
# Retry wrapper (VERY IMPORTANT)
# ---------------------------------------------------------------------------

def run_with_retries(fn, retries=3):
    for i in range(retries):
        try:
            return fn()
        except Exception as e:
            print(f"[Vortex] Attempt {i+1} failed: {e}")
            time.sleep(3)
    raise RuntimeError("All retries failed")


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

def main():
    query_type = os.environ.get("QUERY_TYPE", "").strip()
    question   = os.environ.get("QUESTION", "").strip()
    image_url  = os.environ.get("IMAGE_URL", "").strip()

    if not question and not image_url:
        Path("/tmp/vortex_answer.md").write_text("❌ No input provided.")
        sys.exit(1)

    image_path = None
    if image_url:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        urllib.request.urlretrieve(image_url, tmp.name)
        image_path = tmp.name

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )

        page = context.new_page()

        try:
            if image_path:
                answer = run_with_retries(lambda: search_image(page, image_path))
            else:
                answer = run_with_retries(lambda: search_text(page, question))
        except Exception as e:
            debug_dump(page, "fatal")
            answer = f"❌ Vortex failed:\n\n```\n{e}\n```"

        context.close()
        browser.close()

    Path("/tmp/vortex_answer.md").write_text(answer, encoding="utf-8")
    print("[Vortex] Done.")


if __name__ == "__main__":
    main()
