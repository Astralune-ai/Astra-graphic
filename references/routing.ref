# Mode Decision Tree — Extended Reference

> Detailed routing logic for SKILL.md Section 2.

## Content Signal Extraction

### char_count — Strip Markdown Syntax

```
char_count = len(raw_text)
  MINUS: all markdown syntax characters (#, *, >, -, !, [, ], (, ))
  MINUS: blank lines
  MINUS: image references ![...](...) entirely
  MINUS: front matter (--- block)
  KEEP:  actual visible text content only
```

### page_estimate

```
page_estimate = ceil(char_count / 300)
```

300 chars/page assumes: 38px body font, 1080×1440 canvas, 80px side padding, average paragraph density.

### Content Type Classification

| Type | Signals |
|------|---------|
| `article` | 3+ paragraphs, section headings, > 600 chars |
| `tutorial` | Numbered steps, code blocks, "如何/how to" in title |
| `list` | Bullet-heavy, < 100 chars per item, 5+ items |
| `visual` | Keywords: 封面/海报/cover/poster/banner, or image-only input |
| `opinion` | First-person pronouns, "我认为/I think", strong adjectives |
| `data` | Tables, percentages, numbers > 3 per paragraph |
| `mixed` | None of the above dominant, or multiple types present |

### Boolean Signals

```
has_data         = any(re.search(r'\d+[%％]|\d+\.\d+', paragraph) for paragraph in paragraphs)
is_visual_request = any(kw in input_text.lower() for kw in
                     ["封面", "海报", "cover", "poster", "banner", "头图"])
text_density     = char_count / max(section_count, 1)
```

---

## Mode A Triggers — AI Image Direct

Condition: visual-first content, short text, single image output.

| Condition | Example Input |
|-----------|--------------|
| `is_visual_request = True` | "做一张推升的封面" |
| `page_estimate ≤ 2` AND `content_type = visual` | "AI 趋势" (topic keyword only) |
| `page_estimate ≤ 2` AND `has_data = False` AND `text_density < 100` | Short quote or opinion |
| Empty input (topic keyword only) | "认知升级" |
| Image input (reference image provided) | User sends a photo |

## Mode B Triggers — Precision Text Layout

Condition: text-heavy, structured content, multi-page.

| Condition | Example Input |
|-----------|--------------|
| `page_estimate ≥ 4` AND `text_density > 200` | 2000-char deep analysis article |
| `content_type = article` | Long-form with headings and paragraphs |
| `content_type = tutorial` AND `page_estimate ≥ 5` | 10-step deployment guide |
| Markdown file with 3+ sections | `article.md` with clear structure |
| `content_type = list` AND `char_count > 1500` | Long comparison list |

## Mode C Triggers — Hybrid

Condition: mixed signals, medium length, benefits from visual cover + text body.

| Condition | Example Input |
|-----------|--------------|
| `page_estimate` 3–5, mixed signals | 1000-char article with some data |
| `content_type = mixed` | Narrative + data + opinion blend |
| `content_type = opinion` AND `page_estimate ≥ 3` | Personal essay, medium length |
| DEFAULT when signals are ambiguous | Anything that doesn't clearly match A or B |

---

## Brand Influence Rules

```
brand_preferred_mode = brand.json → ai_style.preferred_mode

IF brand_preferred_mode is set:
  - Treat as SUGGESTION, not override
  - Content signals ALWAYS win
  - Example: brand prefers A, but 2000-char article → B wins
  - Example: brand prefers B, but user says "做封面" → A wins
  
IF brand has no preferred_mode (null):
  - Pure content-signal routing, no brand bias
```

---

## Edge Cases & Fallback

| Input | Behavior |
|-------|----------|
| Empty string | Prompt user for topic, then Mode A |
| URL only | Fetch page content → re-analyze signals from extracted text |
| Image only (no text) | Mode A, use image as `--ref` |
| Markdown file | Read file → analyze signals as if inline text |
| Mixed: text + image | Analyze text portion; image becomes reference for Mode A pages |
| `--mode=auto` explicit | Same as no flag; run full signal analysis |
| Very long (20+ pages) | Mode B forced; warn user about page count |
| Single sentence | Mode A; treat as title/caption for visual |

**Fallback**: If signal analysis is inconclusive (no condition matches clearly), default to **Mode C** — it covers both visual and text needs.

---

## ASCII Decision Flowchart

```
START
  │
  ├─ --mode flag set? ──yes──► Use specified mode ──► DONE
  │                              (ai→A, text→B, hybrid→C)
  no
  │
  ├─ is_visual_request? ──yes──► MODE A
  │
  no
  │
  ├─ page_estimate ≤ 2
  │   AND visual-first? ──yes──► MODE A
  │
  no
  │
  ├─ page_estimate ≥ 4
  │   AND text_density > 200? ──yes──► MODE B
  │
  no
  │
  ├─ content_type = article
  │   OR long tutorial? ──yes──► MODE B
  │
  no
  │
  ├─ page_estimate 3-5
  │   AND mixed signals? ──yes──► MODE C
  │
  no
  │
  └─ DEFAULT ──────────────────► MODE C
```

---

*Reference for: SKILL.md Section 2 — Mode Routing Decision Tree*
