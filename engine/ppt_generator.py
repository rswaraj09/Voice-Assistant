import os
import re
import json
import subprocess
import time
import threading

PPT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "generated_ppts")
os.makedirs(PPT_DIR, exist_ok=True)

SCRIPT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "cache", "ppt_scripts")
os.makedirs(SCRIPT_DIR, exist_ok=True)


def handlePPTGeneration(query):
    from engine.command import speak, takecommand
    from engine.config import LLM_KEY
    import google.generativeai as genai

    # Extract topic
    topic = _extract_topic(query)
    speak(f"Sure! Let me create a presentation on {topic}.")

    genai.configure(api_key=LLM_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")

    # ── Step 1: Generate outline ──────────────────────────────────────────
    speak("Generating the outline. One moment.")
    outline = _generate_outline(model, topic)

    if not outline:
        speak("Sorry, I couldn't generate an outline. Please try again.")
        return

    # Read outline aloud
    speak("Here is the outline I have planned:")
    for slide in outline[:5]:  # read first 5 slides aloud to keep it brief
        speak(f"Slide {slide['slide']}: {slide['title']}")
    if len(outline) > 5:
        speak(f"And {len(outline) - 5} more slides.")

    # ── Step 2: Ask for changes ───────────────────────────────────────────
    speak("Would you like any changes to this outline? Say yes with your changes or no to proceed.")
    response = takecommand()

    if response and any(w in response.lower() for w in ["yes", "yeah", "change", "modify", "add", "remove", "update"]):
        speak("Got it. Updating the outline.")
        outline = _apply_changes(model, topic, outline, response)
        speak("Outline updated. Starting generation.")
    else:
        speak("Great. Starting generation now.")

    # ── Step 3: Ask where to save ─────────────────────────────────────────
    speak("Where would you like to save the presentation?")
    save_response = takecommand()
    save_dir = _parse_save_path(save_response)

    # ── Step 4: Generate full slide content ───────────────────────────────
    speak("Generating all slide content. This will take a moment.")
    slides_data = _generate_slides_content(model, topic, outline)

    if not slides_data:
        speak("Sorry, content generation failed. Please try again.")
        return

    # ── Step 5: Generate the PPTX file ───────────────────────────────────
    speak("Building the presentation with professional design.")
    safe_name = re.sub(r'[^a-z0-9_]', '_', topic.lower())[:40]
    filename   = f"{safe_name}.pptx"
    output_path = os.path.join(save_dir, filename)
    os.makedirs(save_dir, exist_ok=True)

    success = _build_pptx(slides_data, topic, output_path)

    if not success:
        speak("Sorry, I had trouble building the presentation.")
        return

    speak(f"Presentation created with {len(slides_data)} slides. Saved to {save_dir}.")

    # ── Step 6: Ask to present ────────────────────────────────────────────
    speak("Would you like me to open and present it now?")
    present_response = takecommand()

    if present_response and any(w in present_response.lower() for w in
                                ["yes", "yeah", "sure", "okay", "ok", "present", "open", "show", "start"]):
        speak("Opening the presentation in PowerPoint.")
        _present_ppt(output_path)
    else:
        speak(f"Your presentation is ready at {output_path}.")


# ════════════════════════════════════════════════════════════════════════════
#  GENERATE OUTLINE
# ════════════════════════════════════════════════════════════════════════════
def _generate_outline(model, topic):
    prompt = f"""Create a professional presentation outline on "{topic}".

Return ONLY valid JSON array, no markdown, no explanation:
[
  {{"slide": 1, "title": "Title Slide", "type": "title", "key_points": ["{topic}", "subtitle here"]}},
  {{"slide": 2, "title": "Introduction", "type": "content", "key_points": ["point 1", "point 2", "point 3"]}},
  {{"slide": 3, "title": "Section Title", "type": "section", "key_points": ["overview of section"]}},
  ...
]

Slide types: "title" (first slide), "section" (divider), "content" (main), "two_column" (comparison), "stats" (numbers/data), "timeline" (steps/history), "conclusion" (last slide)

Create 10-12 slides covering the topic thoroughly. Include variety of slide types.
Make titles concise and impactful. Key points should be short phrases, not sentences."""

    try:
        resp = model.generate_content(prompt)
        raw  = resp.text.strip()
        raw  = re.sub(r'^```json\s*', '', raw)
        raw  = re.sub(r'^```\s*', '', raw)
        raw  = re.sub(r'```\s*$', '', raw)
        return json.loads(raw.strip())
    except Exception as e:
        print(f"[PPT] Outline error: {e}")
        return None


# ════════════════════════════════════════════════════════════════════════════
#  APPLY CHANGES TO OUTLINE
# ════════════════════════════════════════════════════════════════════════════
def _apply_changes(model, topic, outline, changes):
    prompt = f"""Update this presentation outline on "{topic}" based on these changes: "{changes}"

Current outline:
{json.dumps(outline, indent=2)}

Return ONLY the updated JSON array, no markdown, no explanation."""

    try:
        resp = model.generate_content(prompt)
        raw  = resp.text.strip()
        raw  = re.sub(r'^```json\s*', '', raw)
        raw  = re.sub(r'```\s*$', '', raw)
        return json.loads(raw.strip())
    except:
        return outline  # Return original if update fails


# ════════════════════════════════════════════════════════════════════════════
#  GENERATE FULL SLIDE CONTENT
# ════════════════════════════════════════════════════════════════════════════
def _generate_slides_content(model, topic, outline):
    prompt = f"""Generate complete slide content for a professional presentation on "{topic}".

Outline:
{json.dumps(outline, indent=2)}

Return ONLY valid JSON array with rich content for each slide:
[
  {{
    "slide": 1,
    "type": "title",
    "title": "Blockchain Technology",
    "subtitle": "The Future of Decentralized Systems",
    "presenter": "Presented by Nora AI"
  }},
  {{
    "slide": 2,
    "type": "content",
    "title": "What is Blockchain?",
    "bullets": [
      "A distributed, decentralized ledger technology",
      "Records transactions across multiple computers",
      "Ensures transparency and immutability",
      "Eliminates the need for central authority"
    ],
    "stat": {{"number": "100M+", "label": "blockchain wallets worldwide"}}
  }},
  {{
    "slide": 3,
    "type": "two_column",
    "title": "Centralized vs Decentralized",
    "left_heading": "Centralized",
    "left_points": ["Single point of control", "Faster decisions", "Higher risk of failure"],
    "right_heading": "Decentralized",
    "right_points": ["Distributed control", "Consensus-based", "Fault tolerant"]
  }},
  {{
    "slide": 4,
    "type": "stats",
    "title": "Blockchain by the Numbers",
    "stats": [
      {{"number": "$1.5T", "label": "Market Cap"}},
      {{"number": "300M+", "label": "Users Worldwide"}},
      {{"number": "10,000+", "label": "Blockchain Projects"}},
      {{"number": "40%", "label": "Annual Growth Rate"}}
    ]
  }},
  {{
    "slide": 5,
    "type": "timeline",
    "title": "Evolution of Blockchain",
    "steps": [
      {{"year": "2008", "event": "Bitcoin whitepaper published by Satoshi Nakamoto"}},
      {{"year": "2009", "event": "Bitcoin network launches"}},
      {{"year": "2015", "event": "Ethereum introduces smart contracts"}},
      {{"year": "2020", "event": "DeFi ecosystem explodes"}}
    ]
  }},
  {{
    "slide": 6,
    "type": "section",
    "title": "Use Cases",
    "subtitle": "Real-world applications across industries"
  }},
  {{
    "slide": 7,
    "type": "conclusion",
    "title": "Key Takeaways",
    "bullets": [
      "Blockchain enables trustless, transparent transactions",
      "Smart contracts automate complex processes",
      "The technology is still evolving rapidly",
      "Adoption is accelerating across all industries"
    ],
    "call_to_action": "The future is decentralized"
  }}
]

Generate complete, accurate, informative content for ALL {len(outline)} slides.
Return ONLY the JSON array."""

    try:
        resp = model.generate_content(prompt)
        raw  = resp.text.strip()
        raw  = re.sub(r'^```json\s*', '', raw)
        raw  = re.sub(r'```\s*$', '', raw)
        return json.loads(raw.strip())
    except Exception as e:
        print(f"[PPT] Content error: {e}")
        return None


# ════════════════════════════════════════════════════════════════════════════
#  BUILD PPTX USING NODE.JS + PPTXGENJS
# ════════════════════════════════════════════════════════════════════════════
def _build_pptx(slides_data, topic, output_path):
    # Write slides data to temp JSON
    data_file   = os.path.join(SCRIPT_DIR, "slides_data.json")
    script_file = os.path.join(SCRIPT_DIR, "generate_ppt.js")

    with open(data_file, 'w', encoding='utf-8') as f:
        json.dump({"topic": topic, "slides": slides_data, "output": output_path}, f)

    # Write the pptxgenjs generation script
    js_script = _get_pptxgenjs_script()
    with open(script_file, 'w', encoding='utf-8') as f:
        f.write(js_script)

    # Run the Node.js script
    try:
        result = subprocess.run(
            f'node "{script_file}" "{data_file}"',
            shell=True, capture_output=True, text=True, timeout=60,
            cwd=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
        )
        if result.returncode == 0:
            print(f"[PPT] Generated: {output_path}")
            return os.path.exists(output_path)
        else:
            print(f"[PPT] Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"[PPT] Build error: {e}")
        return False


# ════════════════════════════════════════════════════════════════════════════
#  PPTXGENJS SCRIPT — professional design with animations
# ════════════════════════════════════════════════════════════════════════════
def _get_pptxgenjs_script():
    return r"""
const pptxgen = require("pptxgenjs");
const fs      = require("fs");
const path    = require("path");

const dataFile = process.argv[2];
const { topic, slides, output } = JSON.parse(fs.readFileSync(dataFile, "utf8"));

// ── PALETTE — Midnight Executive ─────────────────────────────────────────
const C = {
  navy:      "1E2761",
  iceBlue:   "7EC8E3",
  white:     "FFFFFF",
  offWhite:  "F0F4FF",
  accent:    "00C9B1",   // teal accent
  dark:      "0D1B4B",
  gray:      "64748B",
  lightGray: "CBD5E1",
  textDark:  "1E293B",
  gold:      "F59E0B",
};

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.title  = topic;

// ── HELPERS ───────────────────────────────────────────────────────────────
const makeShadow = () => ({
  type: "outer", blur: 8, offset: 3, angle: 135,
  color: "000000", opacity: 0.18
});

function addDarkBg(slide) {
  slide.background = { color: C.navy };
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 4.8, w: 10, h: 0.825,
    fill: { color: C.dark }, line: { color: C.dark }
  });
  // accent line at bottom
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 5.3, w: 10, h: 0.08,
    fill: { color: C.accent }, line: { color: C.accent }
  });
}

function addLightBg(slide) {
  slide.background = { color: C.offWhite };
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.12, h: 5.625,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.12, y: 0, w: 0.06, h: 5.625,
    fill: { color: C.accent }, line: { color: C.accent }
  });
}

function addSlideNumber(slide, num, total) {
  slide.addText(`${num} / ${total}`, {
    x: 8.8, y: 5.25, w: 1, h: 0.3,
    fontSize: 9, color: C.lightGray,
    align: "right", fontFace: "Calibri"
  });
}

function addTopicLabel(slide) {
  slide.addText(topic.toUpperCase(), {
    x: 0.35, y: 5.28, w: 8, h: 0.25,
    fontSize: 8, color: C.lightGray,
    fontFace: "Calibri", charSpacing: 2
  });
}

// ── SLIDE RENDERERS ───────────────────────────────────────────────────────

function renderTitle(pres, data, num, total) {
  const slide = pres.addSlide();
  addDarkBg(slide);

  // Large accent circle
  slide.addShape(pres.shapes.OVAL, {
    x: 7.2, y: -0.8, w: 4, h: 4,
    fill: { color: C.accent, transparency: 85 },
    line: { color: C.accent, transparency: 85 }
  });
  slide.addShape(pres.shapes.OVAL, {
    x: 7.8, y: -0.3, w: 2.5, h: 2.5,
    fill: { color: C.iceBlue, transparency: 90 },
    line: { color: C.iceBlue, transparency: 90 }
  });

  // Title
  slide.addText(data.title || topic, {
    x: 0.6, y: 1.2, w: 8, h: 1.4,
    fontSize: 42, bold: true, color: C.white,
    fontFace: "Calibri", align: "left",
    shadow: makeShadow()
  });

  // Accent line under title
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.6, y: 2.75, w: 2.5, h: 0.06,
    fill: { color: C.accent }, line: { color: C.accent }
  });

  // Subtitle
  if (data.subtitle) {
    slide.addText(data.subtitle, {
      x: 0.6, y: 2.95, w: 7.5, h: 0.6,
      fontSize: 18, color: C.iceBlue,
      fontFace: "Calibri", align: "left"
    });
  }

  if (data.presenter) {
    slide.addText(data.presenter, {
      x: 0.6, y: 4.9, w: 6, h: 0.3,
      fontSize: 11, color: C.lightGray,
      fontFace: "Calibri", align: "left"
    });
  }
}

function renderSection(pres, data, num, total) {
  const slide = pres.addSlide();
  slide.background = { color: C.accent };

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 2.5,
    fill: { color: C.dark }, line: { color: C.dark }
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 2.5, w: 10, h: 0.08,
    fill: { color: C.white }, line: { color: C.white }
  });

  slide.addText(data.title, {
    x: 0.7, y: 0.7, w: 8.5, h: 1.6,
    fontSize: 38, bold: true, color: C.white,
    fontFace: "Calibri", align: "left"
  });

  if (data.subtitle) {
    slide.addText(data.subtitle, {
      x: 0.7, y: 3.0, w: 8.5, h: 0.8,
      fontSize: 20, color: C.dark,
      fontFace: "Calibri", align: "left", bold: true
    });
  }

  addSlideNumber(slide, num, total);
}

function renderContent(pres, data, num, total) {
  const slide = pres.addSlide();
  addLightBg(slide);

  // Title bar
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.25, y: 0.18, w: 9.5, h: 0.9,
    fill: { color: C.navy }, line: { color: C.navy },
    shadow: makeShadow()
  });
  slide.addText(data.title, {
    x: 0.4, y: 0.22, w: 9, h: 0.8,
    fontSize: 24, bold: true, color: C.white,
    fontFace: "Calibri", align: "left", valign: "middle", margin: 0
  });

  // Bullets
  const bullets = data.bullets || data.key_points || [];
  if (bullets.length > 0) {
    const bulletItems = bullets.map((b, i) => ({
      text: b,
      options: { bullet: true, breakLine: i < bullets.length - 1, color: C.textDark, fontSize: 16, fontFace: "Calibri" }
    }));
    slide.addText(bulletItems, {
      x: 0.5, y: 1.3, w: data.stat ? 6.5 : 9,
      h: 3.8, valign: "top", paraSpaceAfter: 6
    });
  }

  // Optional stat callout
  if (data.stat) {
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 7.3, y: 1.3, w: 2.4, h: 1.8,
      fill: { color: C.navy }, line: { color: C.navy },
      shadow: makeShadow()
    });
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 7.3, y: 1.3, w: 2.4, h: 0.08,
      fill: { color: C.accent }, line: { color: C.accent }
    });
    slide.addText(data.stat.number, {
      x: 7.3, y: 1.5, w: 2.4, h: 0.8,
      fontSize: 28, bold: true, color: C.accent,
      align: "center", fontFace: "Calibri", margin: 0
    });
    slide.addText(data.stat.label, {
      x: 7.3, y: 2.3, w: 2.4, h: 0.6,
      fontSize: 11, color: C.lightGray,
      align: "center", fontFace: "Calibri", margin: 0
    });
  }

  addSlideNumber(slide, num, total);
  addTopicLabel(slide);
}

function renderTwoColumn(pres, data, num, total) {
  const slide = pres.addSlide();
  addLightBg(slide);

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.25, y: 0.18, w: 9.5, h: 0.9,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText(data.title, {
    x: 0.4, y: 0.22, w: 9, h: 0.8,
    fontSize: 24, bold: true, color: C.white,
    fontFace: "Calibri", align: "left", valign: "middle", margin: 0
  });

  const colW = 4.2, gap = 0.4, startX = 0.4, startY = 1.25;

  // Left column
  slide.addShape(pres.shapes.RECTANGLE, {
    x: startX, y: startY, w: colW, h: 3.7,
    fill: { color: C.white }, line: { color: C.lightGray },
    shadow: makeShadow()
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: startX, y: startY, w: colW, h: 0.55,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText(data.left_heading || "Option A", {
    x: startX + 0.15, y: startY + 0.05, w: colW - 0.3, h: 0.45,
    fontSize: 14, bold: true, color: C.white,
    fontFace: "Calibri", valign: "middle", margin: 0
  });
  const leftItems = (data.left_points || []).map((b, i) => ({
    text: b,
    options: { bullet: true, breakLine: i < (data.left_points.length - 1), color: C.textDark, fontSize: 14, fontFace: "Calibri" }
  }));
  slide.addText(leftItems, {
    x: startX + 0.15, y: startY + 0.65, w: colW - 0.3, h: 2.9, valign: "top", paraSpaceAfter: 5
  });

  // Right column
  const rx = startX + colW + gap;
  slide.addShape(pres.shapes.RECTANGLE, {
    x: rx, y: startY, w: colW, h: 3.7,
    fill: { color: C.white }, line: { color: C.lightGray },
    shadow: makeShadow()
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: rx, y: startY, w: colW, h: 0.55,
    fill: { color: C.accent }, line: { color: C.accent }
  });
  slide.addText(data.right_heading || "Option B", {
    x: rx + 0.15, y: startY + 0.05, w: colW - 0.3, h: 0.45,
    fontSize: 14, bold: true, color: C.white,
    fontFace: "Calibri", valign: "middle", margin: 0
  });
  const rightItems = (data.right_points || []).map((b, i) => ({
    text: b,
    options: { bullet: true, breakLine: i < (data.right_points.length - 1), color: C.textDark, fontSize: 14, fontFace: "Calibri" }
  }));
  slide.addText(rightItems, {
    x: rx + 0.15, y: startY + 0.65, w: colW - 0.3, h: 2.9, valign: "top", paraSpaceAfter: 5
  });

  addSlideNumber(slide, num, total);
  addTopicLabel(slide);
}

function renderStats(pres, data, num, total) {
  const slide = pres.addSlide();
  addDarkBg(slide);

  slide.addText(data.title, {
    x: 0.5, y: 0.2, w: 9, h: 0.8,
    fontSize: 28, bold: true, color: C.white,
    fontFace: "Calibri", align: "left"
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: 1.05, w: 2, h: 0.06,
    fill: { color: C.accent }, line: { color: C.accent }
  });

  const stats = data.stats || [];
  const cols = Math.min(stats.length, 4);
  const cardW = 9.0 / cols - 0.2;
  const startX = 0.5;

  stats.slice(0, 4).forEach((s, i) => {
    const cx = startX + i * (cardW + 0.2);
    slide.addShape(pres.shapes.RECTANGLE, {
      x: cx, y: 1.3, w: cardW, h: 2.8,
      fill: { color: C.dark }, line: { color: C.iceBlue, width: 1 },
      shadow: makeShadow()
    });
    slide.addShape(pres.shapes.RECTANGLE, {
      x: cx, y: 1.3, w: cardW, h: 0.08,
      fill: { color: C.accent }, line: { color: C.accent }
    });
    slide.addText(s.number, {
      x: cx + 0.1, y: 1.7, w: cardW - 0.2, h: 1.0,
      fontSize: 34, bold: true, color: C.accent,
      align: "center", fontFace: "Calibri", margin: 0
    });
    slide.addText(s.label, {
      x: cx + 0.1, y: 2.8, w: cardW - 0.2, h: 0.7,
      fontSize: 12, color: C.lightGray,
      align: "center", fontFace: "Calibri", margin: 0
    });
  });

  addSlideNumber(slide, num, total);
}

function renderTimeline(pres, data, num, total) {
  const slide = pres.addSlide();
  addLightBg(slide);

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.25, y: 0.18, w: 9.5, h: 0.9,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addText(data.title, {
    x: 0.4, y: 0.22, w: 9, h: 0.8,
    fontSize: 24, bold: true, color: C.white,
    fontFace: "Calibri", align: "left", valign: "middle", margin: 0
  });

  const steps = data.steps || [];
  const stepH = Math.min(3.8 / steps.length, 0.85);
  const lineX  = 1.8;
  const startY = 1.3;

  // Vertical timeline line
  slide.addShape(pres.shapes.LINE, {
    x: lineX, y: startY + 0.2,
    w: 0, h: steps.length * stepH - 0.1,
    line: { color: C.accent, width: 2 }
  });

  steps.forEach((s, i) => {
    const cy = startY + i * stepH;

    // Circle on line
    slide.addShape(pres.shapes.OVAL, {
      x: lineX - 0.15, y: cy + 0.05, w: 0.3, h: 0.3,
      fill: { color: C.accent }, line: { color: C.accent }
    });

    // Year badge
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0.3, y: cy, w: 1.3, h: 0.38,
      fill: { color: C.navy }, line: { color: C.navy }
    });
    slide.addText(s.year || `Step ${i+1}`, {
      x: 0.3, y: cy, w: 1.3, h: 0.38,
      fontSize: 13, bold: true, color: C.white,
      align: "center", fontFace: "Calibri", valign: "middle", margin: 0
    });

    // Event text
    slide.addText(s.event || s.title || "", {
      x: lineX + 0.3, y: cy, w: 7.5, h: 0.38,
      fontSize: 13, color: C.textDark,
      fontFace: "Calibri", valign: "middle"
    });
  });

  addSlideNumber(slide, num, total);
  addTopicLabel(slide);
}

function renderConclusion(pres, data, num, total) {
  const slide = pres.addSlide();
  addDarkBg(slide);

  // Background shape
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 3.5, h: 5.625,
    fill: { color: C.dark }, line: { color: C.dark }
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 3.5, y: 0, w: 0.1, h: 5.625,
    fill: { color: C.accent }, line: { color: C.accent }
  });

  // Left side label
  slide.addText("KEY\nTAKEAWAYS", {
    x: 0.3, y: 1.5, w: 2.8, h: 2,
    fontSize: 28, bold: true, color: C.accent,
    align: "center", fontFace: "Calibri",
    charSpacing: 3
  });

  // Right side title
  slide.addText(data.title || "Conclusion", {
    x: 3.8, y: 0.3, w: 5.8, h: 0.8,
    fontSize: 26, bold: true, color: C.white,
    fontFace: "Calibri"
  });

  // Bullets
  const bullets = data.bullets || [];
  const bulletItems = bullets.map((b, i) => ({
    text: b,
    options: { bullet: true, breakLine: i < bullets.length - 1, color: C.white, fontSize: 14, fontFace: "Calibri" }
  }));
  slide.addText(bulletItems, {
    x: 3.8, y: 1.2, w: 5.8, h: 3.2, valign: "top", paraSpaceAfter: 8
  });

  // Call to action
  if (data.call_to_action) {
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 3.8, y: 4.6, w: 5.8, h: 0.5,
      fill: { color: C.accent }, line: { color: C.accent }
    });
    slide.addText(data.call_to_action, {
      x: 3.8, y: 4.6, w: 5.8, h: 0.5,
      fontSize: 13, bold: true, color: C.dark,
      align: "center", fontFace: "Calibri", valign: "middle", margin: 0
    });
  }
}

// ── MAIN RENDER ───────────────────────────────────────────────────────────
const total = slides.length;

slides.forEach((slide, idx) => {
  const num = idx + 1;
  switch (slide.type) {
    case "title":      renderTitle(pres, slide, num, total);     break;
    case "section":    renderSection(pres, slide, num, total);   break;
    case "two_column": renderTwoColumn(pres, slide, num, total); break;
    case "stats":      renderStats(pres, slide, num, total);     break;
    case "timeline":   renderTimeline(pres, slide, num, total);  break;
    case "conclusion": renderConclusion(pres, slide, num, total);break;
    default:           renderContent(pres, slide, num, total);   break;
  }
});

pres.writeFile({ fileName: output })
  .then(() => { console.log("OK:" + output); process.exit(0); })
  .catch(e => { console.error("ERR:" + e.message); process.exit(1); });
"""


# ════════════════════════════════════════════════════════════════════════════
#  OPEN IN POWERPOINT + PRESENT
# ════════════════════════════════════════════════════════════════════════════
def _present_ppt(pptx_path):
    pptx_path = os.path.abspath(pptx_path)
    try:
        # Try to open in presentation mode via PowerPoint COM
        ps_cmd = f'''
Add-Type -AssemblyName Microsoft.Office.Interop.PowerPoint
$app = New-Object -ComObject PowerPoint.Application
$app.Visible = [Microsoft.Office.Core.MsoTriState]::msoTrue
$pres = $app.Presentations.Open("{pptx_path}")
$pres.SlideShowSettings.Run()
'''
        result = subprocess.run(
            ['powershell', '-Command', ps_cmd],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            print("[PPT] Presenting via PowerPoint COM")
            return

        # Fallback: just open the file
        os.startfile(pptx_path)
        print("[PPT] Opened via startfile")

    except Exception as e:
        print(f"[PPT] Present error: {e}")
        try:
            os.startfile(pptx_path)
        except:
            subprocess.Popen(f'start "" "{pptx_path}"', shell=True)


# ════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════════════════════
def _extract_topic(query):
    patterns = [
        r'(?:create|make|build|generate|prepare)\s+(?:a\s+)?(?:ppt|presentation|powerpoint|slides?)\s+(?:on|about|for|regarding)\s+(.+)',
        r'(?:create|make|build|generate|prepare)\s+(?:on|about)\s+(.+)\s+(?:ppt|presentation|powerpoint|slides?)',
        r'(?:ppt|presentation|powerpoint|slides?)\s+(?:on|about|for)\s+(.+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            topic = match.group(1).strip()
            topic = re.sub(r'\s+', ' ', topic)
            return topic[:80]
    # Fallback: remove ppt-related words
    topic = re.sub(r'\b(create|make|build|generate|prepare|a|ppt|presentation|powerpoint|slides?|on|about|for)\b',
                   '', query, flags=re.IGNORECASE).strip()
    return re.sub(r'\s+', ' ', topic)[:80] or query[:80]


def _parse_save_path(response):
    if not response:
        return os.path.join(os.path.expanduser("~"), "Documents", "Presentations")
    response = response.lower().strip()

    path_match = re.search(r'[a-z]:\\[\w\\]+', response, re.IGNORECASE)
    if path_match:
        return path_match.group()
    if "desktop"  in response: return os.path.join(os.path.expanduser("~"), "Desktop")
    if "document" in response: return os.path.join(os.path.expanduser("~"), "Documents", "Presentations")
    if "download" in response: return os.path.join(os.path.expanduser("~"), "Downloads")

    drive_match = re.search(r'\b([a-z])\s*(?:drive|disk)?\b', response)
    if drive_match:
        drive = drive_match.group(1).upper()
        return os.path.join(f"{drive}:\\", "Presentations")

    return os.path.join(os.path.expanduser("~"), "Documents", "Presentations")
