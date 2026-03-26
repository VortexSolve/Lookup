#!/usr/bin/env python3
import os, requests, threading, time, re
from pathlib import Path
from bs4 import BeautifulSoup

QUESTION = os.environ.get("QUESTION", "").strip()
IMAGE_URL = os.environ.get("IMAGE_URL", "").strip()

# --------------------------------------------------
# ⚙️ CONFIG
# --------------------------------------------------

TIMEOUT = 8

BAD_KEYWORDS = [
    "buy", "order", "delivery", "near me",
    "yelp", "tripadvisor", "pinterest",
    "tiktok", "facebook", "reddit",
    "shop", "florist"
]

GOOD_SOURCES = [
    "wikipedia", "khan", "bbc",
    "stackexchange", "math", "symbolab",
    "wolfram", "education"
]

# --------------------------------------------------
# 🧠 HELPERS
# --------------------------------------------------

def clean(text):
    return re.sub(r"\s+", " ", text).strip()

def is_good(text):
    t = text.lower()
    if any(b in t for b in BAD_KEYWORDS):
        return False
    return len(t) > 30

def score(text):
    t = text.lower()
    s = 0
    for g in GOOD_SOURCES:
        if g in t:
            s += 3
    if any(x in t for x in ["what", "why", "how", "solve"]):
        s += 2
    return s

# --------------------------------------------------
# 🔍 GOOGLE LENS
# --------------------------------------------------

def google_lens(results):
    if not IMAGE_URL:
        return
    try:
        r = requests.get(
            f"https://lens.google.com/uploadbyurl?url={IMAGE_URL}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=TIMEOUT
        )
        soup = BeautifulSoup(r.text, "html.parser")

        for a in soup.select("a"):
            t = clean(a.get_text())
            if is_good(t):
                results.append(("lens", t))
                if len(results) >= 3:
                    return
    except:
        pass

# --------------------------------------------------
# 🌐 SEARCH ENGINES
# --------------------------------------------------

def bing(results, query):
    try:
        r = requests.get(
            f"https://www.bing.com/search?q={query}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=TIMEOUT
        )
        soup = BeautifulSoup(r.text, "html.parser")

        for li in soup.select("li.b_algo"):
            t = clean(li.get_text(" "))
            if is_good(t):
                results.append(("bing", t))
    except:
        pass


def duckduckgo(results, query):
    try:
        r = requests.get(
            f"https://duckduckgo.com/html/?q={query}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=TIMEOUT
        )
        soup = BeautifulSoup(r.text, "html.parser")

        for r in soup.select(".result"):
            t = clean(r.get_text(" "))
            if is_good(t):
                results.append(("duck", t))
    except:
        pass

# --------------------------------------------------
# 🤖 AI
# --------------------------------------------------

def ask_ai(prompt):
    try:
        r = requests.post(
            "https://text.pollinations.ai/",
            json={
                "model": "openai",
                "messages": [
                    {"role": "system", "content": "Answer clearly and accurately."},
                    {"role": "user", "content": prompt}
                ]
            },
            timeout=20
        )

        if not r.text.strip():
            return ""

        try:
            return r.json().get("text", "")
        except:
            return r.text

    except Exception as e:
        return f"AI error: {e}"

# --------------------------------------------------
# 🧠 ANSWER PROCESSING
# --------------------------------------------------

def short_answer(text):
    if not text:
        return "_No answer_"
    for line in text.split("\n"):
        line = line.strip()
        if len(line) > 25:
            return line
    return text[:200]

def confidence(answer, sources):
    if not answer:
        return "Low"
    if len(sources) > 5:
        return "High"
    if len(sources) > 2:
        return "Medium"
    return "Low"

# --------------------------------------------------
# 🚀 MAIN
# --------------------------------------------------

def main():
    query = QUESTION or f"solve this: {IMAGE_URL}"

    results = []

    threads = [
        threading.Thread(target=google_lens, args=(results,)),
        threading.Thread(target=bing, args=(results, query)),
        threading.Thread(target=duckduckgo, args=(results, query))
    ]

    # ⚡ run in parallel
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # 🧠 sort results
    results.sort(key=lambda x: score(x[1]), reverse=True)

    lens = "\n\n".join([r[1] for r in results if r[0] == "lens"][:3])
    search = "\n\n".join([r[1] for r in results if r[0] != "lens"][:5])

    combined = f"""
Google Lens:
{lens}

Search:
{search}
"""

    # 🤖 AI solve
    ai = ask_ai(f"""
Answer this clearly:

{query}

Context:
{combined}
""")

    if not ai:
        ai = "⚠️ AI failed to generate a response."

    conf = confidence(ai, results)

    # 🎨 FINAL OUTPUT
    final = f"""
# 🌀 Vortex Result

> 🧠 **Answer:**  
> {short_answer(ai)}

> 📊 **Confidence:** {conf}

---

<details>
<summary>📖 Full Explanation</summary>

{ai}
</details>

<details>
<summary>🔍 Google Lens</summary>

{lens or "_None_"}
</details>

<details>
<summary>🌐 Search Results</summary>

{search or "_None_"}
</details>

<details>
<summary>🐛 Debug</summary>

Query: {query}  
Image: {IMAGE_URL or "None"}  
Results: {len(results)}  
Lens chars: {len(lens)}  
Search chars: {len(search)}  
AI chars: {len(ai)}

</details>
"""
