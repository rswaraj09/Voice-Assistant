"""
Avatar generator — 2D avatar creation and management.

Uses the public DiceBear API for parametric avatars (no API key required).
Styles: adventurer, avataaars, big-ears, bottts, fun-emoji, lorelei, micah,
miniavs, notionists, personas, pixel-art, thumbs.

Generated avatars are saved as SVG to templates/assets/avatars/ so the
frontend can display them directly.
"""

import json
import os
import re
import sqlite3
import threading
import time
from urllib.parse import quote_plus
from urllib.request import urlopen, Request

import eel


DB_PATH = "nora.db"
_db_lock = threading.Lock()

_BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
AVATAR_DIR  = os.path.normpath(os.path.join(_BASE_DIR, "..", "templates", "assets", "avatars"))
os.makedirs(AVATAR_DIR, exist_ok=True)

AVAILABLE_STYLES = [
    "adventurer", "avataaars", "big-ears", "bottts", "fun-emoji", "lorelei",
    "micah", "miniavs", "notionists", "personas", "pixel-art", "thumbs",
]


# ── Schema ─────────────────────────────────────────────────────────────────

def _get_connection():
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_avatar_tables():
    with _db_lock:
        con = _get_connection()
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS avatars (
                id INTEGER PRIMARY KEY,
                name VARCHAR(100) UNIQUE,
                description TEXT,
                image_path VARCHAR(500),
                model_path VARCHAR(500),
                customization_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 0
            )
        """)
        con.commit()
        con.close()


# ── Generation ─────────────────────────────────────────────────────────────

def _fetch_dicebear_svg(style, seed):
    url = f"https://api.dicebear.com/7.x/{style}/svg?seed={quote_plus(seed)}"
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0 (Nora)"})
        with urlopen(req, timeout=15) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[avatar] DiceBear fetch failed: {e}")
        return None


def _fallback_svg(seed):
    # Deterministic colour pick based on seed.
    h = sum(ord(c) for c in seed) % 360
    return f"""<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 200'>
  <circle cx='100' cy='100' r='100' fill='hsl({h},70%,55%)'/>
  <circle cx='75'  cy='85'  r='10' fill='#fff'/>
  <circle cx='125' cy='85'  r='10' fill='#fff'/>
  <path d='M70 130 Q100 160 130 130' stroke='#fff' stroke-width='6' fill='none' stroke-linecap='round'/>
</svg>"""


def generate_avatar_from_parameters(name, style="avataaars", seed=None, description=""):
    """Create an avatar by parameters and persist it."""
    style = style.lower().strip() if style else "avataaars"
    if style not in AVAILABLE_STYLES:
        return {"ok": False, "message": f"Unknown style. Available: {', '.join(AVAILABLE_STYLES)}"}

    name = (name or "").strip()
    if not name:
        return {"ok": False, "message": "Avatar name is required."}

    seed = seed or name
    svg  = _fetch_dicebear_svg(style, seed) or _fallback_svg(seed)

    safe_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", name)
    filename  = f"{safe_name}_{int(time.time())}.svg"
    file_path = os.path.join(AVATAR_DIR, filename)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(svg)
    except Exception as e:
        return {"ok": False, "message": f"Could not save avatar file: {e}"}

    # relative path for the frontend
    rel_path = f"assets/avatars/{filename}"

    customization = json.dumps({"style": style, "seed": seed})

    with _db_lock:
        con = _get_connection()
        cur = con.cursor()
        try:
            cur.execute(
                """INSERT INTO avatars (name, description, image_path, customization_json, is_active)
                   VALUES (?, ?, ?, ?, 0)""",
                (name, description, rel_path, customization),
            )
            avatar_id = cur.lastrowid
            con.commit()
        except sqlite3.IntegrityError:
            con.close()
            return {"ok": False, "message": f"Avatar '{name}' already exists."}
        finally:
            con.close()

    return {"ok": True, "message": f"Avatar '{name}' created.",
            "id": avatar_id, "image_path": rel_path, "style": style, "seed": seed}


def generate_avatar_from_description(name, description):
    """
    Use the assistant's existing Gemini integration to extract avatar
    parameters from a free-text description, then synthesise via DiceBear.
    """
    style = "avataaars"
    seed  = name

    try:
        from engine.config import LLM_KEY
        import google.generativeai as genai
        genai.configure(api_key=LLM_KEY)
        model  = genai.GenerativeModel("gemini-2.5-flash")
        prompt = (
            f"Pick ONE avatar style from this list for the description below: "
            f"{', '.join(AVAILABLE_STYLES)}.\n"
            f"Respond with just the style name — nothing else.\n"
            f"Description: {description}"
        )
        resp = model.generate_content(prompt)
        candidate = (resp.text or "").strip().lower()
        candidate = re.sub(r"[^a-z\-]", "", candidate)
        if candidate in AVAILABLE_STYLES:
            style = candidate
        # Seed influences the generated features deterministically.
        seed = description[:60] or name
    except Exception as e:
        print(f"[avatar] Gemini style selection skipped: {e}")

    return generate_avatar_from_parameters(name, style=style, seed=seed, description=description)


# ── CRUD ───────────────────────────────────────────────────────────────────

def list_avatars():
    with _db_lock:
        con = _get_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT id, name, description, image_path, customization_json, is_active
            FROM avatars ORDER BY created_at DESC
        """)
        rows = cur.fetchall()
        con.close()
    return [{
        "id": r[0], "name": r[1], "description": r[2], "image_path": r[3],
        "customization": json.loads(r[4]) if r[4] else {}, "is_active": bool(r[5]),
    } for r in rows]


def set_active_avatar(avatar_id):
    with _db_lock:
        con = _get_connection()
        cur = con.cursor()
        cur.execute("UPDATE avatars SET is_active = 0")
        cur.execute("UPDATE avatars SET is_active = 1 WHERE id = ?", (avatar_id,))
        con.commit()
        con.close()


def get_active_avatar():
    with _db_lock:
        con = _get_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT id, name, image_path FROM avatars
            WHERE is_active = 1 LIMIT 1
        """)
        row = cur.fetchone()
        con.close()
    if not row:
        return None
    return {"id": row[0], "name": row[1], "image_path": row[2]}


def delete_avatar(avatar_id):
    with _db_lock:
        con = _get_connection()
        cur = con.cursor()
        cur.execute("SELECT image_path FROM avatars WHERE id = ?", (avatar_id,))
        row = cur.fetchone()
        if row:
            full_path = os.path.normpath(os.path.join(_BASE_DIR, "..", "templates", row[0]))
            try:
                if os.path.exists(full_path):
                    os.remove(full_path)
            except Exception as e:
                print(f"[avatar] file delete failed: {e}")
            cur.execute("DELETE FROM avatars WHERE id = ?", (avatar_id,))
            con.commit()
        con.close()


# ── Voice commands ─────────────────────────────────────────────────────────

_CREATE_AVATAR_RE = re.compile(r"\b(?:create|make|generate)\s+(?:a\s+|an\s+)?avatar(?:\s+(?:named|called)\s+(\S+))?", re.IGNORECASE)
_LIST_AVATAR_RE   = re.compile(r"\b(?:list|show)\s+(?:my\s+|all\s+)?avatars?\b", re.IGNORECASE)
_SWITCH_AVATAR_RE = re.compile(r"\b(?:switch to|activate|use)\s+avatar\s+(\S+)", re.IGNORECASE)
_DELETE_AVATAR_RE = re.compile(r"\b(?:delete|remove)\s+avatar\s+(\S+)", re.IGNORECASE)


def handle_avatar_command(query):
    from engine.command import speak, takecommand
    if not query:
        return False

    if _LIST_AVATAR_RE.search(query):
        avatars = list_avatars()
        if not avatars:
            speak("You don't have any avatars yet.")
        else:
            names = ", ".join(a["name"] for a in avatars)
            speak(f"You have {len(avatars)} avatars: {names}.")
        return True

    m = _SWITCH_AVATAR_RE.search(query)
    if m:
        name = m.group(1).strip()
        avatars = [a for a in list_avatars() if a["name"].lower() == name.lower()]
        if not avatars:
            speak(f"Avatar {name} not found.")
            return True
        set_active_avatar(avatars[0]["id"])
        speak(f"Switched to avatar {name}.")
        try:
            eel.noraUpdateActiveAvatar(avatars[0]["image_path"])
        except Exception:
            pass
        return True

    m = _DELETE_AVATAR_RE.search(query)
    if m:
        name = m.group(1).strip()
        avatars = [a for a in list_avatars() if a["name"].lower() == name.lower()]
        if avatars:
            delete_avatar(avatars[0]["id"])
            speak(f"Deleted avatar {name}.")
        else:
            speak(f"Avatar {name} not found.")
        return True

    m = _CREATE_AVATAR_RE.search(query)
    if m:
        name = (m.group(1) or "").strip()
        if not name:
            speak("What should I name the avatar?")
            name = (takecommand() or "").strip()
        if not name:
            speak("Cancelled — no name given.")
            return True
        speak("Describe the avatar, or say skip to use a default style.")
        desc = (takecommand() or "").strip()
        if not desc or desc.lower().startswith("skip"):
            result = generate_avatar_from_parameters(name)
        else:
            result = generate_avatar_from_description(name, desc)
        speak(result.get("message", "Done."))
        if result.get("ok"):
            try:
                eel.noraAvatarsChanged()
            except Exception:
                pass
        return True

    return False


# ── Eel ────────────────────────────────────────────────────────────────────

@eel.expose
def uiListAvatars():
    return json.dumps(list_avatars())


@eel.expose
def uiCreateAvatar(name, style="avataaars", seed=None, description=""):
    return json.dumps(generate_avatar_from_parameters(name, style, seed, description))


@eel.expose
def uiCreateAvatarFromDescription(name, description):
    return json.dumps(generate_avatar_from_description(name, description))


@eel.expose
def uiSetActiveAvatar(avatar_id):
    set_active_avatar(int(avatar_id))
    return json.dumps({"ok": True})


@eel.expose
def uiDeleteAvatar(avatar_id):
    delete_avatar(int(avatar_id))
    return json.dumps({"ok": True})


@eel.expose
def uiGetActiveAvatar():
    a = get_active_avatar()
    return json.dumps(a or {})


@eel.expose
def uiAvatarStyles():
    return json.dumps(AVAILABLE_STYLES)


init_avatar_tables()
