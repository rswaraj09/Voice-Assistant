
import json
import re

import google.generativeai as genai

import engine.command as cmd
from engine.command import speak, takecommand
from engine.config import LLM_KEY

HINDI_VOICE = "hi-IN-SwaraNeural"   # female; use "hi-IN-MadhurNeural" for male
MODEL_NAME = "gemini-2.5-flash"

# Words that trigger the feature (Roman + Devanagari). Used by command.py too.
POEM_TRIGGER_PATTERN = (
    r"\b(poem|poems|poetry|kavita|kavitaa|kavitayen|shayari|shayri|shayeri|"
    r"कविता|शायरी)\b"
)

_FILLER_WORDS = [
    # request words
    "a", "an", "the", "me", "mujhe", "mere", "liye", "ke", "ki", "ka", "ko",
    "write", "likho", "likh", "likhna", "likhiye", "sunao", "suna", "sunana",
    "tell", "say", "recite", "generate", "create", "make", "banao", "bana",
    "give", "do", "dena", "de", "please", "pls", "plz", "ek", "one", "some",
    "in", "hinglish", "hindi", "english", "mein", "me", "par", "pe", "on",
    "about", "for", "regarding", "related", "to", "of", "and", "or",
    "nora", "jarvis", "hey", "hi", "can", "you", "could", "will", "would",
    "new", "nayi", "naya", "short", "chhoti", "choti", "small", "long", "badi",
    # trigger words themselves
    "poem", "poems", "poetry", "kavita", "kavitaa", "kavitayen",
    "shayari", "shayri", "shayeri", "कविता", "शायरी",
]


def is_poem_request(query):
    return bool(re.search(POEM_TRIGGER_PATTERN, query.lower()))


def _extract_topic(query):
    pattern = r"\b(" + "|".join(re.escape(w) for w in _FILLER_WORDS) + r")\b"
    topic = re.sub(pattern, " ", query.lower())
    topic = re.sub(r"[^\w\s\u0900-\u097F]", " ", topic)
    return re.sub(r"\s+", " ", topic).strip()


def _length_hint(query):
    q = query.lower()
    if any(w in q for w in ["short", "chhoti", "choti", "small", "2 line", "two line"]):
        return "SHORT: exactly 4 lines (one stanza)."
    if any(w in q for w in ["long", "badi", "lambi", "lamba"]):
        return "LONG: 5 stanzas of 4 lines each."
    return "MEDIUM: 3 stanzas of 4 lines each."


def _style_hint(query):
    q = query.lower()
    if "shayari" in q or "shayri" in q or "shayeri" in q or "शायरी" in q:
        return "Shayari style: 2-line couplets (sher) with strong rhyme and a punchy last line."
    if any(w in q for w in ["funny", "hasya", "comedy", "mazedaar", "mazak"]):
        return "Funny, playful, light-hearted with a witty punchline."
    if any(w in q for w in ["sad", "dukh", "udaas", "judai", "breakup", "dard"]):
        return "Emotional and melancholic, but gentle."
    if any(w in q for w in ["love", "pyaar", "pyar", "ishq", "romantic", "mohabbat"]):
        return "Romantic and tender."
    if any(w in q for w in ["motivat", "inspir", "josh", "himmat", "success"]):
        return "Motivational, energetic and uplifting."
    return "Pick the mood that best suits the topic."


def _build_prompt(topic, query):
    return f"""You are a talented Indian poet who writes in HINGLISH.

Write a poem about: "{topic}"
Original request: "{query}"

Rules:
- Hinglish = Hindi written in Roman (English) letters, naturally mixed with
  common English words, the way young Indians text each other.
  Example of the feel: "Dil ki baatein kehni hain, thoda sa time chahiye".
- Length: {_length_hint(query)}
- Style: {_style_hint(query)}
- Use a clear rhyme scheme (AABB or ABAB). Keep lines short and singable.
- Stanzas are separated by one blank line.
- No markdown, no emojis, no explanations.

Return ONLY valid JSON with exactly these keys:
{{
  "title": "short Hinglish title in Roman letters",
  "hinglish": "the poem in Roman-script Hinglish, stanzas separated by a blank line",
  "devanagari": "the SAME poem, same lines, same stanza breaks, written in Devanagari script (English words transliterated to Devanagari too) so a Hindi text-to-speech voice can read it"
}}"""


def _parse_json(raw):
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise


def generate_poem(topic, query=""):
    """Returns dict with keys: title, hinglish, devanagari."""
    genai.configure(api_key=LLM_KEY)
    model = genai.GenerativeModel(
        MODEL_NAME,
        generation_config={
            "response_mime_type": "application/json",
            "temperature": 1.0,
        },
    )
    response = model.generate_content(_build_prompt(topic, query or topic))
    data = _parse_json(response.text)

    title = str(data.get("title", "")).strip()
    hinglish = str(data.get("hinglish", "")).strip()
    devanagari = str(data.get("devanagari", "")).strip() or hinglish
    if not hinglish:
        raise ValueError("Empty poem returned")
    return {"title": title, "hinglish": hinglish, "devanagari": devanagari}


def _split_stanzas(text):
    return [s.strip() for s in re.split(r"\n\s*\n", text.strip()) if s.strip()]


def recite_poem(poem):
    """Show Hinglish on screen, speak the Devanagari version stanza by stanza."""
    if poem["title"]:
        speak(poem["title"], voice=HINDI_VOICE)

    eng_stanzas = _split_stanzas(poem["hinglish"])
    dev_stanzas = _split_stanzas(poem["devanagari"])

    if len(eng_stanzas) != len(dev_stanzas):
        # Stanza counts don't line up; speak everything as one block.
        speak(
            poem["devanagari"].replace("\n", ", "),
            use_cache=False,
            voice=HINDI_VOICE,
            display_text=poem["hinglish"],
        )
        return

    for eng, dev in zip(eng_stanzas, dev_stanzas):
        if cmd._interrupted:
            break
        speak(
            dev.replace("\n", ", "),
            use_cache=False,
            voice=HINDI_VOICE,
            display_text=eng,
        )


def handlePoemCommand(query):
    topic = _extract_topic(query)

    if not topic:
        speak("Kis topic par kavita sunau? Jaise baarish, dosti, ya maa.")
        topic = (takecommand() or "").strip()
        if not topic:
            speak("Koi baat nahi, jab man ho tab bata dena.")
            return False
        topic = _extract_topic(topic) or topic

    speak(f"{topic} par kavita likh raha hoon, ek second.")

    try:
        poem = generate_poem(topic, query)
        print(f"[Poem] {poem['title']}\n{poem['hinglish']}")
        recite_poem(poem)
        speak("Kaisi lagi? Aur sunani ho to bolo, ya koi naya topic bata do.")
        return True
    except Exception as e:
        print(f"[Poem] Error: {e}")
        speak("Sorry, abhi kavita nahi ban paayi. Ek baar phir try karo.")
        return False