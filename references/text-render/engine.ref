# Text Rendering Pipeline — Engine Reference

> Complete HTML → PNG pipeline for Mode B output.

## Overview

```
Markdown → Parse Blocks → Detect Tone → Inject Brand CSS
  → Generate HTML → Playwright Render → Measure Heights
  → Page Binning → Multi-page Screenshot → PNG Output
```

Scripts:
- `{skill_dir}/scripts/render_pages.py` — multi-page card output (1080×1440 per page)
- `{skill_dir}/scripts/render_single.py` — single image output (long/infograph/comic/whiteboard)
- `{skill_dir}/scripts/capture.js` — generic Playwright capture utility

---

## 1. Markdown Parsing

Input markdown is parsed into typed blocks:

| Block Type | Markdown Signal | CSS Class |
|-----------|----------------|-----------|
| `title` | `# Heading` | `.title` |
| `subtitle` | `## Heading` | `.subtitle` |
| `section` | `### Heading` | `.section-heading` |
| `para` | Plain paragraph | `.para` |
| `callout` | `> blockquote` | `.callout` |
| `callout-gold` | `> !!!` or auto-detected golden sentence | `.callout-gold` |
| `image` | `![alt](src)` | `.image-block` |
| `highlight` | Standalone short sentence (golden sentence) | `.highlight` |
| `divider` | `---` or `***` | `.divider` |
| `list` | `- item` or `1. item` | `.list-block` |

### Inline Markup

| Markdown | HTML | CSS Class |
|----------|------|-----------|
| `**bold text**` | `<strong class="gold">` | `.gold` — accent color |
| `^^highlight^^` | `<span class="teal">` | `.teal` — secondary color |
| `*italic*` | `<em>` | Standard italic |
| `` `code` `` | `<code>` | Monospace, subtle bg |

---

## 2. HTML Generation

### Template Injection

Each page is built from a base HTML template:

```
<!DOCTYPE html>
<html>
<head>
  <style>
    /* Base reset + page dimensions */
    /* Brand CSS via {{CUSTOM_CSS}} */
    /* Tone CSS variables */
    /* Block-level styles */
  </style>
</head>
<body>
  <div class="page">
    {{CONTENT_BLOCKS}}
  </div>
  {{WATERMARK}}
  {{PAGE_NUMBER}}
</body>
</html>
```

### CSS Variable Insertion

Tone detection (see `tone-detection.md`) produces two CSS variables:

```css
:root {
  --tone-accent: #D4A520;     /* From tone detection */
  --tone-secondary: #2D6A4F;  /* From tone detection */
  --bg: #0D0D0F;              /* From brand */
  --text: #E8E8E8;            /* From brand */
  --muted: #666;              /* From brand */
}
```

### Brand CSS Injection

Brand-specific styles loaded from `{skill_dir}/brands/{brand}/base.css` and injected at `{{CUSTOM_CSS}}` placeholder. Brand CSS overrides default tone variables when brand has explicit palette.

---

## 3. Background Texture

1. Read texture file from `{skill_dir}/brands/{brand}/backgrounds/texture.png`
2. Base64 encode: `data:image/png;base64,{encoded}`
3. Apply as CSS background:
   ```css
   body {
     background-image: url(data:image/png;base64,...);
     background-repeat: repeat-y;
     background-size: 100% auto;
     opacity: 0.45; /* 45% opacity via pseudo-element overlay */
   }
   ```
4. Texture sits behind content, adds grain/paper feel without competing with text.

---

## 4. Playwright Workflow

### render_pages.py (Multi-Card)

```
1. Parse markdown → block list
2. Detect tone → CSS variables
3. For each page assignment:
   a. Build HTML string with assigned blocks
   b. page.set_content(html)
   c. Measure actual rendered height via JS:
      document.querySelector('.page').scrollHeight
   d. If height > USABLE_H (1260px):
      → Rollback: remove last block, push to next page
   e. Set viewport: 1080 × 1440
   f. page.screenshot(path=output_path, type='png')
```

### render_single.py (Long Image / Infograph)

```
1. Parse markdown → block list
2. Build single HTML with all blocks
3. page.set_content(html)
4. Measure total content height via JS
5. Set viewport: 1080 × measured_height
6. page.screenshot(full_page=True)
```

### capture.js (Generic)

```
Usage: node capture.js <html-file> <output-png> <width> <height>

1. Launch Chromium (headless)
2. Read HTML file
3. page.setViewportSize({ width, height })
4. page.setContent(htmlContent)
5. page.screenshot({ path: outputPath })
6. Close browser
```

---

## 5. Page Binning Algorithm

For multi-card mode (`-m`), content must fit 1080×1440 pages.

### Constants

```
PAGE_W      = 1080px
PAGE_H      = 1440px
PAD_TOP     = 80px
PAD_BOTTOM  = 100px
PAD_SIDES   = 80px
USABLE_H    = PAGE_H - PAD_TOP - PAD_BOTTOM = 1260px
```

### Algorithm

```
current_page = []
current_height = 0

for block in parsed_blocks:
    block_h = estimate_height(block)  # Pre-render estimate
    
    if current_height + block_h > USABLE_H:
        # Overflow — finalize current page
        pages.append(current_page)
        current_page = [block]
        current_height = block_h
    else:
        current_page.append(block)
        current_height += block_h

# Don't forget the last page
pages.append(current_page)
```

### Overflow Detection & Rollback

After Playwright renders each page:
1. Measure actual `.page` scrollHeight
2. If scrollHeight > USABLE_H:
   - Remove last block from page
   - Push removed block to next page
   - Re-render current page
   - Re-bin remaining blocks
3. Max 3 rollback iterations per page to prevent infinite loop.

---

## 6. Image Handling

All images embedded as base64 to avoid external dependencies:

```python
with open(image_path, 'rb') as f:
    b64 = base64.b64encode(f.read()).decode()
img_src = f"data:image/png;base64,{b64}"
```

Image constraints:
- `max-height: 950px` (leaves room for caption + spacing)
- `min-height: 220px` (too small = invisible on mobile)
- `object-fit: contain` (never crop, never stretch)
- `width: 100%` of content area
- 16px margin top and bottom

---

## 7. Vertical Centering

When page content is shorter than USABLE_H, center vertically:

```
content_h = measured content height
top_offset = (USABLE_H - content_h) / 2
```

Applied via `padding-top` on the `.page` container. Prevents content from "floating" at the top of short pages.

---

*Reference for: SKILL.md Section 6.1 — Rendering Pipeline*
