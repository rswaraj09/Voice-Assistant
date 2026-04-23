# Setup Guide — New Features

This guide walks through getting the five new features ([Modes](#mode-system), [News](#news-aggregator), [Avatars](#avatar-creation), [ML Training](#ml-training-integration), [Code-Gen optimizations](#code-generator-optimizations)) running locally. It assumes the base Voice-Assistant project already runs on your machine.

If it doesn't, start from the original project [README.md](README.md) first.

---

## Prerequisites

| Thing | Why | How to check |
|------|-----|--------------|
| Python 3.9–3.11 | The project pins several older packages that won't build on 3.12+ | `python --version` |
| Windows 10 / 11 | Several features (`nircmd`, `Get-StartApps`, `os.startfile`) are Windows-only | already using Windows |
| Microsoft Edge | The app launches in Edge app mode via `start msedge.exe --app=...` | `msedge --version` |
| Internet access | DiceBear (avatars) and RSS feeds (news) need it at runtime | — |
| A Gemini API key | Used by existing Gemini features **and** the new avatar style selector | see [engine/config.py](engine/config.py) |

Nothing else is strictly required. Kaggle CLI, HuggingFace, sklearn, tensorflow, torch, `feedparser`, and a NewsAPI key are **all optional**. The code degrades gracefully when they're missing (see [Optional dependencies](#optional-dependencies)).

---

## 1. Pull the changes

The new / modified files:

```
engine/modes.py              NEW
engine/news_aggregator.py    NEW
engine/avatar_generator.py   NEW
engine/dataset_finder.py     NEW
engine/model_trainer.py      NEW
engine/validators.py         NEW
engine/code_generator.py     MODIFIED — parallel batching + regen loop
engine/ml_project_generator.py MODIFIED — uses dataset_finder + model_trainer
engine/command.py            MODIFIED — voice dispatch + speak() avatar hook
engine/db.py                 EMPTIED (was dev-only script)
main.py                      MODIFIED — imports new modules
templates/index.html         MODIFIED — new tabs + active-avatar host
templates/main.js            MODIFIED — UI wiring
templates/style.css          MODIFIED — avatar animation keyframes
```

## 2. Install base requirements (if you haven't)

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

No new hard dependencies were added. The new modules use only things that should already be installed for the base app (`eel`, `google-generativeai`, `pygame`, `pyttsx3`, etc.) plus the Python standard library.

## 3. Run the app

```powershell
python run.py
```

On first launch after pulling these changes:

- `nora.db` will gain four new tables automatically (`modes`, `mode_items`, `saved_articles`, `news_preferences`, `avatars`) via `CREATE TABLE IF NOT EXISTS`. No migration script to run.
- `templates/assets/avatars/` will be created automatically the first time `engine/avatar_generator` is imported.

## 4. Verify each feature

Open the Edge window, click the gear icon (Settings), and confirm three new tabs exist: **Modes**, **News**, **Avatars**.

### Mode System
1. Settings → Modes → type "coding" in the first box, click **Create**.
2. On the new mode card, pick `app`, type `notepad`, click **Add**.
3. Click **Activate** — Notepad should launch. The card border turns green and an "active" badge appears.
4. Voice test: `"jarvis open coding mode"` — should say "Activating coding mode" and open Notepad.

### News
1. Settings → News → pick a category → click **Fetch**.
2. Articles should appear with Save / Open buttons.
3. Voice test: `"jarvis show me technology news"` — assistant reads the top three titles. Then say `"save that article"` — it gets saved to DB.

### Avatars
1. Settings → Avatars → name "nora" → style `avataaars` → **Create**.
2. Grid updates with an SVG preview.
3. Click **Use** on the card. A circular avatar appears top-right of the main UI.
4. Trigger any voice response (e.g. `"jarvis what time is it"`). The avatar should pulse while the assistant speaks.

### Code Generator optimization
No UI test needed. Trigger a project generation from voice (e.g. `"jarvis create a todo app"`). Watch the console:
- You should see `[CodeGen] ✓ <filename> (N/M)` lines arriving out-of-order (parallel).
- After generation: `[CodeGen] Validation: {files: N, syntax_errors: …}`.
- If any file has syntax errors, you'll see `[CodeGen] Retrying <N> failed file(s): […]` followed by re-gen outcomes.

### ML Training
Trigger `"jarvis create a house price prediction model"`. Watch the console for `[DataSearch]` lines. Generation now runs in parallel (`[MLGen] Generated N/M files.`). If `train.py` somehow wasn't produced, you'll see `[MLGen] train.py injected from deterministic template.`

---

## Optional dependencies

Install any of these only if you want the related feature to work more fully. **None of them are required to start the app.**

```powershell
# Better RSS parsing (recommended for News)
pip install feedparser

# Kaggle dataset discovery
pip install kaggle
# then drop your kaggle.json in %USERPROFILE%\.kaggle\

# HuggingFace dataset discovery
pip install huggingface_hub datasets

# sklearn ML script execution
pip install scikit-learn pandas joblib

# Keras / TensorFlow
pip install tensorflow

# PyTorch (pick the wheel matching your CUDA/CPU)
pip install torch torchvision
```

Environment variables (put them in `.env` at the repo root):

```
GEMINI_API_KEY=...                # already used by the base app
NEWS_API_KEY=...                  # optional — enables NewsAPI fallback in news_aggregator
```

---

## Common setup problems and fixes

### "ImportError: cannot import name 'X' from engine.command"
Usually means Python cached an older `.pyc`. Delete `engine/__pycache__/` and try again.

```powershell
Remove-Item -Recurse -Force engine\__pycache__
```

### "sqlite3.OperationalError: no such column: modes.is_active"
You had a `nora.db` from an earlier run *before* the active-mode migration shipped. Two options:

1. The safe one: the code auto-runs an `ALTER TABLE ... ADD COLUMN is_active` on startup. Just re-launch the app.
2. If that still fails (e.g. the DB was corrupted mid-upgrade): delete `nora.db` and restart. You'll lose saved modes/news/avatars but not the core app data — the original tables (`sys_command`, `web_command`, `contacts`, `info`) regenerate as you use the app.

### Avatars render as plain coloured circles instead of faces
That's the offline fallback SVG. It means the DiceBear API call failed. Usually:
- No internet.
- A firewall / corporate proxy blocks `api.dicebear.com`.
- DiceBear's public API is temporarily down.

The avatar still works — it just looks simpler. Retry the create when network is back.

### News tab shows "No articles" even after clicking Fetch
- Without `feedparser` installed, the stdlib fallback is used; it's less tolerant of malformed feeds. Install feedparser: `pip install feedparser`.
- BBC RSS feeds are blocked in some regions. Try setting `NEWS_API_KEY` and clicking Fetch — the NewsAPI path bypasses RSS.
- Cache hangover: the module caches results for 30 minutes per `(category, limit, source)` tuple. Restart the app if you just fixed a config issue and need a fresh fetch.

### Voice command "open coding mode" opens a new app called "coding mode" instead
This means the mode with that name doesn't exist. The dispatcher routes `open X mode` to the **Mode System** only when `handle_mode_command` matches, otherwise it falls through to the generic `open` handler. Create the mode first in Settings → Modes, then try again.

### "NEWS_API_KEY not set" warnings in console
Not an error. The news module prefers NewsAPI when the key is present, but the RSS path works fine without it. Ignore, or set the env var if you want richer search results.

### ThreadPoolExecutor causes 429 rate-limit errors from Gemini
You're likely on the Gemini free tier. Open [engine/code_generator.py](engine/code_generator.py), find `smart_generate_with_batching`, and reduce `max_workers=4` to `max_workers=2`. The parallel path will still fall back to sequential if <50% of files succeed.

### "ModuleNotFoundError: No module named 'feedparser'"
It's optional — the stdlib parser kicks in automatically. But if you want it, `pip install feedparser`.

### Avatar doesn't animate while Nora is speaking
- Open the browser devtools console (F12 in Edge) — look for `noraAvatarState` log lines. If they're missing, Eel isn't reaching the browser; refresh the page.
- If the log lines appear but the avatar isn't visible, check that you've clicked **Use** on an avatar card.
- Make sure `style.css` was reloaded — Edge sometimes caches aggressively. Hard-refresh with Ctrl+Shift+R.

### ML project generation takes ages or runs out of Gemini quota
The parallel path issues up to 4 concurrent Gemini requests. If you've hit daily quota, either:
- Switch to the sequential fallback by deleting / renaming `smart_generate_with_batching` calls in [engine/ml_project_generator.py](engine/ml_project_generator.py) and [engine/code_generator.py](engine/code_generator.py); or
- Wait for the quota to reset.

### "PRAGMA foreign_keys = ON" does nothing
SQLite silently accepts it even when it can't enforce FKs (e.g. old sqlite3 binary). Our schemas don't rely on FK enforcement to be correct — just used for readability and cascade deletes in `mode_items`. Ignore.

### `python engine/db.py` does nothing
Correct — that's intentional now. The old file had live schema-setup code that pointed at a hardcoded Windows path. It's now a docstring-only module. Actual schema setup happens on module import of each feature.

### The Edge window never opens
[main.py](main.py) calls `start msedge.exe --app="http://localhost:8000/index.html"` after a 2-second delay. If Edge isn't on PATH, open the URL manually.

### Porcupine hotword license errors
Unrelated to these changes but commonly hit during first setup. `pvporcupine` needs a free access key for v2+. The base `engine/features.py:hotword()` already handles the call; if it fails, hotword detection breaks but everything else keeps working (you can still click the mic button).

---

## Rollback

If any change causes trouble and you need to revert:

```powershell
git status                        # confirm what's changed
git diff engine/command.py        # inspect the speak()-hook change
git checkout engine/command.py    # revert individual file
# or, nuclear option:
git checkout .
```

The new files (`engine/modes.py`, `engine/news_aggregator.py`, etc.) are isolated. Deleting them and removing their imports from [main.py](main.py) (lines 9–12) disables the new features cleanly — no other code paths depend on them.

---

## Where to look when something breaks

| Symptom | File to check |
|---------|---------------|
| Mode dispatch wrong | [engine/modes.py](engine/modes.py) regexes at lines `_OPEN_MODE_RE` etc. |
| Avatar not displaying | [templates/main.js](templates/main.js) `refreshActiveAvatar`, [engine/avatar_generator.py](engine/avatar_generator.py) `get_active_avatar` |
| News fetch empty | [engine/news_aggregator.py](engine/news_aggregator.py) `_parse_rss`, `DEFAULT_RSS_FEEDS` |
| Code-gen parallel misbehaves | [engine/code_generator.py](engine/code_generator.py) `smart_generate_with_batching`, `_validate_and_maybe_regenerate` |
| ML project missing train.py | [engine/ml_project_generator.py](engine/ml_project_generator.py) fallback blocks after `smart_generate_with_batching` |
| Voice command doesn't route | [engine/command.py](engine/command.py) `process_query` — mode/news/avatar checks are at the top |

---

## What I have *not* tested end-to-end

Everything static-checks cleanly (Python AST, JS `new Function` parse). But I did not run the Eel app with a live microphone, Gemini key, and Edge browser. Please smoke-test before a demo. The most fragile thing to verify first is the voice-command dispatch order — say a plain phrase like "hey jarvis" and make sure the assistant still falls through to chat. If mode/news/avatar handlers started eating normal queries, the `re.search(r'\bmodes?\b', query)` guards in [engine/command.py](engine/command.py#L572) are the first place to adjust.
