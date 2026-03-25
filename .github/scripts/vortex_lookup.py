#!/usr/bin/env python3
"""
Vortex Lookup - GitHub Actions automation script.
Uses Playwright to search Gauth with a text question or image,
then saves the answer as Markdown to /tmp/vortex_answer.md.

Clears cookies, localStorage, and sessionStorage before every search.
"""

import os
import sys
import time
import tempfile
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

GAUTH_URL = "https://www.gauthmath.com/"

# Selectors
TEXT_INPUT_SELECTOR = 'input.SearchInput_input__mhkh5Y[type="search"]'
FILE_INPUT_SELECTOR  = 'input.UploadImage_file__zJYRAZ[type="file"]'
ANSWER_SELECTOR      = "div.AnswerStructure_as__k7_0_7"

# ---------------------------------------------------------------------------
# HTML → Markdown conversion (lightweight, no external deps beyond stdlib)
# ---------------------------------------------------------------------------
import re
import html as html_module

def _tag(pattern, replacement):
    return (re.compile(pattern, re.IGNORECASE | re.DOTALL), replacement)

HTML_RULES = [
    # Headings
    _tag(r"<h1[^>]*>(.*?)</h1>", r"# \1\n"),
    _tag(r"<h2[^>]*>(.*?)</h2>", r"## \1\n"),
    _tag(r"<h3[^>]*>(.*?)</h3>", r"### \1\n"),
    _tag(r"<h4[^>]*>(.*?)</h4>", r"#### \1\n"),
    # Bold / italic
    _tag(r"<strong[^>]*>(.*?)</strong>", r"**\1**"),
    _tag(r"<b[^>]*>(.*?)</b>",           r"**\1**"),
    _tag(r"<em[^>]*>(.*?)</em>",         r"*\1*"),
    _tag(r"<i[^>]*>(.*?)</i>",           r"*\1*"),
    # Links
    _tag(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', r"[\2](\1)"),
    # Images
    _tag(r'<img[^>]+alt=["\']([^"\']*)["\'][^>]+src=["\']([^"\']+)["\'][^>]*/?>',  r"![\1](\2)"),
    _tag(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*/?>',  r"![](\1)"),
    # Lists
    _tag(r"<ul[^>]*>(.*?)</ul>",         lambda m: re.sub(r"<li[^>]*>(.*?)</li>", r"\n- \1", m.group(1), flags=re.IGNORECASE|re.DOTALL) + "\n"),
    _tag(r"<ol[^>]*>(.*?)</ol>",         _tag_ol),
    # Table (simple)
    _tag(r"<table[^>]*>(.*?)</table>",   lambda m: _convert_table(m.group(1))),
    # Code
    _tag(r"<pre[^>]*><code[^>]*>(.*?)</code></pre>", r"\n```\n\1\n```\n"),
    _tag(r"<code[^>]*>(.*?)</code>",     r"`\1`"),
    # Paragraphs / line breaks
    _tag(r"<br\s*/?>",                   r"\n"),
    _tag(r"<p[^>]*>(.*?)</p>",           r"\1\n\n"),
    _tag(r"<div[^>]*>(.*?)</div>",       r"\1\n"),
    # Horizontal rule
    _tag(r"<hr\s*/?>",                   r"\n---\n"),
    # Strip remaining tags
    _tag(r"<[^>]+>",                     r""),
]

def _tag_ol(match):
    items = re.findall(r"<li[^>]*>(.*?)</li>", match.group(1), re.IGNORECASE | re.DOTALL)
    return "\n".join(f"{i+1}. {item.strip()}" for i, item in enumerate(items)) + "\n"

def _convert_table(inner_html):
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", inner_html, re.IGNORECASE | re.DOTALL)
    md_rows = []
    for idx, row in enumerate(rows):
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.IGNORECASE | re.DOTALL)
        cells = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
        md_rows.append("| " + " | ".join(cells) + " |")
        if idx == 0:
            md_rows.append("| " + " | ".join(["---"] * len(cells)) + " |")
    return "\n".join(md_rows) + "\n"

def html_to_markdown(html: str) -> str:
    text = html
    for pattern, replacement in HTML_RULES:
        if callable(replacement):
            text = pattern.sub(replacement, text)
        else:
            text = pattern.sub(replacement, text)
    # Decode HTML entities
    text = html_module.unescape(text)
    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

# ---------------------------------------------------------------------------
# Storage-clearing helper
# ---------------------------------------------------------------------------

def clear_browser_storage(page):
    """Clear cookies, localStorage, and sessionStorage."""
    try:
        page.context.clear_cookies()
    except Exception:
        pass
    try:
        page.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Core search functions
# ---------------------------------------------------------------------------

def search_text(page, question: str) -> str:
    print(f"[Vortex] Navigating to {GAUTH_URL} ...")
    page.goto(GAUTH_URL, wait_until="domcontentloaded", timeout=60_000)
    clear_browser_storage(page)
    page.reload(wait_until="domcontentloaded", timeout=60_000)

    print(f"[Vortex] Typing question: {question[:80]}...")
    page.wait_for_selector(TEXT_INPUT_SELECTOR, timeout=30_000)
    page.fill(TEXT_INPUT_SELECTOR, "")
    page.fill(TEXT_INPUT_SELECTOR, question)
    page.press(TEXT_INPUT_SELECTOR, "Enter")

    return _wait_for_answer(page)


def search_image(page, image_path: str) -> str:
    print(f"[Vortex] Navigating to {GAUTH_URL} ...")
    page.goto(GAUTH_URL, wait_until="domcontentloaded", timeout=60_000)
    clear_browser_storage(page)
    page.reload(wait_until="domcontentloaded", timeout=60_000)

    print(f"[Vortex] Uploading image: {image_path}")
    page.wait_for_selector(FILE_INPUT_SELECTOR, timeout=30_000)
    page.set_input_files(FILE_INPUT_SELECTOR, image_path)

    return _wait_for_answer(page)


def _wait_for_answer(page) -> str:
    print("[Vortex] Waiting for answer to appear...")
    try:
        page.wait_for_selector(ANSWER_SELECTOR, timeout=90_000)
    except PlaywrightTimeoutError:
        # Take a screenshot for debugging
        page.screenshot(path="/tmp/vortex_debug.png", full_page=True)
        raise RuntimeError(
            "Timed out waiting for Gauth answer. "
            "A debug screenshot has been saved to /tmp/vortex_debug.png."
        )

    # Small extra wait for content to stabilise
    time.sleep(2)

    answer_html = page.inner_html(ANSWER_SELECTOR)
    return html_to_markdown(answer_html)

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    query_type = os.environ.get("QUERY_TYPE", "Text Question").strip()
    question   = os.environ.get("QUESTION",   "").strip()
    image_url  = os.environ.get("IMAGE_URL",  "").strip()

    if not question and not image_url:
        print("[Vortex] ERROR: No question text or image URL provided.", file=sys.stderr)
        Path("/tmp/vortex_answer.md").write_text(
            "❌ **No input provided.** Please supply a text question or an image URL."
        )
        sys.exit(1)

    # Download image if needed
    image_path = None
    if image_url:
        suffix = Path(image_url.split("?")[0]).suffix or ".png"
        tmp_img = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        print(f"[Vortex] Downloading image from {image_url} ...")
        try:
            urllib.request.urlretrieve(image_url, tmp_img.name)
            image_path = tmp_img.name
            print(f"[Vortex] Image saved to {image_path}")
        except Exception as e:
            print(f"[Vortex] WARNING: Could not download image: {e}", file=sys.stderr)
            image_path = None

    answer = ""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
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
                answer = search_image(page, image_path)
            else:
                answer = search_text(page, question)
        except Exception as e:
            print(f"[Vortex] ERROR: {e}", file=sys.stderr)
            answer = f"❌ **Vortex Lookup encountered an error:**\n\n```\n{e}\n```"
        finally:
            context.close()
            browser.close()

    output_path = Path("/tmp/vortex_answer.md")
    output_path.write_text(answer, encoding="utf-8")
    print(f"[Vortex] Answer written to {output_path} ({len(answer)} chars).")


if __name__ == "__main__":
    main()
