import os
import re
import time
import requests
import subprocess
from datetime import datetime
import google.generativeai as genai
from engine.config import LLM_KEY

#  Save location — Pictures\JarvisGallery 
GALLERY_DIR = os.path.join(os.path.expanduser("~"), "Pictures", "JarvisGallery")
os.makedirs(GALLERY_DIR, exist_ok=True)


#  EXTRACT PROMPT FROM VOICE QUERY
#  Strips trigger words and keeps the actual description

def extract_image_prompt(query: str) -> str:
    query = query.lower().strip()
    patterns = [
        r"generate\s+(?:a\s+)?(?:4k\s+)?(?:realistic\s+)?(?:hd\s+)?(?:high.res\w*\s+)?image\s+of\s+",
        r"generate\s+(?:a\s+)?(?:4k\s+)?(?:realistic\s+)?(?:hd\s+)?(?:high.res\w*\s+)?picture\s+of\s+",
        r"generate\s+(?:a\s+)?(?:4k\s+)?(?:realistic\s+)?(?:hd\s+)?photo\s+of\s+",
        r"create\s+(?:a\s+)?(?:4k\s+)?(?:realistic\s+)?(?:hd\s+)?image\s+of\s+",
        r"create\s+(?:a\s+)?(?:4k\s+)?(?:realistic\s+)?(?:hd\s+)?picture\s+of\s+",
        r"draw\s+(?:a\s+)?(?:4k\s+)?(?:realistic\s+)?",
        r"make\s+(?:a\s+)?(?:4k\s+)?(?:realistic\s+)?image\s+of\s+",
        r"show\s+(?:me\s+)?(?:a\s+)?(?:4k\s+)?(?:realistic\s+)?image\s+of\s+",
        r"generate\s+",
        r"image\s+of\s+",
        r"picture\s+of\s+",
    ]
    for pattern in patterns:
        query = re.sub(pattern, "", query, flags=re.IGNORECASE).strip()

    # Remove leading filler words
    query = re.sub(r"^(a|an|the|some)\s+", "", query).strip()
    return query



#  DETECT STYLE

def detect_style(query: str) -> str:
    query = query.lower()
    if any(w in query for w in ["animated", "anime", "cartoon", "2d", "pixar", "illustrated", "drawing"]):
        return "animated"
    elif any(w in query for w in ["realistic", "real", "4k", "hd", "photo", "cinematic", "actual"]):
        return "realistic"
    else:
        return "realistic"  # default


#  ENHANCE PROMPT — ask Gemini to make the prompt richer

def enhance_prompt(raw_prompt: str, style: str = "realistic") -> str:
    try:
        genai.configure(api_key=LLM_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash")

        if style == "animated":
            instruction = (
                f"Convert this into a detailed anime/cartoon style image generation prompt. "
                f"Add vibrant colors, clean lines, anime aesthetics, studio quality. "
                f"Keep it under 100 words. Return ONLY the prompt, no explanation.\n\nSubject: {raw_prompt}"
            )
        else:
            instruction = (
                f"Convert this into a detailed photorealistic image generation prompt. "
                f"Add lighting, atmosphere, camera details. "
                f"Keep it under 100 words. Return ONLY the prompt, no explanation.\n\nSubject: {raw_prompt}"
            )

        response = model.generate_content(instruction)
        enhanced = response.text.strip()
        print(f"[ImageGen] Style: {style} | Enhanced prompt: {enhanced}")
        return enhanced
    except Exception as e:
        print(f"[ImageGen] Prompt enhancement failed: {e}")
        if style == "animated":
            return raw_prompt + ", anime style, vibrant colors, clean lines, studio ghibli quality"
        else:
            return raw_prompt + ", 4K, photorealistic, high detail, professional photography"



#  GENERATE IMAGE — using Pollinations.ai (free, no API key needed)

def generate_image(prompt: str) -> str | None:
    """
    Uses Pollinations.ai free API — no key needed.
    Returns saved file path or None on failure.
    """
    import urllib.parse

    encoded = urllib.parse.quote(prompt)
    # width=1920&height=1080 for 4K-style widescreen, model=flux for best quality
    url = f"https://image.pollinations.ai/prompt/{encoded}?width=1920&height=1080&model=flux&nologo=true&enhance=true"

    print(f"[ImageGen] Requesting image from Pollinations...")
    print(f"[ImageGen] URL: {url}")

    try:
        response = requests.get(url, timeout=60, stream=True)
        if response.status_code == 200:
            # Verify it's actually an image
            content_type = response.headers.get("Content-Type", "")
            if "image" not in content_type:
                print(f"[ImageGen] Unexpected content type: {content_type}")
                return None

            # Save with timestamp filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = re.sub(r'[^\w\s-]', '', prompt[:40]).strip().replace(' ', '_')
            filename = f"{safe_name}_{timestamp}.jpg"
            filepath = os.path.join(GALLERY_DIR, filename)

            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            size_kb = os.path.getsize(filepath) / 1024
            print(f"[ImageGen] Saved: {filepath} ({size_kb:.1f} KB)")

            if size_kb < 5:
                print("[ImageGen] File too small — likely an error response, not an image")
                os.remove(filepath)
                return None

            return filepath
        else:
            print(f"[ImageGen] API error: {response.status_code}")
            return None

    except requests.exceptions.Timeout:
        print("[ImageGen] Request timed out (60s)")
        return None
    except Exception as e:
        print(f"[ImageGen] Request failed: {e}")
        return None



#  OPEN IMAGE — opens with default Windows photo viewer

def open_image(filepath: str):
    try:
        os.startfile(filepath)  # opens with default photo app on Windows
        print(f"[ImageGen] Opened: {filepath}")
    except Exception as e:
        print(f"[ImageGen] Could not open image: {e}")
        try:
            subprocess.Popen(["explorer", os.path.dirname(filepath)])
        except:
            pass



#  MAIN HANDLER — called from command.py

def handleImageGeneration(query: str, speak_fn):
    """
    Full pipeline:
    1. Extract subject from voice query
    2. Enhance prompt via Gemini
    3. Generate image via Pollinations
    4. Save to Pictures/JarvisGallery
    5. Open with default viewer
    """
    # Step 1 — extract
    raw_prompt = extract_image_prompt(query)
    if not raw_prompt:
        speak_fn("Please tell me what you'd like me to generate.")
        return

    # Step 2 — style detection
    style = detect_style(query)
    style_word = "animated" if style == "animated" else "realistic"
    speak_fn(f"Generating a {style_word} image of {raw_prompt}. Please wait a moment.")
    print(f"[ImageGen] Raw prompt: {raw_prompt} | Style: {style}")

    # Step 3 — enhance
    enhanced_prompt = enhance_prompt(raw_prompt, style)

    # Step 3 & 4 — generate and save
    filepath = generate_image(enhanced_prompt)

    # Step 6 — open or report failure
    if filepath:
        speak_fn(f"{style_word.capitalize()} image generated and saved. Opening it now.")
        time.sleep(0.5)
        open_image(filepath)
    else:
        speak_fn("Sorry, I couldn't generate the image right now. Please try again.")