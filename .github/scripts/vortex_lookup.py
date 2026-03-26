#!/usr/bin/env python3
import os, threading, requests, re
from bs4 import BeautifulSoup
from pathlib import Path

QUESTION = os.environ.get("QUESTION", "").strip()
IMAGE_URL = os.environ.get("IMAGE_URL", "").strip()

# --------------------------------------------------
# 🔍 DOMAIN FILTER (VERY IMPORTANT)
# --------------------------------------------------

BAD_SITES = [
    "godlikeproductions",
    "pinterest",
    "facebook",
    "tiktok",
    "quora"
]

GOOD_HINTS = [
    "math", "stackexchange", "wikipedia",
    "bbc", "khanacademy", "symbolab",
    "wolfram", "mathway"
]

def is_good_result(text):
    text = text.lower()
    if any(bad in text for bad in BAD_SITES):
        return False
    return True

# --------------------------------------------------
# 🔍 GOOGLE LENS (IMPROVED)
# --------------------------------------------------

def google_lens():
    if not IMAGE_URL:
        return ""

    try:
        r = requests.get(
            f"https://lens.google.com/uploadbyurl?url={IMAGE_URL}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )

        soup = BeautifulSoup(r.text, "html.parser")

        results = []
        for a in soup.select("a"):
            text = a.get_text(strip=True)
            if text and len(text) > 25:
                if is_good_result(text):
                    results.append(text)
            if len(results) >= 3:
                break

        return "\n\n".join(results)
    except:
        return ""

# --------------------------------------------------
# 🌐 SEARCH (FILTERED + RANKED)
# --------------------------------------------------

def search_engine(query, results):
    try:
        r = requests.get(
            f"https://www.bing.com/search?q={query}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8
        )
        soup = BeautifulSoup(r.text, "html.parser")

        for li in soup.select("li.b_algo"):
            text = li.get_text(" ", strip=True)

            if not is_good_result(text):
                continue

            score = sum(1 for g in GOOD_HINTS if g in text.lower())

            results.append((score, text))

    except:
        pass


def run_search(query):
    results = []
    t = threading.Thread(target=search_engine, args=(query, results))
    t.start()
    t.join()

    # sort by score
    results.sort(key=lambda x: x[0], reverse=True)

    return "\n\n".join([r[1] for r in results[:3]])

# --------------------------------------------------
# 🤖 POLLINATIONS AI (FIXED)
# --------------------------------------------------

def vortex_ai(prompt):
    try:
        r = requests.post(
            "https://text.pollinations.ai/",
            json={
                "model": "openai",
                "messages": [
                    {"role": "system", "content": "You are a helpful tutor. Solve clearly and correctly."},
                    {"role": "user", "content": prompt}
                ]
            },
            timeout=20
        )

        if not r.text.strip():
            return ""

        try:
            data = r.json()
            return data.get("text", "")
        except:
            return r.text

    except Exception as e:
        return f"AI error: {e}"

# --------------------------------------------------
# 🧠 SIMPLE OCR (IMAGE → TEXT via Lens fallback)
# --------------------------------------------------

def extract_question():
    if QUESTION:
        return QUESTION

    if IMAGE_URL:
        return f"Solve this math problem from an image: {IMAGE_URL}"

    return ""

# --------------------------------------------------
# 🚀 MAIN
# --------------------------------------------------

def main():
    print("[Vortex] Running improved engine")

    query = extract_question()

    # 🔍 Step 1: Lens
    lens = google_lens()

    # 🌐 Step 2: Search
    search = run_search(query)

    combined = f"""
## 🔍 Google Lens
{lens}

## 🌐 Search
{search}
"""

    # 🧠 Step 3: AI
    ai_prompt = f"""
Solve this problem clearly and correctly.

Question:
{query}

Context:
{combined}
"""

    answer = vortex_ai(ai_prompt)

    if not answer:
        answer = "⚠️ AI could not generate a response."

    final = f"""
{combined}

## 🧠 Final Answer
{answer}
"""

    Path("/tmp/vortex_answer.md").write_text(final)
    print("[Vortex] Done")


if __name__ == "__main__":
    main()
