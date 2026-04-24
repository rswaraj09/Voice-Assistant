
const pptxgen = require("pptxgenjs");
const fs      = require("fs");
const path    = require("path");

const dataFile = process.argv[2];
const { topic, slides, output, images } = JSON.parse(fs.readFileSync(dataFile, "utf8"));

// ── PALETTE — Midnight Executive ─────────────────────────────────────────
const C = {
  navy:       "1E2761",
  iceBlue:    "7EC8E3",
  white:      "FFFFFF",
  offWhite:   "F8FAFF",
  accent:     "00C9B1",
  accentWarm: "F59E0B",
  dark:       "0D1B4B",
  gray:       "64748B",
  lightGray:  "CBD5E1",
  textDark:   "1E293B",
  cardBg:     "EDF2FF",
  danger:     "EF4444",
  purple:     "7C3AED",
};

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.title  = topic;

// ── SHADOW HELPER ─────────────────────────────────────────────────────────
const shadow = (opacity = 0.18, blur = 8, offset = 3) => ({
  type: "outer", blur, offset, angle: 135,
  color: "000000", opacity
});

// ── SLIDE NUMBER ──────────────────────────────────────────────────────────
function addSlideNum(slide, num, total, dark = false) {
  slide.addText(`${num} / ${total}`, {
    x: 8.9, y: 5.3, w: 0.9, h: 0.25,
    fontSize: 8, color: dark ? C.lightGray : C.gray,
    align: "right", fontFace: "Calibri"
  });
}

// ── BACKGROUND HELPERS ────────────────────────────────────────────────────
function darkBg(slide) {
  slide.background = { color: C.navy };
}

function lightBg(slide) {
  slide.background = { color: C.offWhite };
}

// ── PROGRESS BAR (bottom of every slide) ─────────────────────────────────
function addProgressBar(slide, num, total) {
  const w = (num / total) * 10;
  // track
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 5.55, w: 10, h: 0.075,
    fill: { color: "1A2550" }, line: { color: "1A2550" }
  });
  // fill
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 5.55, w: w, h: 0.075,
    fill: { color: C.accent }, line: { color: C.accent }
  });
}

// ── IMAGE HELPER ──────────────────────────────────────────────────────────
function addImage(slide, slideNum, x, y, w, h, opts = {}) {
  const imgPath = images[String(slideNum)];
  if (imgPath && fs.existsSync(imgPath)) {
    slide.addImage({ path: imgPath, x, y, w, h, ...opts });
    return true;
  }
  // Fallback: gradient placeholder rectangle
  slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w, h,
    fill: { color: C.dark },
    line: { color: C.navy }
  });
  slide.addText("[ Visual ]", {
    x, y, w, h,
    fontSize: 14, color: C.lightGray,
    align: "center", valign: "middle", fontFace: "Calibri"
  });
  return false;
}

// ════════════════════════════════════════════════════════════════════════════
//  SLIDE RENDERERS
// ════════════════════════════════════════════════════════════════════════════

// ── TITLE SLIDE ───────────────────────────────────────────────────────────
function renderTitle(data, num, total) {
  const slide = pres.addSlide();
  darkBg(slide);

  // Full bleed background image (right half, low opacity overlay)
  const hasImg = images[String(num)] && fs.existsSync(images[String(num)]);
  if (hasImg) {
    slide.addImage({ path: images[String(num)], x: 4.5, y: 0, w: 5.5, h: 5.625, transparency: 40 });
  }

  // Dark gradient overlay on right side
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 4.5, y: 0, w: 5.5, h: 5.625,
    fill: { type: "solid", color: C.navy, transparency: hasImg ? 20 : 100 },
    line: { color: C.navy, transparency: 100 }
  });

  // Left accent bar
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.18, h: 5.625,
    fill: { color: C.accent }, line: { color: C.accent }
  });

  // Large decorative circle
  slide.addShape(pres.shapes.OVAL, {
    x: -0.8, y: 3.5, w: 3.5, h: 3.5,
    fill: { color: C.accent, transparency: 88 },
    line: { color: C.accent, transparency: 88 }
  });

  // Main title
  slide.addText(data.title || topic, {
    x: 0.55, y: 1.0, w: 6.5, h: 1.8,
    fontSize: 44, bold: true, color: C.white,
    fontFace: "Calibri", align: "left",
    shadow: shadow(0.3, 12, 4)
  });

  // Horizontal rule
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0.55, y: 2.9, w: 3.0, h: 0.05,
    fill: { color: C.accent }, line: { color: C.accent }
  });

  // Subtitle
  if (data.subtitle) {
    slide.addText(data.subtitle, {
      x: 0.55, y: 3.05, w: 6.5, h: 0.7,
      fontSize: 18, color: C.iceBlue,
      fontFace: "Calibri", align: "left"
    });
  }

  // Tagline pill
  if (data.tagline) {
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 0.55, y: 3.9, w: Math.min(data.tagline.length * 0.12 + 0.6, 5), h: 0.42,
      fill: { color: C.accent, transparency: 20 },
      line: { color: C.accent },
      rectRadius: 0.1
    });
    slide.addText(data.tagline, {
      x: 0.65, y: 3.9, w: 4.8, h: 0.42,
      fontSize: 12, color: C.white, bold: true,
      fontFace: "Calibri", valign: "middle"
    });
  }

  // Presenter
  if (data.presenter) {
    slide.addText(data.presenter, {
      x: 0.55, y: 5.15, w: 5, h: 0.25,
      fontSize: 10, color: C.lightGray,
      fontFace: "Calibri"
    });
  }

  addProgressBar(slide, num, total);
}

// ── SECTION DIVIDER ───────────────────────────────────────────────────────
function renderSection(data, num, total) {
  const slide = pres.addSlide();

  // Background image with heavy overlay
  const hasImg = images[String(num)] && fs.existsSync(images[String(num)]);
  if (hasImg) {
    slide.addImage({ path: images[String(num)], x: 0, y: 0, w: 10, h: 5.625, transparency: 20 });
  }

  // Full overlay
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 5.625,
    fill: { color: C.dark, transparency: hasImg ? 25 : 0 },
    line: { color: C.dark }
  });

  // Big section number
  slide.addText(`0${num}`, {
    x: 7.0, y: 0.3, w: 2.5, h: 2,
    fontSize: 100, bold: true, color: C.accent,
    fontFace: "Calibri", align: "right",
    transparency: 80
  });

  // Section label
  slide.addText("SECTION", {
    x: 0.6, y: 1.4, w: 5, h: 0.35,
    fontSize: 11, color: C.accent, bold: true,
    fontFace: "Calibri", charSpacing: 6
  });

  // Title
  slide.addText(data.title, {
    x: 0.6, y: 1.8, w: 8.5, h: 1.6,
    fontSize: 40, bold: true, color: C.white,
    fontFace: "Calibri", align: "left",
    shadow: shadow(0.4, 10, 3)
  });

  // Subtitle
  if (data.subtitle) {
    slide.addText(data.subtitle, {
      x: 0.6, y: 3.5, w: 7, h: 0.6,
      fontSize: 18, color: C.iceBlue,
      fontFace: "Calibri", align: "left"
    });
  }

  addProgressBar(slide, num, total);
  addSlideNum(slide, num, total, true);
}

// ── CONTENT SLIDE (with optional image sidebar) ───────────────────────────
function renderContent(data, num, total) {
  const slide = pres.addSlide();
  lightBg(slide);

  const hasImg = images[String(num)] && fs.existsSync(images[String(num)]);
  const contentW = hasImg ? 5.8 : 9.0;

  // Title band
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 1.05,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  // Accent stripe
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 1.05, w: 10, h: 0.05,
    fill: { color: C.accent }, line: { color: C.accent }
  });
  slide.addText(data.title, {
    x: 0.35, y: 0.08, w: 9.3, h: 0.88,
    fontSize: 26, bold: true, color: C.white,
    fontFace: "Calibri", valign: "middle"
  });

  // Image sidebar
  if (hasImg) {
    slide.addImage({ path: images[String(num)], x: 6.2, y: 1.15, w: 3.6, h: 3.5 });
    // Overlay label
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 6.2, y: 4.3, w: 3.6, h: 0.35,
      fill: { color: C.dark, transparency: 20 }, line: { color: C.dark }
    });
    slide.addText(topic.toUpperCase(), {
      x: 6.25, y: 4.3, w: 3.5, h: 0.35,
      fontSize: 8, color: C.lightGray, charSpacing: 2,
      fontFace: "Calibri", valign: "middle"
    });
  }

  // Bullets as styled rows
  const bullets = data.bullets || data.key_points || [];
  bullets.slice(0, 6).forEach((b, i) => {
    const y = 1.25 + i * 0.6;
    // Bullet dot
    slide.addShape(pres.shapes.OVAL, {
      x: 0.3, y: y + 0.12, w: 0.18, h: 0.18,
      fill: { color: C.accent }, line: { color: C.accent }
    });
    slide.addText(b, {
      x: 0.6, y: y, w: contentW - 0.3, h: 0.5,
      fontSize: 15, color: C.textDark,
      fontFace: "Calibri", valign: "middle"
    });
    // Subtle separator
    if (i < bullets.length - 1) {
      slide.addShape(pres.shapes.LINE, {
        x: 0.6, y: y + 0.52, w: contentW - 0.3, h: 0,
        line: { color: C.lightGray, width: 0.5 }
      });
    }
  });

  // Stat callout card
  if (data.stat) {
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: hasImg ? 0.3 : 7.0, y: hasImg ? 4.35 : 1.3, w: 2.5, h: 1.0,
      fill: { color: C.navy }, line: { color: C.accent, width: 1 },
      shadow: shadow(0.25, 6, 3), rectRadius: 0.08
    });
    slide.addText(data.stat.number, {
      x: hasImg ? 0.3 : 7.0, y: hasImg ? 4.4 : 1.4, w: 2.5, h: 0.55,
      fontSize: 28, bold: true, color: C.accent,
      align: "center", fontFace: "Calibri"
    });
    slide.addText(data.stat.label, {
      x: hasImg ? 0.3 : 7.0, y: hasImg ? 4.9 : 1.95, w: 2.5, h: 0.35,
      fontSize: 10, color: C.lightGray,
      align: "center", fontFace: "Calibri"
    });
  }

  addProgressBar(slide, num, total);
  addSlideNum(slide, num, total);
}

// ── TWO COLUMN ────────────────────────────────────────────────────────────
function renderTwoColumn(data, num, total) {
  const slide = pres.addSlide();
  lightBg(slide);

  // Title
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 1.05,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 1.05, w: 10, h: 0.05,
    fill: { color: C.accent }, line: { color: C.accent }
  });
  slide.addText(data.title, {
    x: 0.35, y: 0.08, w: 9.3, h: 0.88,
    fontSize: 26, bold: true, color: C.white,
    fontFace: "Calibri", valign: "middle"
  });

  // VS divider label
  slide.addShape(pres.shapes.OVAL, {
    x: 4.6, y: 1.8, w: 0.8, h: 0.8,
    fill: { color: C.accentWarm }, line: { color: C.accentWarm },
    shadow: shadow(0.25, 6, 3)
  });
  slide.addText("VS", {
    x: 4.6, y: 1.8, w: 0.8, h: 0.8,
    fontSize: 14, bold: true, color: C.white,
    align: "center", valign: "middle", fontFace: "Calibri"
  });

  const colW = 4.3;

  // Left column
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.25, y: 1.25, w: colW, h: 3.8,
    fill: { color: C.white }, line: { color: C.lightGray },
    shadow: shadow(0.12, 5, 2), rectRadius: 0.1
  });
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: 0.25, y: 1.25, w: colW, h: 0.55,
    fill: { color: C.navy }, line: { color: C.navy }, rectRadius: 0.1
  });
  slide.addText(data.left_heading || "Option A", {
    x: 0.4, y: 1.28, w: colW - 0.3, h: 0.48,
    fontSize: 15, bold: true, color: C.white,
    fontFace: "Calibri", valign: "middle"
  });
  (data.left_points || []).forEach((pt, i) => {
    slide.addShape(pres.shapes.OVAL, {
      x: 0.42, y: 1.97 + i * 0.55 + 0.13, w: 0.14, h: 0.14,
      fill: { color: C.navy }, line: { color: C.navy }
    });
    slide.addText(pt, {
      x: 0.65, y: 1.95 + i * 0.55, w: colW - 0.8, h: 0.48,
      fontSize: 13, color: C.textDark,
      fontFace: "Calibri", valign: "middle"
    });
  });

  // Right column
  const rx = 10 - 0.25 - colW;
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: rx, y: 1.25, w: colW, h: 3.8,
    fill: { color: C.white }, line: { color: C.lightGray },
    shadow: shadow(0.12, 5, 2), rectRadius: 0.1
  });
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x: rx, y: 1.25, w: colW, h: 0.55,
    fill: { color: C.accent }, line: { color: C.accent }, rectRadius: 0.1
  });
  slide.addText(data.right_heading || "Option B", {
    x: rx + 0.15, y: 1.28, w: colW - 0.3, h: 0.48,
    fontSize: 15, bold: true, color: C.white,
    fontFace: "Calibri", valign: "middle"
  });
  (data.right_points || []).forEach((pt, i) => {
    slide.addShape(pres.shapes.OVAL, {
      x: rx + 0.17, y: 1.97 + i * 0.55 + 0.13, w: 0.14, h: 0.14,
      fill: { color: C.accent }, line: { color: C.accent }
    });
    slide.addText(pt, {
      x: rx + 0.4, y: 1.95 + i * 0.55, w: colW - 0.8, h: 0.48,
      fontSize: 13, color: C.textDark,
      fontFace: "Calibri", valign: "middle"
    });
  });

  addProgressBar(slide, num, total);
  addSlideNum(slide, num, total);
}

// ── STATS / INFOGRAPHIC ───────────────────────────────────────────────────
function renderStats(data, num, total) {
  const slide = pres.addSlide();
  darkBg(slide);

  // Background image at low opacity
  if (images[String(num)] && fs.existsSync(images[String(num)])) {
    slide.addImage({ path: images[String(num)], x: 0, y: 0, w: 10, h: 5.625, transparency: 75 });
  }

  slide.addText(data.title, {
    x: 0.5, y: 0.2, w: 9, h: 0.75,
    fontSize: 28, bold: true, color: C.white,
    fontFace: "Calibri"
  });

  const stats = (data.stats || []).slice(0, 4);
  const cols = stats.length;
  const cardW = (9.0 / cols) - 0.25;
  const startX = 0.35;

  stats.forEach((s, i) => {
    const cx = startX + i * (cardW + 0.25);
    const cy = 1.15;

    // Card background
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: cx, y: cy, w: cardW, h: 3.2,
      fill: { color: C.dark, transparency: 10 },
      line: { color: C.accent, width: 1 },
      shadow: shadow(0.3, 10, 4), rectRadius: 0.12
    });

    // Top accent bar
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: cx, y: cy, w: cardW, h: 0.12,
      fill: { color: i % 2 === 0 ? C.accent : C.iceBlue },
      line: { color: i % 2 === 0 ? C.accent : C.iceBlue }, rectRadius: 0.05
    });

    // Big number
    slide.addText(s.number, {
      x: cx + 0.1, y: cy + 0.4, w: cardW - 0.2, h: 1.2,
      fontSize: 38, bold: true,
      color: i % 2 === 0 ? C.accent : C.iceBlue,
      align: "center", fontFace: "Calibri",
      shadow: shadow(0.2, 6, 2)
    });

    // Label
    slide.addText(s.label, {
      x: cx + 0.1, y: cy + 1.75, w: cardW - 0.2, h: 0.9,
      fontSize: 13, color: C.lightGray,
      align: "center", fontFace: "Calibri"
    });
  });

  addProgressBar(slide, num, total);
  addSlideNum(slide, num, total, true);
}

// ── TIMELINE ──────────────────────────────────────────────────────────────
function renderTimeline(data, num, total) {
  const slide = pres.addSlide();
  lightBg(slide);

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 1.05,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 1.05, w: 10, h: 0.05,
    fill: { color: C.accentWarm }, line: { color: C.accentWarm }
  });
  slide.addText(data.title, {
    x: 0.35, y: 0.08, w: 9.3, h: 0.88,
    fontSize: 26, bold: true, color: C.white,
    fontFace: "Calibri", valign: "middle"
  });

  const steps = (data.steps || []).slice(0, 6);

  // Horizontal timeline for up to 4 steps, vertical for more
  if (steps.length <= 4) {
    // HORIZONTAL TIMELINE
    const cardW = (9.0 / steps.length) - 0.2;
    const lineY  = 2.4;

    // Horizontal line
    slide.addShape(pres.shapes.LINE, {
      x: 0.5, y: lineY + 0.2,
      w: 9, h: 0,
      line: { color: C.accentWarm, width: 2 }
    });

    steps.forEach((s, i) => {
      const cx = 0.5 + i * (cardW + 0.2);

      // Node circle
      const nodeX = cx + cardW / 2 - 0.22;
      slide.addShape(pres.shapes.OVAL, {
        x: nodeX, y: lineY + 0.2 - 0.22, w: 0.44, h: 0.44,
        fill: { color: C.accentWarm }, line: { color: C.white, width: 2 },
        shadow: shadow(0.3, 6, 2)
      });

      // Year above
      slide.addText(s.year || `${i + 1}`, {
        x: nodeX - 0.3, y: lineY - 0.5, w: 1.0, h: 0.4,
        fontSize: 14, bold: true, color: C.navy,
        align: "center", fontFace: "Calibri"
      });

      // Event card below
      slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x: cx, y: lineY + 0.55, w: cardW, h: 1.8,
        fill: { color: C.white }, line: { color: C.lightGray },
        shadow: shadow(0.1, 4, 2), rectRadius: 0.08
      });
      slide.addText(s.event || s.title || "", {
        x: cx + 0.1, y: lineY + 0.65, w: cardW - 0.2, h: 1.6,
        fontSize: 12, color: C.textDark,
        fontFace: "Calibri", valign: "top"
      });
    });

  } else {
    // VERTICAL TIMELINE (5-6 steps)
    const stepH = 3.8 / steps.length;
    const lineX  = 1.9;
    const startY = 1.25;

    slide.addShape(pres.shapes.LINE, {
      x: lineX, y: startY + 0.15,
      w: 0, h: steps.length * stepH - 0.15,
      line: { color: C.accentWarm, width: 2 }
    });

    steps.forEach((s, i) => {
      const cy = startY + i * stepH;

      slide.addShape(pres.shapes.OVAL, {
        x: lineX - 0.18, y: cy + 0.06, w: 0.36, h: 0.36,
        fill: { color: C.accentWarm }, line: { color: C.white, width: 2 },
        shadow: shadow(0.2, 4, 2)
      });

      // Year pill
      slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
        x: 0.3, y: cy, w: 1.35, h: 0.38,
        fill: { color: C.navy }, line: { color: C.navy }, rectRadius: 0.06
      });
      slide.addText(s.year || `Step ${i+1}`, {
        x: 0.3, y: cy, w: 1.35, h: 0.38,
        fontSize: 13, bold: true, color: C.white,
        align: "center", fontFace: "Calibri", valign: "middle"
      });

      slide.addText(s.event || s.title || "", {
        x: lineX + 0.3, y: cy, w: 7.5, h: 0.38,
        fontSize: 13, color: C.textDark,
        fontFace: "Calibri", valign: "middle"
      });
    });
  }

  addProgressBar(slide, num, total);
  addSlideNum(slide, num, total);
}

// ── IMAGE FOCUS ───────────────────────────────────────────────────────────
function renderImageFocus(data, num, total) {
  const slide = pres.addSlide();
  darkBg(slide);

  const hasImg = images[String(num)] && fs.existsSync(images[String(num)]);

  if (hasImg) {
    // Full bleed image
    slide.addImage({ path: images[String(num)], x: 0, y: 0, w: 10, h: 5.625 });
    // Gradient overlay (bottom)
    slide.addShape(pres.shapes.RECTANGLE, {
      x: 0, y: 2.8, w: 10, h: 2.825,
      fill: { color: C.dark, transparency: 10 }, line: { color: C.dark }
    });
  }

  // Title overlay at top
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 1.0,
    fill: { color: C.dark, transparency: hasImg ? 15 : 0 },
    line: { color: C.dark }
  });
  slide.addText(data.title, {
    x: 0.4, y: 0.1, w: 9.2, h: 0.8,
    fontSize: 26, bold: true, color: C.white,
    fontFace: "Calibri", valign: "middle"
  });

  // Highlight pill
  if (data.highlight) {
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 0.4, y: 2.85, w: Math.min(data.highlight.length * 0.16 + 0.5, 5), h: 0.48,
      fill: { color: C.accent }, line: { color: C.accent }, rectRadius: 0.08
    });
    slide.addText(data.highlight, {
      x: 0.5, y: 2.85, w: 5, h: 0.48,
      fontSize: 15, bold: true, color: C.dark,
      fontFace: "Calibri", valign: "middle"
    });
  }

  // Caption
  if (data.caption) {
    slide.addText(data.caption, {
      x: 0.4, y: 3.5, w: 9.2, h: 1.6,
      fontSize: 16, color: C.white,
      fontFace: "Calibri", valign: "top"
    });
  }

  addProgressBar(slide, num, total);
  addSlideNum(slide, num, total, true);
}

// ── ICON GRID (infographic cards) ────────────────────────────────────────
function renderIconGrid(data, num, total) {
  const slide = pres.addSlide();
  lightBg(slide);

  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 10, h: 1.05,
    fill: { color: C.navy }, line: { color: C.navy }
  });
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 1.05, w: 10, h: 0.05,
    fill: { color: C.purple }, line: { color: C.purple }
  });
  slide.addText(data.title, {
    x: 0.35, y: 0.08, w: 9.3, h: 0.88,
    fontSize: 26, bold: true, color: C.white,
    fontFace: "Calibri", valign: "middle"
  });

  const items = (data.items || []).slice(0, 6);
  const cols = items.length <= 3 ? items.length : Math.ceil(items.length / 2);
  const rows = items.length <= 3 ? 1 : 2;
  const cardW = (9.2 / cols) - 0.2;
  const cardH = rows === 1 ? 3.5 : 1.7;
  const startX = 0.4;
  const startY = 1.25;

  const accentColors = [C.accent, C.purple, C.iceBlue, C.accentWarm, C.navy, C.gray];

  items.forEach((item, i) => {
    const col = i % cols;
    const row = Math.floor(i / cols);
    const x = startX + col * (cardW + 0.2);
    const y = startY + row * (cardH + 0.2);
    const color = accentColors[i % accentColors.length];

    // Card
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y, w: cardW, h: cardH,
      fill: { color: C.white }, line: { color: C.lightGray },
      shadow: shadow(0.1, 4, 2), rectRadius: 0.1
    });

    // Colored top bar
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x, y, w: cardW, h: 0.08,
      fill: { color }, line: { color }, rectRadius: 0.04
    });

    // Icon circle
    slide.addShape(pres.shapes.OVAL, {
      x: x + cardW / 2 - 0.3, y: y + 0.15, w: 0.6, h: 0.6,
      fill: { color, transparency: 15 }, line: { color }
    });
    slide.addText(item.icon || "●", {
      x: x + cardW / 2 - 0.3, y: y + 0.15, w: 0.6, h: 0.6,
      fontSize: 20, align: "center", valign: "middle"
    });

    // Heading
    slide.addText(item.heading || "", {
      x: x + 0.1, y: y + 0.82, w: cardW - 0.2, h: 0.45,
      fontSize: 13, bold: true, color: C.textDark,
      align: "center", fontFace: "Calibri"
    });

    // Description
    if (item.text) {
      slide.addText(item.text, {
        x: x + 0.12, y: y + 1.3, w: cardW - 0.24, h: cardH - 1.4,
        fontSize: 11, color: C.gray,
        align: "center", fontFace: "Calibri", valign: "top"
      });
    }
  });

  addProgressBar(slide, num, total);
  addSlideNum(slide, num, total);
}

// ── QUOTE SLIDE ───────────────────────────────────────────────────────────
function renderQuote(data, num, total) {
  const slide = pres.addSlide();
  darkBg(slide);

  // Background image
  if (images[String(num)] && fs.existsSync(images[String(num)])) {
    slide.addImage({ path: images[String(num)], x: 0, y: 0, w: 10, h: 5.625, transparency: 70 });
  }

  // Big quotation mark graphic
  slide.addText("\u201C", {
    x: 0.3, y: -0.3, w: 3, h: 2.5,
    fontSize: 160, color: C.accent,
    fontFace: "Georgia", transparency: 40
  });

  // Quote text
  slide.addText(data.quote || "", {
    x: 1.0, y: 1.1, w: 8.0, h: 2.4,
    fontSize: 22, color: C.white, italic: true,
    fontFace: "Georgia", align: "center",
    shadow: shadow(0.3, 8, 3)
  });

  // Divider
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 4.2, y: 3.7, w: 1.6, h: 0.05,
    fill: { color: C.accent }, line: { color: C.accent }
  });

  // Author
  if (data.author) {
    slide.addText(`— ${data.author}`, {
      x: 1, y: 3.85, w: 8, h: 0.45,
      fontSize: 14, bold: true, color: C.iceBlue,
      fontFace: "Calibri", align: "center"
    });
  }

  // Context
  if (data.context) {
    slide.addText(data.context, {
      x: 1, y: 4.35, w: 8, h: 0.4,
      fontSize: 11, color: C.gray,
      fontFace: "Calibri", align: "center"
    });
  }

  addProgressBar(slide, num, total);
  addSlideNum(slide, num, total, true);
}

// ── CONCLUSION ────────────────────────────────────────────────────────────
function renderConclusion(data, num, total) {
  const slide = pres.addSlide();
  darkBg(slide);

  // Background image (right side)
  if (images[String(num)] && fs.existsSync(images[String(num)])) {
    slide.addImage({ path: images[String(num)], x: 5.5, y: 0, w: 4.5, h: 5.625, transparency: 55 });
  }

  // Left panel
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 5.5, h: 5.625,
    fill: { color: C.dark }, line: { color: C.dark }
  });
  // Accent border right of panel
  slide.addShape(pres.shapes.RECTANGLE, {
    x: 5.5, y: 0, w: 0.1, h: 5.625,
    fill: { color: C.accent }, line: { color: C.accent }
  });

  // "KEY TAKEAWAYS" label
  slide.addText("KEY TAKEAWAYS", {
    x: 0.3, y: 0.3, w: 4.8, h: 0.4,
    fontSize: 11, bold: true, color: C.accent,
    fontFace: "Calibri", charSpacing: 4
  });

  // Title
  slide.addText(data.title || "Conclusion", {
    x: 0.3, y: 0.8, w: 4.9, h: 0.8,
    fontSize: 28, bold: true, color: C.white,
    fontFace: "Calibri"
  });

  // Bullets with numbered circles
  const bullets = (data.bullets || []).slice(0, 5);
  bullets.forEach((b, i) => {
    slide.addShape(pres.shapes.OVAL, {
      x: 0.3, y: 1.8 + i * 0.6 + 0.06, w: 0.36, h: 0.36,
      fill: { color: C.accent }, line: { color: C.accent }
    });
    slide.addText(`${i + 1}`, {
      x: 0.3, y: 1.8 + i * 0.6 + 0.06, w: 0.36, h: 0.36,
      fontSize: 12, bold: true, color: C.dark,
      align: "center", valign: "middle", fontFace: "Calibri"
    });
    slide.addText(b, {
      x: 0.78, y: 1.8 + i * 0.6, w: 4.4, h: 0.52,
      fontSize: 13, color: C.white,
      fontFace: "Calibri", valign: "middle"
    });
  });

  // Call to action banner
  if (data.call_to_action) {
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
      x: 5.8, y: 4.4, w: 3.8, h: 0.7,
      fill: { color: C.accent }, line: { color: C.accent },
      shadow: shadow(0.3, 8, 3), rectRadius: 0.1
    });
    slide.addText(data.call_to_action, {
      x: 5.8, y: 4.4, w: 3.8, h: 0.7,
      fontSize: 14, bold: true, color: C.dark,
      align: "center", fontFace: "Calibri", valign: "middle"
    });
  }

  addProgressBar(slide, num, total);
}

// ════════════════════════════════════════════════════════════════════════════
//  MAIN RENDER
// ════════════════════════════════════════════════════════════════════════════
const total = slides.length;

slides.forEach((slide, idx) => {
  const num = idx + 1;
  switch ((slide.type || "content").toLowerCase()) {
    case "title":       renderTitle(slide, num, total);       break;
    case "section":     renderSection(slide, num, total);     break;
    case "two_column":  renderTwoColumn(slide, num, total);   break;
    case "stats":       renderStats(slide, num, total);       break;
    case "timeline":    renderTimeline(slide, num, total);    break;
    case "image_focus": renderImageFocus(slide, num, total);  break;
    case "icon_grid":   renderIconGrid(slide, num, total);    break;
    case "quote":       renderQuote(slide, num, total);       break;
    case "conclusion":  renderConclusion(slide, num, total);  break;
    default:            renderContent(slide, num, total);     break;
  }
});

pres.writeFile({ fileName: output })
  .then(() => { console.log("OK:" + output); process.exit(0); })
  .catch(e  => { console.error("ERR:" + e.message); process.exit(1); });
