#!/usr/bin/env python3
import os, time, threading, tempfile, urllib.request
from pathlib import Path

import requests
from bs4 import BeautifulSoup

QUESTION = os.environ.get("QUESTION", "").strip()
IMAGE_URL = os.environ.get("IMAGE_URL", "").strip()

# ------------------------------------------------------------------
# FAST FAIL GAUTH (5s max)
# ------------------------------------------------------------------

def try_gauth():
    from playwright.sync_api import sync_playwright
    from playwright_stealth import stealth_sync

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            stealth_sync(page)

            page.goto("https://www.gauthmath.com/", timeout=8000)

            # FAIL FAST: if no input quickly → blocked
            page.wait_for_selector("input", timeout=5000)

            browser.close()
            return "⚠️ Gauth responded but parsing disabled for speed."
    except:
        return None

# ------------------------------------------------------------------
# GOOGLE LENS
# ------------------------------------------------------------------

def google_lens():
    if not IMAGE_URL:
        return ""

    try:
        url = f"https://lens.google.com/uploadbyurl?url={IMAGE_URL}"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")

        out = []
        for a in soup.select("a"):
            t = a.get_text(strip=True)
            h = a.get("href")
            if t and h and len(t) > 20:
                out.append(f"🔗 {t}\n{h}")
            if len(out) >= 3:
                break

        return "\n\n".join(out)
    except:
        return ""

# ------------------------------------------------------------------
# BING + DDG PARALLEL
# ------------------------------------------------------------------

def bing(results):
    try:
        r = requests.get(f"https://www.bing.com/search?q={QUESTION}", headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        soup = BeautifulSoup(r.text, "html.parser")
        for li in soup.select("li.b_algo")[:2]:
            results.append(li.get_text(" ", strip=True))
    except:
        pass

def ddg(results):
    try:
        r = requests.get(f"https://duckduckgo.com/html/?q={QUESTION}", headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.select(".result__a")[:2]:
            results.append(a.get_text(strip=True))
    except:
        pass

def search():
    results = []
    t1 = threading.Thread(target=bing, args=(results,))
    t2 = threading.Thread(target=ddg, args=(results,))
    t1.start(); t2.start()
    t1.join(); t2.join()
    return "\n\n".join(results)

# ------------------------------------------------------------------
# VORTEX SOLVER (Pollinations)
# ------------------------------------------------------------------

def vortex_ai(text):
    try:
        r = requests.post(
            "https://text.pollinations.ai/",
            json={"messages":[{"role":"user","content":text}]},
            timeout=15
        )
        return r.json().get("text","")
    except Exception as e:
        return f"AI failed: {e}"

# ------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------

def main():
    print("[Vortex] FAST MODE")

    # 1. Try Gauth (quick check only)
    gauth = try_gauth()

    # 2. Lens
    lens = google_lens()

    # 3. Search (parallel)
    search_results = search()

    combined = f"""
## 🔍 Google Lens
{lens}

## 🌐 Search
{search_results}
"""

    # 4. AI final
    final = vortex_ai(combined or QUESTION)

    answer = f"""
{combined}

## 🧠 Final Answer
{final}
"""

    Path("/tmp/vortex_answer.md").write_text(answer)
    print("[Vortex] Done")

if __name__ == "__main__":
    main()
