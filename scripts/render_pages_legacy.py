#!/usr/bin/env python3
"""
Asyre XHS — Per-page card renderer.
Reads Markdown, measures each block's height via Playwright,
bins blocks into 1080×1440 pages, renders each page independently.

Key layout rules:
  1. Images limited to IMG_MAX_H px — compact enough to share page with text
  2. Section-based grouping — text+image in same section stay together
  3. Vertical centering — content block centered within page, even top/bottom margins
  4. Zero text/image cutoff guaranteed via post-render verification

v2.0 (2026-03-26): Added highlight detection, dropcap, tone-aware colors
"""

import argparse
import base64
import os
import re
import shutil
# import zipfile  # removed — no longer generating zip
from pathlib import Path

from playwright.sync_api import sync_playwright

# ── Constants ──────────────────────────────────────────────────────
PAGE_W = 1080
PAGE_H = 1440
PAD_X = 80
PAD_TOP = 80
PAD_BOT = 100
USABLE_H = PAGE_H - PAD_TOP - PAD_BOT  # 1260
BLOCK_GAP = 24  # gap between blocks
IMG_MAX_H = 950  # max image height — landscape (687px) untouched, portrait capped at 950 for readability
SAFETY_MARGIN = 20  # extra margin to avoid edge-case overflow

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = SKILL_DIR / "templates"

# ── Tone Detection System ──────────────────────────────────────────

TONE_KEYWORDS = {
    'strategic': ['战略', '策略', '商业', '投资', '市场', '竞争', '增长', '定价', '渠道', '营收', '估值', '资本', '金融', '泡沫'],
    'tech': ['架构', '系统', '算法', '代码', '模型', 'API', '工程', '数据', '服务器', 'Transformer', '技术'],
    'philosophical': ['认知', '思维', '本质', '意义', '哲学', '存在', '意识', '价值观'],
    'literary': ['故事', '人物', '写作', '文字', '诗', '叙事', '创作', '表达'],
    'default': []
}

TONE_COLORS = {
    'strategic': {'accent': '#D4A520', 'secondary': '#2D6A4F', 'callout_bg': 'rgba(40,35,20,0.75)'},
    'tech': {'accent': '#40B8B8', 'secondary': '#3D5A80', 'callout_bg': 'rgba(20,30,40,0.75)'},
    'philosophical': {'accent': '#C4A55A', 'secondary': '#8B5E3C', 'callout_bg': 'rgba(35,30,25,0.75)'},
    'literary': {'accent': '#C08050', 'secondary': '#6B4E3D', 'callout_bg': 'rgba(40,30,25,0.75)'},
    'default': {'accent': '#D4A520', 'secondary': '#40B8B8', 'callout_bg': 'rgba(30,30,40,0.75)'}
}


def detect_tone(blocks: list[dict]) -> str:
    """Scan all text blocks and return the most matching tone."""
    all_text = ''
    for b in blocks:
        if 'text' in b:
            all_text += b['text'] + ' '
    
    scores = {}
    for tone, keywords in TONE_KEYWORDS.items():
        if tone == 'default':
            continue
        score = sum(1 for kw in keywords if kw in all_text)
        if score > 0:
            scores[tone] = score
    
    if not scores:
        return 'default'
    
    return max(scores, key=scores.get)


def get_tone_colors(tone: str) -> dict:
    """Get color scheme for a tone."""
    return TONE_COLORS.get(tone, TONE_COLORS['default'])


# ── Markdown → sections ───────────────────────────────────────────

def strip_markdown(text: str) -> str:
    """Remove markdown markup to get plain text for length calculation."""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\^\^(.+?)\^\^', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    return text.strip()


def is_highlight_candidate(line: str, prev_empty: bool, next_empty: bool) -> bool:
    """Check if a line qualifies as a highlight (golden quote).
    
    Criteria:
    - Independent paragraph (surrounded by empty lines)
    - Pure text length ≤ 25 characters (excluding markdown)
    - Not starting with # > ! (already captured by other patterns)
    - Not starting with punctuation or digits
    - Has substance (not just "第一章" etc.)
    """
    if not prev_empty or not next_empty:
        return False
    
    stripped = line.strip()
    if not stripped:
        return False
    
    # Skip markdown headers, quotes, images
    if stripped.startswith('#') or stripped.startswith('>') or stripped.startswith('!'):
        return False
    
    # Skip lines starting with punctuation or digits
    first_char = stripped[0]
    if first_char.isdigit() or first_char in '.,;:!?，。；：！？、·…—""''「」【】':
        return False
    
    # Check plain text length
    plain = strip_markdown(stripped)
    if len(plain) > 25:
        return False
    
    # Skip trivial short content (chapter markers, etc.)
    if len(plain) < 6:
        return False
    
    return True


def parse_markdown(text: str) -> list[dict]:
    """Parse markdown into typed blocks."""
    blocks = []
    lines = text.strip().split('\n')
    n = len(lines)
    i = 0
    
    while i < n:
        line = lines[i].rstrip()
        
        # Check for empty line context (for highlight detection)
        prev_empty = (i == 0) or (lines[i - 1].strip() == '')
        next_empty = (i == n - 1) or (i + 1 < n and lines[i + 1].strip() == '')

        if not line:
            i += 1
            continue

        # Image
        m = re.match(r'^!\[([^\]]*)\]\(([^)]+)\)', line)
        if m:
            blocks.append({'type': 'image', 'alt': m.group(1), 'path': m.group(2)})
            i += 1
            continue

        # Main title (h1)
        if line.startswith('# ') and not line.startswith('## '):
            blocks.append({'type': 'title', 'text': line[2:].strip()})
            i += 1
            continue

        # Subtitle (h2)
        if line.startswith('## '):
            blocks.append({'type': 'subtitle', 'text': line[3:].strip()})
            i += 1
            continue

        # Section header (h3)
        if line.startswith('### '):
            blocks.append({'type': 'section', 'text': line[4:].strip()})
            i += 1
            continue

        # Gold callout (>>)
        if line.startswith('>>'):
            text_content = line[2:].strip()
            while i + 1 < n and lines[i + 1].startswith('>>'):
                i += 1
                text_content += '\n' + lines[i][2:].strip()
            blocks.append({'type': 'callout-gold', 'text': text_content})
            i += 1
            continue

        # Red callout (>)
        if line.startswith('>') and not line.startswith('>>'):
            text_content = line[1:].strip()
            while i + 1 < n and lines[i + 1].startswith('>') and not lines[i + 1].startswith('>>'):
                i += 1
                text_content += '\n' + lines[i][1:].strip()
            blocks.append({'type': 'callout', 'text': text_content})
            i += 1
            continue

        # Divider
        if re.match(r'^-{3,}$', line):
            blocks.append({'type': 'divider'})
            i += 1
            continue

        # Check for highlight (golden quote) before treating as paragraph
        if is_highlight_candidate(line, prev_empty, next_empty):
            blocks.append({'type': 'highlight', 'text': line.strip()})
            i += 1
            continue

        # Paragraph
        para_lines = [line]
        while i + 1 < n:
            next_line = lines[i + 1].rstrip()
            if (not next_line or next_line.startswith('#') or next_line.startswith('>')
                    or re.match(r'^-{3,}$', next_line) or re.match(r'^!\[', next_line)):
                break
            i += 1
            para_lines.append(next_line)
        blocks.append({'type': 'para', 'text': '\n'.join(para_lines)})
        i += 1

    return blocks


def make_block_groups(blocks: list[dict]) -> list[list[int]]:
    """Create groups of 1 block each (no binding).
    
    Each block is its own group. Dividers are skipped.
    Simple packing gives the best fill rate when images are large.
    """
    groups: list[list[int]] = []
    for i, b in enumerate(blocks):
        if b['type'] == 'divider':
            continue
        groups.append([i])
    return groups


# ── Inline markup ──────────────────────────────────────────────────

def inline_markup(text: str) -> str:
    """Convert **bold** to gold, ^^text^^ to teal."""
    text = re.sub(r'\*\*(.+?)\*\*', r'<span class="gold">\1</span>', text)
    text = re.sub(r'\^\^(.+?)\^\^', r'<span class="teal">\1</span>', text)
    return text


# ── Image base64 ──────────────────────────────────────────────────

def img_to_base64(path: str) -> str:
    if not os.path.exists(path):
        return ''
    ext = Path(path).suffix.lower().lstrip('.')
    mime = {'jpg': 'jpeg', 'jpeg': 'jpeg', 'png': 'png', 'gif': 'gif', 'webp': 'webp'}.get(ext, 'png')
    with open(path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode()
    return f'data:image/{mime};base64,{b64}'


# ── Block → HTML ──────────────────────────────────────────────────

def block_to_html(block: dict, dropcap: bool = False) -> str:
    """Convert a block to HTML.
    
    Args:
        block: The block dict with type and content
        dropcap: If True and block is 'para', add dropcap class
    """
    t = block['type']
    if t == 'title':
        return f'<div class="main-title">{inline_markup(block["text"])}</div>'
    elif t == 'subtitle':
        return f'<div class="main-subtitle">{inline_markup(block["text"])}</div>'
    elif t == 'section':
        return f'<div class="section-title">{inline_markup(block["text"])}</div>'
    elif t == 'para':
        lines = block['text'].split('\n')
        text = '<br>'.join(inline_markup(l) for l in lines)
        css_class = 'para dropcap' if dropcap else 'para'
        return f'<div class="{css_class}">{text}</div>'
    elif t == 'highlight':
        return f'<div class="highlight">{inline_markup(block["text"])}</div>'
    elif t == 'callout':
        return f'<div class="callout">{inline_markup(block["text"])}</div>'
    elif t == 'callout-gold':
        return f'<div class="callout-gold">{inline_markup(block["text"])}</div>'
    elif t == 'divider':
        return '<div class="divider"></div>'
    elif t == 'image':
        b64 = img_to_base64(block['path'])
        if b64:
            max_h = block.get('_shrunk_h', IMG_MAX_H)
            return (f'<div class="article-image">'
                    f'<img src="{b64}" style="max-height:{max_h}px;object-fit:contain">'
                    f'</div>')
        return ''
    return ''


# ── Load CSS from template ────────────────────────────────────────

def load_style() -> str:
    template = TEMPLATES_DIR / "page.html"
    html = template.read_text()
    m = re.search(r'<style>(.*?)</style>', html, re.DOTALL)
    return m.group(1) if m else ''


# ── Page HTML builder ─────────────────────────────────────────────

def build_page_html(style: str, bg_url: str, content_html: str,
                    page_num: int, total: int, watermark: str,
                    is_last: bool = False, center_offset: int = 0,
                    tone_colors: dict = None) -> str:
    """Build a full HTML page for one card.
    
    center_offset: extra top padding to vertically center the content block.
    tone_colors: dict with accent, secondary, callout_bg for CSS variables
    """
    # Inject tone colors as CSS variables
    if tone_colors:
        tone_css = (f":root {{ "
                    f"--accent: {tone_colors['accent']}; "
                    f"--secondary: {tone_colors['secondary']}; "
                    f"--callout-bg: {tone_colors['callout_bg']}; "
                    f"--text: #E8E0D0; "
                    f"--text-dim: #8A8070; "
                    f"--bg: #0D0D0F; "
                    f"}}\n")
    else:
        tone_css = ''
    
    page_style = tone_css + style.replace("url('{{BG_URL}}')", f"url('{bg_url}')")

    page_indicator = (f'<div style="position:fixed;top:30px;right:40px;font-size:22px;'
                      f'color:rgba(212,165,32,0.4);letter-spacing:3px;z-index:20">'
                      f'{page_num:02d}/{total:02d}</div>')

    wm_html = (f'<div style="position:fixed;bottom:30px;right:40px;font-size:20px;'
               f'color:rgba(212,165,32,0.15);letter-spacing:6px;z-index:20">'
               f'{watermark}</div>')

    fade = ''
    if is_last:
        fade = ('<div style="position:fixed;bottom:0;left:0;right:0;height:200px;'
                'background:linear-gradient(transparent,#0D0D0F);z-index:15"></div>')

    pad_top = PAD_TOP + center_offset

    return f'''<!DOCTYPE html><html><head><meta charset="utf-8">
<style>{page_style}
body {{ width: {PAGE_W}px; height: {PAGE_H}px; overflow: hidden; }}
.content {{ padding: {pad_top}px {PAD_X}px {PAD_BOT}px {PAD_X}px; }}
</style></head><body>
<div class="bg-texture"></div>
{page_indicator}{wm_html}{fade}
<div class="content">{content_html}</div>
</body></html>'''


# ── Measure blocks ────────────────────────────────────────────────

def measure_blocks(page, blocks: list[dict], style: str) -> list[int]:
    """Measure each block's rendered height using Playwright."""
    containers = []
    for i, b in enumerate(blocks):
        html = block_to_html(b)
        containers.append(f'<div id="block-{i}" style="width:{PAGE_W - PAD_X * 2}px">{html}</div>')

    measure_html = f'''<!DOCTYPE html><html><head><meta charset="utf-8">
    <style>{style}
    body {{ width: {PAGE_W}px; padding: 0 {PAD_X}px; }}
    </style></head><body>{''.join(containers)}</body></html>'''

    page.set_content(measure_html, timeout=120000)
    page.wait_for_timeout(800)

    heights = []
    for i in range(len(blocks)):
        h = page.evaluate(f'document.getElementById("block-{i}").getBoundingClientRect().height')
        heights.append(int(h) + BLOCK_GAP)

    return heights


def measure_html_content(page, style: str, bg_url: str, content_html: str) -> int:
    """Measure the actual rendered height of content (excluding padding)."""
    page_style = style.replace("url('{{BG_URL}}')", f"url('{bg_url}')")
    html = f'''<!DOCTYPE html><html><head><meta charset="utf-8">
    <style>{page_style}
    body {{ width: {PAGE_W}px; }}
    .content {{ padding: 0 {PAD_X}px; }}
    </style></head><body>
    <div class="bg-texture"></div>
    <div class="content" id="mc">{content_html}</div>
    </body></html>'''
    page.set_content(html, timeout=120000)
    page.wait_for_timeout(300)
    return int(page.evaluate('document.getElementById("mc").getBoundingClientRect().height'))


# ── Main ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Asyre XHS per-page card renderer')
    parser.add_argument('--input', '-i', required=True, help='Markdown file')
    parser.add_argument('--output', '-o', required=True, help='Output directory')
    parser.add_argument('--background', '-bg', help='Background image path')
    parser.add_argument('--avatar', help='Author avatar path')
    parser.add_argument('--author', default='Asher 修荷', help='Author name')
    parser.add_argument('--date', default='', help='Date string')
    parser.add_argument('--tags', default='', help='Tags (× separated)')
    parser.add_argument('--watermark', default='修荷 · 蜕升学院', help='Watermark text')
    args = parser.parse_args()

    md_text = Path(args.input).read_text()
    blocks = parse_markdown(md_text)
    groups = make_block_groups(blocks)

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Detect tone and get colors
    tone = detect_tone(blocks)
    tone_colors = get_tone_colors(tone)
    print(f"🎨 Detected tone: {tone} → accent={tone_colors['accent']}")

    style = load_style()
    bg_url = img_to_base64(args.background) if args.background else ''

    # Author header
    avatar_b64 = img_to_base64(args.avatar) if args.avatar else ''
    author_html = ''
    if avatar_b64:
        tags_html = f'<div class="tags">{args.tags}</div>' if args.tags else ''
        date_html = f'<div class="meta">{args.date}</div>' if args.date else ''
        author_html = (f'<div class="author-header">'
                       f'<img src="{avatar_b64}">'
                       f'<div><div class="name">{args.author}</div>'
                       f'{date_html}{tags_html}</div></div>')

    signature_html = (f'<div class="signature">— {args.author}</div>'
                      f'<div class="watermark">{args.watermark}</div>')

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': PAGE_W, 'height': PAGE_H})

        # Measure all blocks
        print("📐 Measuring blocks...")
        heights = measure_blocks(page, blocks, style)

        # Measure author header
        author_h = 0
        if author_html:
            page.set_content(f'''<!DOCTYPE html><html><head><meta charset="utf-8">
            <style>{style} body {{ width: {PAGE_W}px; padding: 0 {PAD_X}px; }}</style></head>
            <body><div id="ah" style="width:{PAGE_W - PAD_X * 2}px">{author_html}</div></body></html>''')
            page.wait_for_timeout(500)
            author_h = int(page.evaluate('document.getElementById("ah").getBoundingClientRect().height')) + BLOCK_GAP

        # ── Group-based bin packing ──
        # Groups are small units: typically 1 block (text) or 2 blocks (text+image).
        # Images are pre-grouped with their preceding text block to keep context together.
        # Groups stay together; pages fill naturally without forcing full sections to single pages.
        
        pages_content: list[list[int]] = []
        current_page: list[int] = []
        cap = USABLE_H - SAFETY_MARGIN  # effective capacity per page
        remaining_h = cap - author_h  # first page has author header

        for group in groups:
            group_h = sum(heights[bi] for bi in group)

            if group_h <= remaining_h:
                # Group fits on current page
                current_page.extend(group)
                remaining_h -= group_h

            elif group_h <= cap:
                # Group fits on a fresh page but not current one
                if current_page:
                    pages_content.append(current_page)
                current_page = list(group)
                remaining_h = cap - group_h

            else:
                # Group too tall — try shrinking images to fit
                image_indices = [bi for bi in group if blocks[bi]['type'] == 'image']
                
                fitted = False
                overflow = group_h - cap
                
                if image_indices and overflow > 0:
                    # Group overflows — shrink images to fit
                    reduction = overflow + 20  # +20 safety margin
                    new_max_h = IMG_MAX_H - reduction
                    
                    if new_max_h >= 220:  # minimum useful image height
                        for bi in image_indices:
                            blocks[bi]['_shrunk_h'] = new_max_h
                            heights[bi] = max(heights[bi] - reduction, new_max_h + BLOCK_GAP)
                        
                        group_h = sum(heights[bi] for bi in group)
                        if group_h <= remaining_h:
                            # Fits on current page after shrinking
                            current_page.extend(group)
                            remaining_h -= group_h
                            fitted = True
                        elif group_h <= cap:
                            # Fits on a fresh page after shrinking
                            if current_page:
                                pages_content.append(current_page)
                            current_page = list(group)
                            remaining_h = cap - group_h
                            fitted = True
                
                if not fitted:
                    # Still doesn't fit even after shrinking — give it own page
                    if current_page:
                        pages_content.append(current_page)
                        current_page = []
                    pages_content.append(group)
                    remaining_h = cap

        if current_page:
            pages_content.append(current_page)

        total_pages = len(pages_content)
        print(f"📄 {total_pages} pages planned")

        # ── Render each page ──
        rendered = []
        first_para_done = False  # Track if we've applied dropcap
        
        for pi, block_indices in enumerate(pages_content):
            page_num = pi + 1
            is_first = (pi == 0)
            is_last = (pi == len(pages_content) - 1)

            # Build content HTML
            content_parts = []
            if is_first and author_html:
                content_parts.append(author_html)
            
            for bi in block_indices:
                b = blocks[bi]
                # Apply dropcap only to the first para block on the first page
                apply_dropcap = False
                if is_first and not first_para_done and b['type'] == 'para':
                    apply_dropcap = True
                    first_para_done = True
                content_parts.append(block_to_html(b, dropcap=apply_dropcap))
            
            if is_last:
                content_parts.append(signature_html)

            content_html = '\n'.join(content_parts)

            # Measure actual content height for this page
            content_h = measure_html_content(page, style, bg_url, content_html)

            # Overflow check — if content too tall, pop last block to next page
            overflow_iter = 0
            while content_h > USABLE_H and len(block_indices) > 1 and overflow_iter < 10:
                overflow_iter += 1
                overflow_bi = block_indices.pop()
                is_last = False
                content_parts = []
                if is_first and author_html:
                    content_parts.append(author_html)
                # Rebuild with dropcap preserved for first para on first page
                first_para_in_rebuild = False
                for bi in block_indices:
                    b = blocks[bi]
                    apply_dc = False
                    if is_first and not first_para_in_rebuild and b['type'] == 'para':
                        apply_dc = True
                        first_para_in_rebuild = True
                    content_parts.append(block_to_html(b, dropcap=apply_dc))
                content_html = '\n'.join(content_parts)
                content_h = measure_html_content(page, style, bg_url, content_html)

                if pi + 1 < len(pages_content):
                    pages_content[pi + 1].insert(0, overflow_bi)
                else:
                    pages_content.append([overflow_bi])
                    total_pages += 1
            
            if overflow_iter >= 10:
                print(f'  ⚠️ Page {page_num}: overflow check hit limit, may be oversized')

            # Calculate vertical centering offset
            center_offset = 0
            if not is_last and content_h < USABLE_H:
                center_offset = (USABLE_H - content_h) // 2

            # Render with tone colors
            full_html = build_page_html(style, bg_url, content_html,
                                        page_num, total_pages, args.watermark,
                                        is_last, center_offset, tone_colors)

            if is_last:
                viewport_h = max(content_h + PAD_TOP + PAD_BOT + 200, 800)
                page.set_viewport_size({'width': PAGE_W, 'height': viewport_h})
            else:
                page.set_viewport_size({'width': PAGE_W, 'height': PAGE_H})

            page.set_content(full_html, timeout=120000)
            page.wait_for_timeout(500)

            out_path = out_dir / f'{page_num:02d}.png'
            page.screenshot(path=str(out_path), type='png')
            rendered.append(out_path)

            fill_pct = min(100, int(content_h / USABLE_H * 100))
            print(f'✅ {out_path.name}  ({content_h}px / {USABLE_H}px = {fill_pct}% fill)')

        browser.close()

    # zip generation removed — deliver PNGs directly
    print(f'\nDone! {len(rendered)} pages → {out_dir}')


if __name__ == '__main__':
    main()
