#!/usr/bin/env python3
"""
astra-graphic — Mode B single-page renderer (editorial engine v8).

Renders an entire Markdown article as ONE tall image (1080px wide, adaptive
height) using the same editorial engine as render_pages.py: hairline rules,
mono kicker section headers, 20 data/structure blocks, tables, 14 themes.

Used for the long / infograph / visual-note molds where pagination is not wanted.

Usage:
  python3 render_single.py --input article.md --output ./out/ --theme mono \
    [--avatar a.jpg --author "Astra Lune" --date 2026-06 --tags "A × B" \
     --watermark "Astra Lune" --background texture.png --no-author --no-signature]
"""

import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from render_pages import (  # reuse the single source of truth
    parse_markdown, block_to_html, full_css, img_to_base64,
    THEMES, MONO_URL, PAGE_W, PAD_X, DEFAULT_THEME, DEFAULT_SIGNATURE,
)

PAD_TOP = 72
PAD_BOT = 84


def main():
    ap = argparse.ArgumentParser(description='astra-graphic Mode B single-page renderer')
    ap.add_argument('--input', '-i', required=True)
    ap.add_argument('--output', '-o', required=True)
    ap.add_argument('--theme', '-t', default=DEFAULT_THEME, help=f'one of: {", ".join(THEMES)}')
    ap.add_argument('--background', '-bg', default='')
    ap.add_argument('--avatar', default='')
    ap.add_argument('--author', default=DEFAULT_SIGNATURE)
    ap.add_argument('--date', default='')
    ap.add_argument('--tags', default='')
    ap.add_argument('--watermark', default=DEFAULT_SIGNATURE)
    ap.add_argument('--no-author', action='store_true')
    ap.add_argument('--no-signature', action='store_true')
    ap.add_argument('--name', default='single', help='output filename stem')
    args = ap.parse_args()

    if args.theme not in THEMES:
        print(f"⚠️  unknown theme '{args.theme}', falling back to {DEFAULT_THEME}")
        args.theme = DEFAULT_THEME

    css, fonts, colors = full_css(args.theme)
    blocks = parse_markdown(Path(args.input).read_text())
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"🎨 theme: {args.theme} ({THEMES[args.theme][0]})  → single image")

    bg_url = img_to_base64(args.background) if args.background else ''

    # author header (reuse base_css .author-header classes)
    author_html = ''
    if args.avatar and not args.no_author:
        av = img_to_base64(args.avatar)
        if av:
            tags = f'<div class="tags">{args.tags}</div>' if args.tags else ''
            date = f'<div class="meta">{args.date}</div>' if args.date else ''
            author_html = (f'<div class="author-header"><img src="{av}">'
                           f'<div><div class="name">{args.author}</div>{date}{tags}</div></div>')

    # content (dropcap on first para)
    parts = []
    if author_html:
        parts.append(author_html)
    first_para = False
    for b in blocks:
        if b['type'] == 'divider':
            parts.append('<div class="hr"></div>')
            continue
        dc = (not first_para and b['type'] == 'para')
        if dc:
            first_para = True
        parts.append(block_to_html(b, dropcap=dc))
    if not args.no_signature:
        parts.append(f'<div class="signature">— {args.author}</div>')
    content_html = '\n'.join(parts)

    texture = (f'<div style="position:fixed;inset:0;background-image:url(\'{bg_url}\');'
               f'background-size:100% auto;background-repeat:repeat-y;opacity:.10;z-index:0"></div>'
               if bg_url else '')
    wm = (f'<div style="text-align:right;font-family:var(--mono);font-size:16px;'
          f'color:{colors["dim"]};opacity:.65;letter-spacing:2px;margin-top:30px;">{args.watermark}</div>')

    html = (f'<!DOCTYPE html><html><head><meta charset="utf-8">'
            f'<link rel="stylesheet" href="{fonts}"><link rel="stylesheet" href="{MONO_URL}">'
            f'<style>{css}'
            f' html,body{{width:{PAGE_W}px;-webkit-font-smoothing:antialiased;}}'
            f' .content{{position:relative;z-index:10;padding:{PAD_TOP}px {PAD_X}px {PAD_BOT}px;}}'
            f'</style></head><body>{texture}'
            f'<div class="content">{content_html}{wm}</div></body></html>')

    out_path = out_dir / f'{args.name}.png'
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={'width': PAGE_W, 'height': 1440}, device_scale_factor=2)
        page.set_content(html, timeout=120000)
        try:
            page.evaluate("document.fonts.ready")
        except Exception:
            pass
        page.wait_for_timeout(700)
        content_h = int(page.evaluate('document.querySelector(".content").getBoundingClientRect().height'))
        final_h = max(content_h, 600)
        page.set_viewport_size({'width': PAGE_W, 'height': final_h})
        page.wait_for_timeout(200)
        page.screenshot(path=str(out_path), clip={'x': 0, 'y': 0, 'width': PAGE_W, 'height': final_h})
        browser.close()

    print(f'✅ {out_path} ({final_h}px tall)\nDone! Single-page image → {out_path}')


if __name__ == '__main__':
    main()
