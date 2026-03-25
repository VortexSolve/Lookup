<p align="center">
  <img src="https://raw.githubusercontent.com/VortexSolve/Solver/main/logo.png" width="120" alt="Vortex Lookup">
</p>

---

<p align="center">
  <a href="https://github.com/VortexSolve/Lookup/releases/latest"><img src="https://img.shields.io/github/v/release/YOUR_USERNAME/Vortex-Lookup?label=version&style=for-the-badge&color=7c6aff"></a>
  <a href="https://github.com/VortexSolve/Lookup/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-GPL--3.0-34d399?style=for-the-badge"></a>
  <a href="https://github.com/VortexSolve/Lookup/stargazers"><img src="https://img.shields.io/github/stars/YOUR_USERNAME/Vortex-Lookup?style=for-the-badge&color=fb923c"></a>
</p>

---

# Vortex Lookup

Vortex Lookup is a **GitHub-native automation** that searches [Gauth](https://www.gauthmath.com/) on your behalf — just open an issue, tag it `searchthis`, and get the answer posted back as a comment automatically. Supports both **text questions** and **image uploads**, with a completely fresh browser session cleared of all cookies and storage every single time.

> Why open a browser when your repo can do it for you?

<details>
  <summary><b>💡 Why does this exist?</b></summary>

Sometimes you're deep in a repo and just need a quick answer. Vortex Lookup turns GitHub Issues into a zero-friction question interface — no new tabs, no accounts, no copy-pasting. Submit the issue, get the answer, move on.

By keeping it open-source:
- Anyone can audit exactly what the automation does
- The browser session is fully sandboxed and stateless
- No API keys or secrets are required whatsoever
- ⭐ **Your questions never touch any third-party service except Gauth**

</details>

<details>
  <summary><b>❓ How do I submit a question?</b></summary>

**Option A — Issue Template (recommended)**

1. Go to **Issues → New Issue**
2. Select **🔍 Vortex Lookup**
3. Choose *Text Question* or *Image Upload*
4. Fill in your question or paste an image URL
5. Submit — the `searchthis` label is applied automatically

**Option B — Manual label**

Open any issue and apply the `searchthis` label yourself. The workflow fires on both `opened` and `labeled` events.

> For images, paste a direct URL or drag-and-drop into the issue body — GitHub generates an embed like `![image](https://...)` which Vortex Lookup parses automatically.

</details>

<details>
  <summary><b>🔧 How it works</b></summary>

```
GitHub Issue  →  label: searchthis
      │
      ▼
GitHub Actions Workflow
      │
      ├─ Parse issue body (text question or image URL)
      ├─ Post "searching..." comment
      │
      ▼
vortex_lookup.py  (Playwright + headless Chromium)
      │
      ├─ Navigate to gauthmath.com
      ├─ Clear cookies + localStorage + sessionStorage
      ├─ Reload page (fresh session guaranteed)
      │
      ├─ [Text]  → fill search input → press Enter
      ├─ [Image] → download image → upload via file input
      │
      ├─ Wait for answer element to appear
      ├─ Extract inner HTML → convert to Markdown
      └─ Write to /tmp/vortex_answer.md
      │
      ▼
GitHub Actions Workflow
      │
      ├─ Post answer as issue comment
      └─ Close issue as "completed"
```

</details>

<details>
  <summary><b>🚀 Setup</b></summary>

**1. Copy the files into your repository**

```
.github/
├── workflows/
│   └── vortex-lookup.yml
├── scripts/
│   └── vortex_lookup.py
└── ISSUE_TEMPLATE/
    └── vortex-lookup.yml
```

**2. Enable Actions write permissions**

Go to **Settings → Actions → General → Workflow permissions** and select *Read and write permissions*.

**3. Done.** No secrets. No API keys. No configuration needed.

</details>

<details>
  <summary><b>⚙️ Configuration</b></summary>

| What | Where | How |
|------|-------|-----|
| Change trigger label | `vortex-lookup.yml` (workflow) | Replace `searchthis` with any label name |
| Keep issues open | `vortex-lookup.yml` (workflow) | Remove the "Close issue" step |
| Increase timeout | `vortex_lookup.py` | Change `timeout=90_000` (milliseconds) |
| Debug screenshot on failure | `vortex-lookup.yml` (workflow) | Add `actions/upload-artifact` step on `failure()` |

</details>

<details>
  <summary><b>📦 Dependencies</b></summary>

All installed automatically by the workflow runner — nothing to install locally.

| Package | Purpose |
|---------|---------|
| `playwright` | Headless browser automation |
| `Pillow` | Image handling |
| `chromium` | Browser engine (via `playwright install`) |

</details>

---

> [!NOTE]
> Vortex Lookup interacts with Gauth's public web interface via headless browser automation.
> No data is stored or logged by this project. Use responsibly and in accordance with [Gauth's Terms of Service](https://www.gauthmath.com/).

> [!TIP]
> If the workflow times out, a debug screenshot is saved to `/tmp/vortex_debug.png`.
> Add an `actions/upload-artifact` step in the workflow to retrieve it.

---

> Vortex Lookup README.md  
> A GitHub-native automation that searches Gauth from your Issues
>
> Copyright (C) 2026  
> https://github.com/YOUR_USERNAME/Vortex-Lookup
>
> This program is free software: you can redistribute it and/or modify
> it under the terms of the GNU General Public License as published by
> the Free Software Foundation, either version 3 of the License, or
> (at your option) any later version.
>
> This program is distributed in the hope that it will be useful,
> but WITHOUT ANY WARRANTY; without even the implied warranty of
> MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
> GNU General Public License for more details.
>
> You should have received a copy of the GNU General Public License
> along with this program. If not, see <https://www.gnu.org/licenses>.

This project was made with the use of generative AI.  
Readme inspired by [iis.Stupid.Menu](https://github.com/iiDk-the-actual/iis.Stupid.Menu)
