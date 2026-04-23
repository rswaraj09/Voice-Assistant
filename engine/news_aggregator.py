"""
News aggregator — fetch, summarize, save, and speak news articles.

Sources:
    - RSS feeds (default; no API key required). Configurable per-category.
    - NewsAPI (optional). Enabled when the env var NEWS_API_KEY is present.

Extractive summarization is done with a lightweight word-frequency algorithm
so the feature works offline. Gemini is used for richer summaries if the
LLM key is available.
"""

import json
import os
import re
import sqlite3
import threading
import time
import webbrowser
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.parse import quote_plus

import eel


DB_PATH = "nora.db"
_db_lock = threading.Lock()
_cache = {}
_CACHE_TTL_S = 30 * 60

# Last articles spoken to the user — powers "save this article" voice command.
_last_spoken_articles = []
_last_category = "general"


DEFAULT_RSS_FEEDS = {
    "technology":   ["http://feeds.bbci.co.uk/news/technology/rss.xml",
                     "https://feeds.feedburner.com/TechCrunch/"],
    "business":     ["http://feeds.bbci.co.uk/news/business/rss.xml"],
    "sports":       ["http://feeds.bbci.co.uk/sport/rss.xml"],
    "health":       ["http://feeds.bbci.co.uk/news/health/rss.xml"],
    "science":      ["http://feeds.bbci.co.uk/news/science_and_environment/rss.xml"],
    "entertainment":["http://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml"],
    "politics":     ["http://feeds.bbci.co.uk/news/politics/rss.xml"],
    "world":        ["http://feeds.bbci.co.uk/news/world/rss.xml"],
    "general":      ["http://feeds.bbci.co.uk/news/rss.xml"],
}


# ── Schema ─────────────────────────────────────────────────────────────────

def _get_connection():
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_news_tables():
    with _db_lock:
        con = _get_connection()
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS saved_articles (
                id INTEGER PRIMARY KEY,
                title VARCHAR(500),
                summary TEXT,
                source VARCHAR(100),
                url VARCHAR(1000),
                category VARCHAR(50),
                saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                user_notes TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS news_preferences (
                id INTEGER PRIMARY KEY,
                preferred_categories VARCHAR(500),
                preferred_sources VARCHAR(500),
                daily_digest_time VARCHAR(10),
                summary_length VARCHAR(20)
            )
        """)
        con.commit()
        con.close()


# ── RSS parsing (falls back to feedparser if installed) ────────────────────

def _parse_rss(url):
    try:
        import feedparser
        feed = feedparser.parse(url)
        out = []
        for entry in feed.entries[:20]:
            out.append({
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
                "summary": entry.get("summary", "") or entry.get("description", ""),
                "published": entry.get("published", ""),
                "source": feed.feed.get("title", url),
            })
        return out
    except ImportError:
        # Minimal RSS parser so the feature works even without feedparser.
        return _naive_rss_parse(url)
    except Exception as e:
        print(f"[news] RSS error for {url}: {e}")
        return []


_RSS_ITEM_RE  = re.compile(r"<item[^>]*>(.*?)</item>", re.IGNORECASE | re.DOTALL)
_RSS_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
_RSS_LINK_RE  = re.compile(r"<link[^>]*>(.*?)</link>", re.IGNORECASE | re.DOTALL)
_RSS_DESC_RE  = re.compile(r"<description[^>]*>(.*?)</description>", re.IGNORECASE | re.DOTALL)
_RSS_DATE_RE  = re.compile(r"<pubDate[^>]*>(.*?)</pubDate>", re.IGNORECASE | re.DOTALL)
_HTML_RE      = re.compile(r"<[^>]+>")


def _clean(s):
    s = _HTML_RE.sub("", s or "")
    s = s.replace("<![CDATA[", "").replace("]]>", "")
    return s.strip()


def _naive_rss_parse(url):
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0 (Nora)"})
        with urlopen(req, timeout=10) as r:
            body = r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[news] fetch error {url}: {e}")
        return []
    out = []
    for item in _RSS_ITEM_RE.findall(body)[:20]:
        title = _RSS_TITLE_RE.search(item)
        link  = _RSS_LINK_RE.search(item)
        desc  = _RSS_DESC_RE.search(item)
        date  = _RSS_DATE_RE.search(item)
        out.append({
            "title":     _clean(title.group(1)) if title else "",
            "url":       _clean(link.group(1))  if link  else "",
            "summary":   _clean(desc.group(1))  if desc  else "",
            "published": _clean(date.group(1))  if date  else "",
            "source":    url,
        })
    return out


# ── NewsAPI (optional) ──────────────────────────────────────────────────────

def _newsapi_fetch(category=None, query=None, limit=10):
    key = os.environ.get("NEWS_API_KEY")
    if not key:
        return None
    base = "https://newsapi.org/v2/"
    if query:
        endpoint = f"{base}everything?q={quote_plus(query)}&pageSize={limit}&apiKey={key}"
    else:
        cat = category if category in {"business", "entertainment", "general",
                                        "health", "science", "sports", "technology"} else "general"
        endpoint = f"{base}top-headlines?category={cat}&pageSize={limit}&apiKey={key}"
    try:
        with urlopen(endpoint, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
        return [{
            "title":     a.get("title", ""),
            "url":       a.get("url", ""),
            "summary":   a.get("description") or a.get("content", "") or "",
            "published": a.get("publishedAt", ""),
            "source":    (a.get("source") or {}).get("name", "NewsAPI"),
        } for a in data.get("articles", [])]
    except Exception as e:
        print(f"[news] NewsAPI error: {e}")
        return None


# ── Public API ─────────────────────────────────────────────────────────────

def fetch_news(category="general", limit=10, source=None):
    """Return a list of article dicts for the given category."""
    cache_key = f"{category}|{limit}|{source}"
    now = time.time()
    if cache_key in _cache and now - _cache[cache_key][0] < _CACHE_TTL_S:
        return _cache[cache_key][1]

    articles = _newsapi_fetch(category=category, limit=limit) if not source else None

    if not articles:
        feeds = DEFAULT_RSS_FEEDS.get(category.lower(), DEFAULT_RSS_FEEDS["general"])
        if source:
            feeds = [source]
        articles = []
        for feed_url in feeds:
            articles.extend(_parse_rss(feed_url))
            if len(articles) >= limit:
                break
        articles = articles[:limit]

    _cache[cache_key] = (now, articles)
    return articles


def search_news(keyword, limit=10):
    articles = _newsapi_fetch(query=keyword, limit=limit)
    if articles:
        return articles
    # Fallback — scrape from the general feed and filter.
    kw = keyword.lower()
    pool = fetch_news("general", limit=30)
    matched = [a for a in pool if kw in a["title"].lower() or kw in a["summary"].lower()]
    return matched[:limit]


def get_trending_news(limit=10):
    return fetch_news("general", limit=limit)


def summarize_article(text, max_sentences=3):
    """Extractive summariser using word-frequency scoring."""
    if not text:
        return ""
    text = _clean(text)
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    sentences = [s for s in sentences if len(s.split()) > 3]
    if len(sentences) <= max_sentences:
        return " ".join(sentences)

    words = re.findall(r"\w+", text.lower())
    stop = {"the", "a", "an", "and", "or", "but", "is", "are", "was", "were",
            "in", "on", "at", "to", "for", "of", "with", "by", "as", "it",
            "this", "that", "has", "have", "be", "been", "from", "which",
            "will", "would", "could", "should", "can", "may", "might"}
    freq = {}
    for w in words:
        if w in stop or len(w) < 3:
            continue
        freq[w] = freq.get(w, 0) + 1

    scored = []
    for idx, s in enumerate(sentences):
        score = sum(freq.get(w.lower(), 0) for w in re.findall(r"\w+", s))
        scored.append((score, idx, s))
    top = sorted(scored, reverse=True)[:max_sentences]
    top_sorted = sorted(top, key=lambda x: x[1])
    return " ".join(s for _, _, s in top_sorted)


def save_article(title, summary, source, url, category, notes=""):
    with _db_lock:
        con = _get_connection()
        cur = con.cursor()
        cur.execute("""
            INSERT INTO saved_articles (title, summary, source, url, category, user_notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (title, summary, source, url, category, notes))
        con.commit()
        con.close()


def list_saved_articles():
    with _db_lock:
        con = _get_connection()
        cur = con.cursor()
        cur.execute("""
            SELECT id, title, summary, source, url, category, saved_at, user_notes
            FROM saved_articles ORDER BY saved_at DESC
        """)
        rows = cur.fetchall()
        con.close()
    return [{
        "id": r[0], "title": r[1], "summary": r[2], "source": r[3],
        "url": r[4], "category": r[5], "saved_at": r[6], "notes": r[7],
    } for r in rows]


def delete_saved_article(article_id):
    with _db_lock:
        con = _get_connection()
        cur = con.cursor()
        cur.execute("DELETE FROM saved_articles WHERE id = ?", (article_id,))
        con.commit()
        con.close()


# ── Voice command handler ─────────────────────────────────────────────────

_CATEGORY_WORDS = list(DEFAULT_RSS_FEEDS.keys()) + ["tech"]
_NEWS_CATEGORY_RE = re.compile(
    r"\b(" + "|".join(_CATEGORY_WORDS) + r")\b.*\bnews\b"
    r"|\bnews\b.*\b(" + "|".join(_CATEGORY_WORDS) + r")\b",
    re.IGNORECASE,
)
_NEWS_SEARCH_RE = re.compile(r"\b(?:news about|search news (?:about|for)|news on)\s+(.+)", re.IGNORECASE)
_TRENDING_RE    = re.compile(r"\b(trending|top)\s+(?:news|headlines)?\b", re.IGNORECASE)
_SAVED_RE       = re.compile(r"\b(?:show|list)\s+(?:my\s+)?saved\s+(?:articles|news)\b", re.IGNORECASE)
_SAVE_THIS_RE   = re.compile(r"\bsave\s+(?:this|that|the\s+first|the\s+last)\s+(?:article|one|news)?\b", re.IGNORECASE)


def _extract_category(query):
    m = _NEWS_CATEGORY_RE.search(query)
    if not m:
        return None
    cat = (m.group(1) or m.group(2) or "").lower()
    if cat == "tech":
        cat = "technology"
    return cat


def handle_news_command(query):
    global _last_category
    from engine.command import speak
    if not query:
        return False

    q = query.strip()

    if _SAVE_THIS_RE.search(q):
        if not _last_spoken_articles:
            speak("There's no recent article to save.")
            return True
        # Save the first article the user most recently heard.
        pick = _last_spoken_articles[0]
        save_article(
            pick.get("title", ""), pick.get("summary", ""),
            pick.get("source", ""), pick.get("url", ""),
            _last_category,
        )
        speak(f"Saved: {pick.get('title', 'article')}.")
        return True

    if _SAVED_RE.search(q):
        saved = list_saved_articles()
        if not saved:
            speak("You have no saved articles.")
        else:
            speak(f"You have {len(saved)} saved articles. Top: {saved[0]['title']}.")
        return True

    m = _NEWS_SEARCH_RE.search(q)
    if m:
        keyword = m.group(1).strip().rstrip(".?!")
        speak(f"Searching news about {keyword}.")
        articles = search_news(keyword, limit=5)
        _last_category = "search"
        _speak_articles(articles)
        return True

    if _TRENDING_RE.search(q):
        speak("Here are the top headlines.")
        articles = get_trending_news(limit=5)
        _last_category = "general"
        _speak_articles(articles)
        return True

    if "news" in q:
        category = _extract_category(q) or "general"
        speak(f"Here are the latest {category} news.")
        articles = fetch_news(category=category, limit=5)
        _last_category = category
        _speak_articles(articles)
        return True

    return False


def _speak_articles(articles):
    global _last_spoken_articles
    from engine.command import speak
    if not articles:
        _last_spoken_articles = []
        speak("No articles found.")
        return
    _last_spoken_articles = list(articles[:3])
    for i, a in enumerate(articles[:3], 1):
        speak(f"{i}. {a['title']}.")


# ── Eel exposures ──────────────────────────────────────────────────────────

@eel.expose
def uiFetchNews(category="general", limit=10):
    try:
        return json.dumps(fetch_news(category=category, limit=limit))
    except Exception as e:
        print(f"[news] uiFetchNews error: {e}")
        return "[]"


@eel.expose
def uiSearchNews(keyword, limit=10):
    try:
        return json.dumps(search_news(keyword, limit))
    except Exception as e:
        print(f"[news] uiSearchNews error: {e}")
        return "[]"


@eel.expose
def uiSaveArticle(title, summary, source, url, category):
    try:
        save_article(title, summary, source, url, category)
        return json.dumps({"ok": True})
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})


@eel.expose
def uiListSavedArticles():
    return json.dumps(list_saved_articles())


@eel.expose
def uiDeleteSavedArticle(article_id):
    delete_saved_article(int(article_id))
    return json.dumps({"ok": True})


@eel.expose
def uiSummarizeText(text, max_sentences=3):
    return summarize_article(text, max_sentences)


init_news_tables()
