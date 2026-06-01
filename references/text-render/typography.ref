# Typography Rules

> Font sizing, golden sentences, dropcap, overflow protection for Mode B rendering.

## Page Dimensions

```
Width:       1080px
Height:      1440px (3:4 aspect ratio)
Padding:     80px left/right, 80px top, 100px bottom
Usable:      920px wide × 1260px tall
```

---

## Font Size Hierarchy

| Element | Size | Weight | Line-height | Notes |
|---------|------|--------|-------------|-------|
| Title (`# H1`) | 80px | 800 | 1.1 | Tight tracking, accent color optional |
| Section heading (`### H3`) | 56px | 700 | 1.2 | |
| Subtitle (`## H2`) | 44px | 600 | 1.3 | |
| Highlight / Golden sentence | 44px | 700 | 1.4 | With accent border |
| Body paragraph | 38px | 400 | 1.6 | **Minimum**, non-negotiable |
| Callout text | 36px | 400 | 1.5 | Slightly smaller than body |
| Page number | 28px | 300 | — | Muted color |
| Watermark | 24px | 300 | — | Bottom-right, low opacity |

### Mobile Readability Check

Screen scaling: 1080px canvas → ~390px phone display = **2.77x reduction**.

| Canvas Size | Phone Size | Readable? |
|-------------|-----------|-----------|
| 38px | ~14px | Yes (minimum) |
| 32px | ~12px | Borderline |
| 28px | ~10px | Only for meta text |
| 24px | ~9px | Watermark only |

---

## Golden Sentence Detection

Standalone short sentences auto-promoted to highlight style.

### Detection Criteria (ALL must pass)

1. **Standalone**: preceded and followed by blank line (independent paragraph)
2. **Short**: stripped length ≤ 25 characters
3. **Not heading**: does not start with `#`
4. **Not quote**: does not start with `>`
5. **Not image**: does not start with `!`
6. **Minimum length**: ≥ 6 characters (excludes "第一章" type fragments)
7. **Not numeric start**: does not start with digit or punctuation

### Golden Sentence Rendering

```css
.highlight {
  border-left: 4px solid var(--tone-accent);
  background: rgba(var(--tone-accent-rgb), 0.06);  /* 6% opacity */
  padding: 16px 24px;
  font-size: 44px;
  font-weight: 700;
  margin: 24px 0;
}
```

### Limits

- Max **2 golden sentences per page** to avoid over-decoration
- If 3+ detected on one page, only the first 2 get highlight treatment; rest render as normal paragraphs

---

## Dropcap

First page, first paragraph block only.

### Rules

- **When**: Page 1, first block of type `para`
- **Size**: 128px
- **Color**: `var(--tone-accent)` (tone accent color)
- **Font**: Brand heading font (e.g., Noto Serif SC)
- **Float**: left, spanning ~3 lines of body text
- **Margin**: 8px right, 4px bottom

### CSS

```css
.dropcap::first-letter {
  float: left;
  font-size: 128px;
  line-height: 0.8;
  color: var(--tone-accent);
  font-family: var(--heading-font);
  margin-right: 8px;
  margin-top: 4px;
}
```

### Skip Conditions

- Do NOT apply dropcap if first block is a heading, image, or callout
- Do NOT apply if first paragraph starts with a number or punctuation
- Only applies to page 1 — subsequent pages never get dropcap

---

## Overflow Protection

Critical for multi-card mode where each page = 1440px.

### Pipeline

```
1. ESTIMATE  → Pre-calculate block heights from char count + font size
2. BIN       → Assign blocks to pages within USABLE_H budget (1260px)
3. RENDER    → Playwright renders HTML, screenshot each page
4. VERIFY    → Measure actual rendered .page scrollHeight
5. ROLLBACK  → If overflow: remove last block, push to next page, re-render
```

### Height Estimation Heuristics

```python
def estimate_height(block):
    if block.type == 'title':     return 120
    if block.type == 'subtitle':  return 80
    if block.type == 'section':   return 90
    if block.type == 'highlight': return 100
    if block.type == 'divider':   return 40
    if block.type == 'image':     return 600  # Conservative
    if block.type == 'callout':
        lines = ceil(len(block.text) / 22)  # ~22 chars per line at 36px
        return lines * 56 + 32  # line_height + padding
    if block.type == 'para':
        lines = ceil(len(block.text) / 20)  # ~20 chars per line at 38px
        return lines * 61  # 38px * 1.6 line-height
    return 60  # fallback
```

### Rollback Limits

- Max 3 rollback iterations per page
- If still overflowing after 3 rollbacks → force split the offending block (break paragraph)
- Log warning when forced split occurs

---

## Image Constraints

| Property | Value | Reason |
|----------|-------|--------|
| `max-height` | 950px | Leave room for caption + margins within 1260px |
| `min-height` | 220px | Smaller = invisible on phone |
| `object-fit` | `contain` | Never crop, never stretch |
| `width` | 100% of content area | Fill horizontal space |
| `margin` | 16px top/bottom | Breathing room |
| `border-radius` | 8px | Subtle rounding |

---

*Reference for: SKILL.md Section 6.4 — Typography Rules*
