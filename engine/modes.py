"""
Mode System — user-defined voice-activated modes that group apps and links.

Users can say:
    "jarvis open coding mode"     → activates the 'coding' mode
    "create coding mode"          → creates a new empty mode
    "add vs code to coding mode"  → adds an app item
    "list modes"                  → speaks all known modes
    "delete coding mode"          → removes a mode
"""

import json
import os
import re
import sqlite3
import threading
import time
import webbrowser

import eel

from engine.command import speak, openApp


DB_PATH = "nora.db"
_db_lock = threading.Lock()


def _get_connection():
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_mode_tables():
    """Create the mode-related tables if they don't yet exist."""
    with _db_lock:
        con = _get_connection()
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS modes (
                id INTEGER PRIMARY KEY,
                mode_name VARCHAR(100) UNIQUE NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 0
            )
        """)
        # Additive migration — older DBs may lack is_active.
        cur.execute("PRAGMA table_info(modes)")
        cols = {row[1] for row in cur.fetchall()}
        if "is_active" not in cols:
            cur.execute("ALTER TABLE modes ADD COLUMN is_active INTEGER DEFAULT 0")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS mode_items (
                id INTEGER PRIMARY KEY,
                mode_id INTEGER NOT NULL,
                item_type VARCHAR(10) NOT NULL,
                item_ref VARCHAR(1000) NOT NULL,
                item_order INTEGER DEFAULT 0,
                FOREIGN KEY (mode_id) REFERENCES modes(id) ON DELETE CASCADE
            )
        """)
        con.commit()
        con.close()


def _normalize(name):
    return (name or "").strip().lower()


# ── Core CRUD ──────────────────────────────────────────────────────────────

def create_mode(mode_name, description=""):
    name = _normalize(mode_name)
    if not name:
        return False, "Mode name required."
    with _db_lock:
        con = _get_connection()
        try:
            con.execute(
                "INSERT INTO modes (mode_name, description) VALUES (?, ?)",
                (name, description),
            )
            con.commit()
            return True, f"Created mode '{name}'."
        except sqlite3.IntegrityError:
            return False, f"Mode '{name}' already exists."
        finally:
            con.close()


def delete_mode(mode_name):
    name = _normalize(mode_name)
    with _db_lock:
        con = _get_connection()
        cur = con.cursor()
        cur.execute("SELECT id FROM modes WHERE mode_name = ?", (name,))
        row = cur.fetchone()
        if not row:
            con.close()
            return False, f"Mode '{name}' not found."
        mode_id = row[0]
        cur.execute("DELETE FROM mode_items WHERE mode_id = ?", (mode_id,))
        cur.execute("DELETE FROM modes WHERE id = ?", (mode_id,))
        con.commit()
        con.close()
        return True, f"Deleted mode '{name}'."


def list_modes():
    with _db_lock:
        con = _get_connection()
        cur = con.cursor()
        cur.execute("SELECT id, mode_name, description, is_active FROM modes ORDER BY mode_name")
        rows = cur.fetchall()
        con.close()
    return [{"id": r[0], "name": r[1], "description": r[2] or "", "is_active": bool(r[3])} for r in rows]


def get_active_mode():
    with _db_lock:
        con = _get_connection()
        cur = con.cursor()
        cur.execute("SELECT id, mode_name FROM modes WHERE is_active = 1 LIMIT 1")
        row = cur.fetchone()
        con.close()
    return {"id": row[0], "name": row[1]} if row else None


def _set_active_mode(mode_id):
    with _db_lock:
        con = _get_connection()
        cur = con.cursor()
        cur.execute("UPDATE modes SET is_active = 0")
        if mode_id is not None:
            cur.execute("UPDATE modes SET is_active = 1 WHERE id = ?", (mode_id,))
        con.commit()
        con.close()


def _get_mode_id(mode_name):
    name = _normalize(mode_name)
    con = _get_connection()
    cur = con.cursor()
    cur.execute("SELECT id FROM modes WHERE mode_name = ?", (name,))
    row = cur.fetchone()
    con.close()
    return row[0] if row else None


def add_to_mode(mode_name, item_type, item_ref):
    """
    item_type: 'app' or 'link'
    item_ref : app name (e.g. 'notepad') or URL (e.g. 'https://github.com')
    """
    item_type = (item_type or "").strip().lower()
    item_ref = (item_ref or "").strip()
    if item_type not in ("app", "link"):
        return False, "item_type must be 'app' or 'link'."
    if not item_ref:
        return False, "item_ref is required."

    mode_id = _get_mode_id(mode_name)
    if mode_id is None:
        # Auto-create the mode if it doesn't exist yet — friendlier UX.
        ok, _ = create_mode(mode_name)
        if not ok:
            return False, f"Could not create mode '{mode_name}'."
        mode_id = _get_mode_id(mode_name)

    with _db_lock:
        con = _get_connection()
        cur = con.cursor()
        cur.execute(
            "SELECT COALESCE(MAX(item_order), 0) FROM mode_items WHERE mode_id = ?",
            (mode_id,),
        )
        next_order = (cur.fetchone()[0] or 0) + 1
        cur.execute(
            """INSERT INTO mode_items (mode_id, item_type, item_ref, item_order)
               VALUES (?, ?, ?, ?)""",
            (mode_id, item_type, item_ref, next_order),
        )
        con.commit()
        con.close()
    return True, f"Added {item_type} '{item_ref}' to mode '{_normalize(mode_name)}'."


def remove_from_mode(item_id):
    with _db_lock:
        con = _get_connection()
        cur = con.cursor()
        cur.execute("DELETE FROM mode_items WHERE id = ?", (item_id,))
        changed = cur.rowcount
        con.commit()
        con.close()
    return changed > 0


def get_mode_items(mode_name):
    mode_id = _get_mode_id(mode_name)
    if mode_id is None:
        return []
    with _db_lock:
        con = _get_connection()
        cur = con.cursor()
        cur.execute(
            """SELECT id, item_type, item_ref, item_order
               FROM mode_items WHERE mode_id = ? ORDER BY item_order""",
            (mode_id,),
        )
        rows = cur.fetchall()
        con.close()
    return [
        {"id": r[0], "type": r[1], "ref": r[2], "order": r[3]}
        for r in rows
    ]


# ── Activation ─────────────────────────────────────────────────────────────

_URL_RE = re.compile(r"^(https?://|www\.)", re.IGNORECASE)


def _open_link(ref):
    url = ref if _URL_RE.match(ref) else None
    if url is None:
        # Try the web_command table as a named lookup.
        con = _get_connection()
        cur = con.cursor()
        cur.execute(
            "SELECT url FROM web_command WHERE LOWER(name) = ?",
            (ref.lower(),),
        )
        row = cur.fetchone()
        con.close()
        if row:
            url = row[0]
    if url is None:
        # Last fallback: treat as a bare domain.
        url = "https://" + ref if "." in ref else "https://www.google.com/search?q=" + ref
    if url.startswith("www."):
        url = "https://" + url
    webbrowser.open(url)


def _open_app(ref):
    # Try sys_command first — user-defined explicit paths win.
    con = _get_connection()
    cur = con.cursor()
    cur.execute(
        "SELECT path FROM sys_command WHERE LOWER(name) = ?",
        (ref.lower(),),
    )
    row = cur.fetchone()
    con.close()
    if row and row[0] and os.path.exists(row[0]):
        try:
            os.startfile(row[0])
            return
        except Exception as e:
            print(f"[modes] sys_command launch failed: {e}")
    # Fallback to the 4-tier Windows app finder used by the voice "open" handler.
    openApp(ref)


def activate_mode(mode_name, item_delay=1.5):
    name = _normalize(mode_name)
    mode_id = _get_mode_id(name)
    items = get_mode_items(name)
    if not items:
        speak(f"Mode {name} is empty or doesn't exist.")
        return False

    _set_active_mode(mode_id)
    try:
        eel.noraActiveModeChanged(name)
    except Exception:
        pass

    speak(f"Activating {name} mode. Opening {len(items)} items.")
    for item in items:
        try:
            if item["type"] == "app":
                _open_app(item["ref"])
            elif item["type"] == "link":
                _open_link(item["ref"])
        except Exception as e:
            print(f"[modes] failed to open {item}: {e}")
        time.sleep(item_delay)
    speak(f"{name} mode ready.")
    return True


def deactivate_mode():
    _set_active_mode(None)
    try:
        eel.noraActiveModeChanged(None)
    except Exception:
        pass


# ── Voice-command text parsing ─────────────────────────────────────────────

_OPEN_MODE_RE     = re.compile(r"\b(?:open|activate|start|launch)\s+(.+?)\s+mode\b", re.IGNORECASE)
_CREATE_MODE_RE   = re.compile(r"\bcreate\s+(?:a\s+|new\s+)?(?:mode\s+(?:called\s+|named\s+)?(.+)|(.+?)\s+mode)\b", re.IGNORECASE)
_DELETE_MODE_RE   = re.compile(r"\b(?:delete|remove)\s+(.+?)\s+mode\b", re.IGNORECASE)
_LIST_MODE_RE     = re.compile(r"\b(?:list|show)\s+(?:my\s+|all\s+)?modes\b", re.IGNORECASE)
_ADD_TO_MODE_RE   = re.compile(r"\badd\s+(.+?)\s+to\s+(.+?)\s+mode\b", re.IGNORECASE)
_DEACTIVATE_RE    = re.compile(r"\b(?:deactivate|exit|clear|end|stop)\s+(?:current\s+)?mode\b", re.IGNORECASE)
_WHICH_MODE_RE    = re.compile(r"\b(?:what|which)\s+mode\b", re.IGNORECASE)


def handle_mode_command(query):
    """
    Inspect `query` and dispatch if it matches a mode command.
    Returns True if handled (caller should stop further processing).
    """
    if not query:
        return False

    q = query.strip()

    if _DEACTIVATE_RE.search(q):
        deactivate_mode()
        speak("Mode deactivated.")
        return True

    if _WHICH_MODE_RE.search(q):
        active = get_active_mode()
        if active:
            speak(f"You're in {active['name']} mode.")
        else:
            speak("No mode is active right now.")
        return True

    m = _LIST_MODE_RE.search(q)
    if m:
        modes = list_modes()
        if not modes:
            speak("You don't have any modes yet.")
        else:
            names = ", ".join(m_["name"] for m_ in modes)
            speak(f"You have {len(modes)} modes: {names}.")
        return True

    m = _ADD_TO_MODE_RE.search(q)
    if m:
        raw_item, mode_name = m.group(1).strip(), m.group(2).strip()
        item_type = "link" if _URL_RE.match(raw_item) else "app"
        ok, msg = add_to_mode(mode_name, item_type, raw_item)
        speak(msg)
        return True

    m = _DELETE_MODE_RE.search(q)
    if m:
        ok, msg = delete_mode(m.group(1).strip())
        speak(msg)
        return True

    m = _OPEN_MODE_RE.search(q)
    if m:
        activate_mode(m.group(1).strip())
        return True

    m = _CREATE_MODE_RE.search(q)
    if m:
        name = (m.group(1) or m.group(2) or "").strip()
        if name:
            ok, msg = create_mode(name)
            speak(msg)
            return True

    return False


# ── Eel-exposed UI helpers ─────────────────────────────────────────────────

@eel.expose
def uiListModes():
    return json.dumps(list_modes())


@eel.expose
def uiCreateMode(name, description=""):
    ok, msg = create_mode(name, description)
    return json.dumps({"ok": ok, "message": msg})


@eel.expose
def uiDeleteMode(name):
    ok, msg = delete_mode(name)
    return json.dumps({"ok": ok, "message": msg})


@eel.expose
def uiGetModeItems(name):
    return json.dumps(get_mode_items(name))


@eel.expose
def uiAddToMode(name, item_type, item_ref):
    ok, msg = add_to_mode(name, item_type, item_ref)
    return json.dumps({"ok": ok, "message": msg})


@eel.expose
def uiRemoveModeItem(item_id):
    ok = remove_from_mode(int(item_id))
    return json.dumps({"ok": ok})


@eel.expose
def uiActivateMode(name):
    threading.Thread(target=activate_mode, args=(name,), daemon=True).start()
    return json.dumps({"ok": True})


@eel.expose
def uiGetActiveMode():
    return json.dumps(get_active_mode() or {})


@eel.expose
def uiDeactivateMode():
    deactivate_mode()
    return json.dumps({"ok": True})


# Initialise tables on import so the module is self-contained.
init_mode_tables()
