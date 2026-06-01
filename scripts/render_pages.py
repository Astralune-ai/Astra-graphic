#!/usr/bin/env python3
"""
astra-graphic — Mode B per-page card renderer (editorial engine v8).

Editorial-magazine layout: hairline rules instead of card fills, mono kicker
labels above sections, "the larger, the lighter" type, 20 data/structure blocks,
tables, 14 selectable themes.

Robustness ported from the legacy renderer:
  - per-block height measurement via Playwright
  - group bin-packing into 1080×1440 pages
  - per-page overflow rollback (pop trailing block to next page)
  - automatic image down-sizing to fit a page
  - vertical centering of short pages
  - orphan-heading guard (a section heading never sits alone at page bottom)
  - author header (first page) + signature (last page), optional paper texture

CLI is backward-compatible with the legacy renderer; adds --theme.
"""

import argparse
import base64
import os
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

# ── Page geometry ──────────────────────────────────────────────────
PAGE_W, PAGE_H = 1080, 1440
PAD_X, PAD_TOP, PAD_BOT = 76, 76, 88
USABLE_H = PAGE_H - PAD_TOP - PAD_BOT       # 1276
BLOCK_GAP = 30
IMG_MAX_H = 620
IMG_MIN_H = 220
SAFETY_MARGIN = 20
MONO_URL = "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&display=swap"

SCALE = dict(title=54, subtitle=29, section=37, para=29, li=28, hl=33, caption=21,
             lh_para=1.74, lh_title=1.24, mb_para=18, mb_block=30, dropcap=92, td=26, th=25,
             kick=18)

# ── Fonts ──────────────────────────────────────────────────────────
FONTS = {
 "songti":  ("https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@300;400;500;600;700;900&display=swap", "'Noto Serif SC',serif"),
 "kai":     ("https://fonts.googleapis.com/css2?family=LXGW+WenKai+TC:wght@300;400;700&display=swap", "'LXGW WenKai TC',serif"),
 "xiaowei": ("https://fonts.googleapis.com/css2?family=ZCOOL+XiaoWei&family=Noto+Serif+SC:wght@400;600;800&display=swap", "'ZCOOL XiaoWei','Noto Serif SC',serif"),
}

# ── Themes (name, font_key, colors) ────────────────────────────────
THEMES = {
 "morandi":("莫兰迪·灰粉雅致","songti",
   dict(bg="#EDE8E6",text="#3A3330",dim="#9C918B",accent="#A86F6F",hlbg="#E3DAD8",
        title="#4A403C",sec="#4A403C",tbl_head="#E0D6D3",tbl_line="#D9CEC9",tbl_alt="#E7E0DE")),
 "forest":("墨绿·深林沉静","songti",
   dict(bg="#14251C",text="#E4EAE2",dim="#8AA093",accent="#7FB89A",hlbg="#1E3427",
        title="#9FD3B6",sec="#9FD3B6",tbl_head="#1E3427",tbl_line="#2F4A39",tbl_alt="#192E22")),
 "klein-serif":("克莱因蓝·宋体版","songti",
   dict(bg="#FFFFFF",text="#0F1115",dim="#8A8F98",accent="#002FA7",hlbg="#EAEEF8",
        title="#0F1115",sec="#002FA7",tbl_head="#002FA7",tbl_head_on="#FFFFFF",tbl_line="#E2E5EB",tbl_alt="#F3F5FB")),
 "nuanhe":("暖荷·米白赭石","songti",
   dict(bg="#FAF8F3",text="#2B2622",dim="#9A9088",accent="#B5663A",hlbg="#F0E9DE",
        title="#2B2622",sec="#2B2622",tbl_head="#EAE1D2",tbl_line="#E4DACA",tbl_alt="#F4EEE4")),
 "qingci":("青瓷·楷体青绿","kai",
   dict(bg="#EEF3F0",text="#1E2B26",dim="#7C8A83",accent="#2A7B6B",hlbg="#E1EAE5",
        title="#2A7B6B",sec="#2A7B6B",tbl_head="#DCE8E2",tbl_line="#D3DFD9",tbl_alt="#E7EEEA")),
 "zhusa":("朱砂·暖白正红","songti",
   dict(bg="#FBF7F2",text="#2A2320",dim="#9A8E84",accent="#B0392E",hlbg="#F3E6E2",
        title="#2A2320",sec="#B0392E",tbl_head="#F0DDD8",tbl_head_on="#FFFFFF",tbl_line="#E6D8D0",tbl_alt="#F5EDE7")),
 "moink":("水墨·宣白玄青","songti",
   dict(bg="#F4F2EC",text="#1E1E1B",dim="#8C887E",accent="#3F5358",hlbg="#E7E8E2",
        title="#1E1E1B",sec="#3F5358",tbl_head="#E2E4DE",tbl_line="#DAD9CF",tbl_alt="#EDEBE4")),
 "midnight":("子夜·墨蓝鎏金","songti",
   dict(bg="#161A22",text="#E6E2D8",dim="#8C8A7E",accent="#C9A86A",hlbg="#1E2430",
        title="#D9C49A",sec="#C9A86A",tbl_head="#1E2430",tbl_line="#2C3340",tbl_alt="#1B2029")),
 "daiqing":("黛青·灰蓝小薇","xiaowei",
   dict(bg="#F1F3F4",text="#20282C",dim="#7E8A8E",accent="#4A6670",hlbg="#E3E9EA",
        title="#4A6670",sec="#4A6670",tbl_head="#DFE6E7",tbl_line="#D5DDDE",tbl_alt="#E8ECED")),
 "ouhe":("藕荷·黛紫雅","songti",
   dict(bg="#F6F2F4",text="#2B2530",dim="#968C97",accent="#7A5A78",hlbg="#ECE3EA",
        title="#2B2530",sec="#7A5A78",tbl_head="#E8DDE6",tbl_line="#E0D5DD",tbl_alt="#F0EAEF")),
 "kraft":("麻栗·牛皮赭石","songti",
   dict(bg="#E8E0D2",text="#2E2820",dim="#8E8270",accent="#8A5526",hlbg="#DDD2BE",
        title="#2E2820",sec="#8A5526",tbl_head="#DBCDB4",tbl_head_on="#FFFFFF",tbl_line="#D5C7AE",tbl_alt="#E1D8C8")),
 "mono":("经典·黑白","songti",
   dict(bg="#FFFFFF",text="#141414",dim="#9A9A9A",accent="#141414",hlbg="#F2F2F2",
        title="#141414",sec="#141414",tbl_head="#141414",tbl_head_on="#FFFFFF",tbl_line="#E4E4E4",tbl_alt="#F7F7F7")),
 "mono-dark":("经典·黑白反相","songti",
   dict(bg="#121212",text="#ECECEC",dim="#888888",accent="#ECECEC",hlbg="#1E1E1E",
        title="#FFFFFF",sec="#ECECEC",tbl_head="#ECECEC",tbl_head_on="#121212",tbl_line="#2E2E2E",tbl_alt="#1A1A1A")),
 "mojin":("墨金·深黑鎏金","songti",
   dict(bg="#0D0D0F",text="#E8E0D0",dim="#8A8070",accent="#D4A520",hlbg="#1C1A12",
        title="#E8C766",sec="#D4A520",tbl_head="#1C1A12",tbl_line="#2A2618",tbl_alt="#141208")),
}

DEFAULT_THEME = "mono"          # classic black-on-white
DEFAULT_SIGNATURE = "Astra Lune"


# ── Markdown parsing ───────────────────────────────────────────────

CHART_KINDS = ("bar","kpi","matrix","compare","steps","hero","donut","progress",
               "timeline","funnel","quote","checklist","statrow","tags","notice",
               "ranking","pyramid","quadrant","gauge","cards")


def strip_markdown(text: str) -> str:
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\^\^(.+?)\^\^', r'\1', text)
    return text.strip()


def is_highlight_candidate(line: str, prev_empty: bool, next_empty: bool) -> bool:
    """Short standalone sentence → golden pull-quote (legacy heuristic)."""
    if not prev_empty or not next_empty:
        return False
    s = line.strip()
    if not s or s[0] in '#>!|-' :
        return False
    if s[0].isdigit() or s[0] in '.,;:!?，。；：！？、·…—""‘’「」【】':
        return False
    plain = strip_markdown(s)
    return 6 <= len(plain) <= 25


def parse_markdown(text: str) -> list[dict]:
    blocks = []
    lines = text.strip().split('\n')
    n = len(lines)
    i = 0
    while i < n:
        line = lines[i].rstrip()
        prev_empty = (i == 0) or (lines[i-1].strip() == '')
        next_empty = (i == n-1) or (i+1 < n and lines[i+1].strip() == '')

        if not line:
            i += 1
            continue

        # image
        m = re.match(r'^!\[([^\]]*)\]\(([^)]+)\)', line)
        if m:
            blocks.append({'type': 'image', 'alt': m.group(1), 'path': m.group(2)})
            i += 1
            continue

        # fenced chart block: ```<kind> [title]  ... rows ...  ```
        mc = re.match(r'^```(' + '|'.join(CHART_KINDS) + r')\s*(.*)$', line)
        if mc:
            kind = mc.group(1); title = mc.group(2).strip(); rows = []; i += 1
            while i < n and not lines[i].strip().startswith('```'):
                if lines[i].strip():
                    rows.append(lines[i].strip())
                i += 1
            i += 1  # skip closing ```
            blocks.append({'type': 'chart', 'kind': kind, 'title': title, 'rows': rows})
            continue

        # markdown table
        if line.startswith('|') and i+1 < n and re.match(r'^\s*\|[\s:|-]+\|\s*$', lines[i+1]):
            rows = [line]; i += 2
            while i < n and lines[i].strip().startswith('|'):
                rows.append(lines[i].rstrip()); i += 1
            blocks.append({'type': 'table', 'rows': rows})
            continue

        if line.startswith('# ') and not line.startswith('## '):
            blocks.append({'type': 'title', 'text': line[2:].strip()}); i += 1; continue
        if line.startswith('## '):
            blocks.append({'type': 'subtitle', 'text': line[3:].strip()}); i += 1; continue
        if line.startswith('### '):
            blocks.append({'type': 'section', 'text': line[4:].strip()}); i += 1; continue

        # gold callout (>>)
        if line.startswith('>>'):
            tc = line[2:].strip()
            while i+1 < n and lines[i+1].startswith('>>'):
                i += 1; tc += '\n' + lines[i][2:].strip()
            blocks.append({'type': 'callout-gold', 'text': tc}); i += 1; continue
        # red callout (>)
        if line.startswith('>'):
            tc = line[1:].strip()
            while i+1 < n and lines[i+1].startswith('>') and not lines[i+1].startswith('>>'):
                i += 1; tc += '\n' + lines[i][1:].strip()
            blocks.append({'type': 'callout', 'text': tc}); i += 1; continue

        # list item
        if line.startswith('- '):
            blocks.append({'type': 'li', 'text': line[2:].strip()}); i += 1; continue
        if re.match(r'^\d+\.\s', line):
            blocks.append({'type': 'li', 'text': re.sub(r'^\d+\.\s', '', line).strip()}); i += 1; continue

        if re.match(r'^-{3,}$', line):
            blocks.append({'type': 'divider'}); i += 1; continue

        if is_highlight_candidate(line, prev_empty, next_empty):
            blocks.append({'type': 'highlight', 'text': line.strip()}); i += 1; continue

        # paragraph (gather consecutive lines)
        para = [line]
        while i+1 < n:
            nx = lines[i+1].rstrip()
            if (not nx or nx[0] in '#>!|' or re.match(r'^-{3,}$', nx)
                    or re.match(r'^!\[', nx) or re.match(r'^```', nx)
                    or nx.startswith('- ') or re.match(r'^\d+\.\s', nx)):
                break
            i += 1; para.append(nx)
        blocks.append({'type': 'para', 'text': '\n'.join(para)}); i += 1

    return blocks


# ── Inline + helpers ───────────────────────────────────────────────

def inline(s: str) -> str:
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong class="gold">\1</strong>', s)
    s = re.sub(r'\^\^(.+?)\^\^', r'<span class="teal">\1</span>', s)
    return s


def section_head(txt: str) -> str:
    """'中文 english' → serif Chinese headline + mono uppercase kicker."""
    m = re.match(r'^(.*?[一-鿿])\s+([A-Za-z][A-Za-z0-9 ]*)$', txt.strip())
    if m:
        zh, en = m.group(1).strip(), m.group(2).strip().upper()
        return f'<div class="section"><span class="sec-kick">{en}</span><span class="sec-zh">{inline(zh)}</span></div>'
    return f'<div class="section"><span class="sec-zh">{inline(txt)}</span></div>'


def img_to_base64(path: str) -> str:
    if not path or not os.path.exists(path):
        return ''
    ext = Path(path).suffix.lower().lstrip('.')
    mime = {'jpg':'jpeg','jpeg':'jpeg','png':'png','gif':'gif','webp':'webp'}.get(ext, 'png')
    with open(path, 'rb') as f:
        return f'data:image/{mime};base64,{base64.b64encode(f.read()).decode()}'


def table_html(rows):
    cells = [[c.strip() for c in r.strip().strip('|').split('|')] for r in rows]
    th = ''.join(f'<th>{inline(c)}</th>' for c in cells[0])
    trs = ''.join('<tr>' + ''.join(f'<td>{inline(c)}</td>' for c in r) + '</tr>' for r in cells[1:])
    return f'<table class="tbl"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>'


def _numparse(rows):
    d = []
    for r in rows:
        p = [x.strip() for x in r.split(',')]
        if len(p) < 2:
            continue
        nums = re.findall(r'-?\d+\.?\d*', p[1])
        d.append((p[0], p[1], float(nums[0]) if nums else 0))
    return d


def chart_html(kind, title, rows):
    head = f'<div class="chart-title">{inline(title)}</div>' if title else ''

    if kind in ("bar", "kpi"):
        data = []
        for r in rows:
            parts = [p.strip() for p in r.split(',')]
            if len(parts) < 2:
                continue
            nums = re.findall(r'-?\d+\.?\d*', parts[1])
            data.append((parts[0], parts[1], float(nums[0]) if nums else 0))
        if not data:
            return ''
        mx = max(v for _, _, v in data) or 1
        if kind == "bar":
            rh = ''.join(
              f'<div class="bar-row"><div class="bar-top"><span class="bar-lbl">{inline(l)}</span>'
              f'<span class="bar-val">{raw}</span></div>'
              f'<div class="bar-track"><div class="bar-fill" style="width:{max(3,round(v/mx*100))}%"></div></div></div>'
              for l, raw, v in data)
            return f'<div class="chart bar-chart">{head}{rh}</div>'
        cells = ''.join(f'<div class="kpi-cell"><div class="kpi-num">{raw}</div><div class="kpi-lbl">{inline(l)}</div></div>' for l, raw, _ in data)
        return f'<div class="chart kpi-block">{head}<div class="kpi-grid">{cells}</div></div>'

    if kind == "matrix":
        cells = ''
        for nidx, r in enumerate(rows, 1):
            acc = " is-accent" if r.startswith('*') else ""
            label = r[1:].strip() if acc else r.strip()
            cells += f'<div class="mx-cell{acc}"><div class="mx-nb">{nidx:02d}</div><div class="mx-t">{inline(label)}</div></div>'
        return f'<div class="chart matrix">{head}<div class="mx-grid">{cells}</div></div>'

    if kind == "compare":
        cols = []
        for r in rows[:2]:
            if '|' not in r:
                continue
            t, body = r.split('|', 1)
            items = ''.join(f'<li>{inline(x.strip())}</li>' for x in body.split(';') if x.strip())
            cols.append((t.strip(), items))
        if len(cols) < 2:
            return ''
        (lt, li), (rt, ri) = cols
        return (f'<div class="chart compare">{head}<div class="cmp-grid">'
                f'<div class="cmp-col cmp-old"><div class="cmp-h">{inline(lt)}</div><ul>{li}</ul></div>'
                f'<div class="cmp-col cmp-new"><div class="cmp-h">{inline(rt)}</div><ul>{ri}</ul></div>'
                f'</div></div>')

    if kind == "steps":
        rh = ''
        for nidx, r in enumerate(rows, 1):
            t, d = (r.split('|', 1) if '|' in r else (r, ''))
            rh += (f'<div class="step"><div class="step-nb">{nidx:02d}</div>'
                   f'<div class="step-body"><div class="step-t">{inline(t.strip())}</div>'
                   f'<div class="step-d">{inline(d.strip())}</div></div></div>')
        return f'<div class="chart steps">{head}<div class="step-list">{rh}</div></div>'

    if kind == "hero":
        cells = ''
        for r in rows:
            num, lbl = (r.split('|', 1) if '|' in r else (r, ''))
            cells += f'<div class="hero-cell"><div class="hero-num">{inline(num.strip())}</div><div class="hero-lbl">{inline(lbl.strip())}</div></div>'
        multi = " hero-multi" if len(rows) > 1 else ""
        return f'<div class="chart hero-block{multi}">{head}{cells}</div>'

    if kind == "donut":
        d = _numparse(rows)
        if not d:
            return ''
        cells = ''
        for l, raw, v in d:
            deg = round(min(100, v) / 100 * 360)
            cells += (f'<div class="dn-cell"><div class="dn-ring" style="background:conic-gradient(var(--acc) {deg}deg,var(--ring) {deg}deg);">'
                      f'<div class="dn-hole">{raw}</div></div><div class="dn-lbl">{inline(l)}</div></div>')
        return f'<div class="chart donut">{head}<div class="dn-grid">{cells}</div></div>'

    if kind == "progress":
        d = _numparse(rows)
        if not d:
            return ''
        rh = ''.join(
          f'<div class="pg-row"><div class="pg-top"><span class="pg-lbl">{inline(l)}</span>'
          f'<span class="pg-val">{raw}</span></div>'
          f'<div class="pg-track"><div class="pg-fill" style="width:{max(2,min(100,round(v)))}%"></div></div></div>'
          for l, raw, v in d)
        return f'<div class="chart progress">{head}{rh}</div>'

    if kind == "timeline":
        rh = ''
        for r in rows:
            p = [x.strip() for x in r.split(',', 1)]
            if len(p) < 2:
                continue
            rh += (f'<div class="tl-row"><div class="tl-dot"></div>'
                   f'<div class="tl-time">{inline(p[0])}</div><div class="tl-ev">{inline(p[1])}</div></div>')
        return f'<div class="chart timeline">{head}<div class="tl-list">{rh}</div></div>'

    if kind == "funnel":
        d = _numparse(rows)
        if not d:
            return ''
        mx = max(v for _, _, v in d) or 1
        rh = ''.join(
          f'<div class="fn-row"><div class="fn-bar" style="width:{max(20,round(v/mx*100))}%">'
          f'<span class="fn-lbl">{inline(l)}</span><span class="fn-val">{raw}</span></div></div>'
          for l, raw, v in d)
        return f'<div class="chart funnel">{head}{rh}</div>'

    if kind == "quote":
        body = rows[0] if rows else title
        src = rows[1] if len(rows) > 1 else ''
        srch = f'<div class="q-src">{inline(src)}</div>' if src else ''
        return f'<div class="chart quote-card"><div class="q-mark">&ldquo;</div><div class="q-body">{inline(body)}</div>{srch}</div>'

    if kind == "checklist":
        rh = ''
        for r in rows:
            done = r.startswith('x ') or r.startswith('X ')
            txt = r[2:].strip() if (done or r.startswith('- ')) else r.strip()
            mark = "✓" if done else "○"
            cls = "ck-done" if done else "ck-todo"
            rh += f'<div class="ck-row {cls}"><span class="ck-box">{mark}</span><span class="ck-t">{inline(txt)}</span></div>'
        return f'<div class="chart checklist">{head}{rh}</div>'

    if kind == "statrow":
        cells = ''
        for r in rows:
            p = [x.strip() for x in r.split(',', 1)]
            if len(p) < 2:
                continue
            num, lbl = p[0], p[1]
            cells += f'<div class="sr-cell"><div class="sr-num">{inline(num)}</div><div class="sr-lbl">{inline(lbl)}</div></div>'
        if not cells:
            return ''
        return f'<div class="chart statrow">{head}<div class="sr-grid">{cells}</div></div>'

    if kind == "tags":
        items = []
        for r in rows:
            for piece in (r.split(',') if ',' in r else [r]):
                piece = piece.strip()
                if piece:
                    items.append(piece)
        pills = ''.join(
          (f'<span class="tag tag-acc">{inline(p[1:].strip())}</span>' if p.startswith('*')
           else f'<span class="tag">{inline(p)}</span>') for p in items)
        return f'<div class="chart tagcloud">{head}<div class="tag-wrap">{pills}</div></div>'

    if kind == "notice":
        body = rows[0] if rows else ''
        typ = "info"
        if '|' in body:
            typ, body = body.split('|', 1)
        typ = typ.strip().lower()
        if typ not in ("info", "warn", "ok"):
            typ = "info"
        lab = {"info": "NOTE", "warn": "注意", "ok": "完成"}[typ]
        return f'<div class="chart notice nt-{typ}"><div class="nt-tag">{lab}</div><div class="nt-body">{inline(body.strip())}</div></div>'

    if kind == "ranking":
        rh = ''
        for nidx, r in enumerate(rows, 1):
            top = " rk-top" if nidx <= 3 else ""
            p = [x.strip() for x in r.split(',', 1)]
            name = p[0]; score = p[1] if len(p) > 1 else ''
            sc = f'<span class="rk-score">{inline(score)}</span>' if score else ''
            rh += f'<div class="rk-row{top}"><span class="rk-no">{nidx:02d}</span><span class="rk-name">{inline(name)}</span>{sc}</div>'
        return f'<div class="chart ranking">{head}{rh}</div>'

    if kind == "pyramid":
        nrows = len(rows); rh = ''
        for idx, r in enumerate(rows):
            w = round(46 + (idx / (max(1, nrows-1))) * 54)
            rh += f'<div class="py-row"><div class="py-tier" style="width:{w}%">{inline(r.strip())}</div></div>'
        return f'<div class="chart pyramid">{head}{rh}</div>'

    if kind == "quadrant":
        cells = rows[:4]
        while len(cells) < 4:
            cells.append('')
        c4 = ''.join(f'<div class="qd-cell qd-{idx+1}">{inline(c.strip())}</div>' for idx, c in enumerate(cells))
        return f'<div class="chart quadrant">{head}<div class="qd-grid">{c4}</div></div>'

    if kind == "gauge":
        d = _numparse(rows)
        if not d:
            return ''
        l, raw, v = d[0]; deg = round(min(100, v) / 100 * 180)
        return (f'<div class="chart gauge">{head}'
                f'<div class="gg-wrap"><div class="gg-arc" style="background:conic-gradient(from 270deg,var(--acc) {deg}deg,var(--ring) {deg}deg 180deg,transparent 180deg);"></div>'
                f'<div class="gg-val">{raw}</div></div><div class="gg-lbl">{inline(l)}</div></div>')

    if kind == "cards":
        cc = ''
        for r in rows:
            t, d = (r.split('|', 1) if '|' in r else (r, ''))
            cc += f'<div class="cd-cell"><div class="cd-t">{inline(t.strip())}</div><div class="cd-d">{inline(d.strip())}</div></div>'
        return f'<div class="chart cards">{head}<div class="cd-grid">{cc}</div></div>'

    return ''


def block_to_html(block: dict, dropcap: bool = False) -> str:
    t = block['type']
    if t == 'title':
        return f'<h1 class="title">{inline(block["text"])}</h1>'
    if t == 'subtitle':
        return f'<h2 class="subtitle">{inline(block["text"])}</h2>'
    if t == 'section':
        return section_head(block['text'])
    if t == 'para':
        text = '<br>'.join(inline(l) for l in block['text'].split('\n'))
        cls = 'para dropcap' if dropcap else 'para'
        return f'<p class="{cls}">{text}</p>'
    if t == 'highlight':
        return f'<div class="highlight">{inline(block["text"])}</div>'
    if t == 'callout':
        text = '<br>'.join(inline(l) for l in block['text'].split('\n'))
        return f'<div class="callout">{text}</div>'
    if t == 'callout-gold':
        text = '<br>'.join(inline(l) for l in block['text'].split('\n'))
        return f'<div class="callout-gold">{text}</div>'
    if t == 'li':
        return f'<div class="li">{inline(block["text"])}</div>'
    if t == 'divider':
        return '<div class="hr"></div>'
    if t == 'table':
        return table_html(block['rows'])
    if t == 'chart':
        return chart_html(block['kind'], block['title'], block['rows'])
    if t == 'image':
        b64 = img_to_base64(block['path'])
        if not b64:
            return ''
        max_h = block.get('_shrunk_h', IMG_MAX_H)
        cap = f'<div class="cap">{inline(block["alt"])}</div>' if block.get('alt') else ''
        return f'<figure class="fig"><img src="{b64}" style="max-height:{max_h}px;object-fit:contain">{cap}</figure>'
    return ''


# ── CSS ────────────────────────────────────────────────────────────

def base_css(S):
    return f"""
 *{{margin:0;padding:0;box-sizing:border-box;}}
 .title{{font-size:{S['title']}px;font-weight:600;line-height:{S['lh_title']};margin-bottom:16px;letter-spacing:.01em;}}
 .subtitle{{font-size:{S['subtitle']}px;margin-bottom:34px;font-weight:400;letter-spacing:.06em;}}
 .section{{margin:42px 0 24px;padding-bottom:15px;border-bottom:1px solid var(--seam);}}
 .sec-kick{{display:block;font-family:var(--mono);font-size:{S['kick']}px;font-weight:500;letter-spacing:.26em;color:var(--dimc);margin-bottom:13px;}}
 .sec-zh{{font-size:{S['section']}px;font-weight:600;color:var(--secc);letter-spacing:.015em;line-height:1.2;}}
 .para{{font-size:{S['para']}px;line-height:{S['lh_para']};margin-bottom:{S['mb_para']}px;}}
 .para.dropcap::first-letter{{font-size:{S['dropcap']}px;font-weight:600;float:left;line-height:.78;margin:8px 16px 0 0;color:var(--acc);}}
 .li{{font-size:{S['li']}px;line-height:1.7;margin-bottom:11px;padding-left:28px;position:relative;}}
 .li::before{{content:"";position:absolute;left:2px;top:.62em;width:14px;height:2px;background:var(--acc);}}
 .highlight{{font-size:{S['hl']}px;font-weight:500;line-height:1.6;padding:8px 0 8px 28px;margin:26px 0;border-left:3px solid var(--acc);}}
 .callout{{font-size:{S['li']+1}px;font-weight:500;line-height:1.62;padding:20px 0 20px 26px;margin:26px 0;border-left:4px solid var(--acc);}}
 .callout-gold{{font-size:{S['li']+1}px;font-weight:600;line-height:1.62;padding:20px 0 20px 26px;margin:26px 0;border-left:4px solid var(--acc);}}
 .hr{{width:100%;height:1px;margin:34px 0;background:var(--seam);}}
 .tbl{{width:100%;border-collapse:collapse;margin:24px 0;font-size:{S['td']}px;}}
 .tbl th{{font-size:{S['th']}px;font-weight:700;text-align:left;padding:14px 16px;}}
 .tbl td{{padding:13px 16px;line-height:1.5;}}
 .fig{{margin:36px 0;}}
 .fig img{{width:100%;display:block;}}
 .fig .cap{{font-family:var(--mono);font-size:{S['caption']}px;margin-top:14px;letter-spacing:.08em;text-align:center;}}
 .gold{{font-weight:600;color:var(--acc);}}
 .teal{{font-weight:600;color:var(--secc);}}
 /* ===== chart blocks — hairline editorial, no box ===== */
 .chart{{margin:30px 0;}}
 .chart-title{{font-size:{S['section']-6}px;font-weight:600;margin-bottom:20px;}}
 .bar-row{{padding:17px 0;border-top:1px solid var(--seam);}}
 .bar-row:first-child{{border-top:0;padding-top:2px;}}
 .bar-top{{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:11px;}}
 .bar-lbl{{font-size:{S['li']}px;font-weight:500;}}
 .bar-val{{font-family:var(--mono);font-size:{S['li']+4}px;font-weight:500;font-variant-numeric:tabular-nums;}}
 .bar-track{{height:6px;}} .bar-fill{{height:100%;}}
 .kpi-grid{{display:grid;grid-template-columns:1fr 1fr;}}
 .kpi-cell{{padding:6px 0;}}
 .kpi-cell:first-child{{padding-right:36px;border-right:1px solid var(--seam);}}
 .kpi-cell:nth-child(2){{padding-left:36px;}}
 .kpi-num{{font-size:78px;font-weight:400;line-height:1;letter-spacing:-1px;font-variant-numeric:tabular-nums;}}
 .kpi-lbl{{font-size:{S['caption']+2}px;margin-top:14px;font-weight:400;letter-spacing:.04em;}}
 .mx-grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:0;border-top:1px solid var(--seam);border-left:1px solid var(--seam);}}
 .mx-cell{{padding:22px 24px;border-right:1px solid var(--seam);border-bottom:1px solid var(--seam);}}
 .mx-nb{{font-family:var(--mono);font-size:{S['caption']}px;font-weight:500;letter-spacing:.12em;margin-bottom:10px;}}
 .mx-t{{font-size:{S['li']}px;font-weight:500;line-height:1.4;}}
 .cmp-grid{{display:grid;grid-template-columns:1fr 1fr;gap:0;}}
 .cmp-col{{padding:4px 0;}}
 .cmp-old{{padding-right:34px;border-right:1px solid var(--seam);}}
 .cmp-new{{padding-left:34px;}}
 .cmp-h{{font-size:{S['li']+3}px;font-weight:600;margin-bottom:18px;}}
 .cmp-col ul{{margin:0;padding-left:0;list-style:none;}}
 .cmp-col li{{font-size:{S['caption']+3}px;line-height:1.55;margin-bottom:13px;padding-left:24px;position:relative;}}
 .cmp-col li::before{{content:"";position:absolute;left:0;top:.62em;width:12px;height:2px;}}
 .step{{display:grid;grid-template-columns:62px 1fr;gap:22px;align-items:start;padding:20px 0;border-top:1px solid var(--seam);}}
 .step:first-child{{border-top:0;padding-top:2px;}}
 .step-nb{{font-family:var(--mono);font-size:32px;font-weight:400;line-height:1.1;font-variant-numeric:tabular-nums;}}
 .step-t{{font-size:{S['li']+2}px;font-weight:600;margin-bottom:7px;}}
 .step-d{{font-size:{S['caption']+2}px;line-height:1.6;}}
 .hero-block{{padding:24px 0;}}
 .hero-block.hero-multi{{display:grid;grid-template-columns:1fr 1fr;gap:28px;}}
 .hero-num{{font-size:148px;font-weight:400;line-height:.86;letter-spacing:-3px;font-variant-numeric:tabular-nums;}}
 .hero-multi .hero-num{{font-size:104px;}}
 .hero-lbl{{font-size:{S['li']}px;margin-top:18px;font-weight:400;letter-spacing:.04em;}}
 .dn-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:20px;}}
 .dn-cell{{text-align:center;}}
 .dn-ring{{width:148px;height:148px;border-radius:50%;margin:0 auto;display:flex;align-items:center;justify-content:center;}}
 .dn-hole{{width:116px;height:116px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-family:var(--mono);font-size:30px;font-weight:500;font-variant-numeric:tabular-nums;}}
 .dn-lbl{{font-size:{S['caption']+2}px;margin-top:15px;font-weight:400;letter-spacing:.04em;}}
 .pg-row{{padding:15px 0;border-top:1px solid var(--seam);}}
 .pg-row:first-child{{border-top:0;padding-top:2px;}}
 .pg-top{{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:11px;}}
 .pg-lbl{{font-size:{S['li']}px;font-weight:500;}}
 .pg-val{{font-family:var(--mono);font-size:{S['li']+2}px;font-weight:500;font-variant-numeric:tabular-nums;}}
 .pg-track{{height:6px;}} .pg-fill{{height:100%;}}
 .tl-row{{display:grid;grid-template-columns:22px 158px 1fr;gap:18px;align-items:start;padding:0 0 26px;position:relative;}}
 .tl-row:last-child{{padding-bottom:0;}}
 .tl-list{{position:relative;}}
 .tl-dot{{width:13px;height:13px;border-radius:50%;margin-top:7px;z-index:2;}}
 .tl-list::before{{content:"";position:absolute;left:6px;top:8px;bottom:8px;width:1px;}}
 .tl-time{{font-family:var(--mono);font-size:{S['caption']+1}px;font-weight:500;font-variant-numeric:tabular-nums;letter-spacing:.04em;}}
 .tl-ev{{font-size:{S['li']}px;line-height:1.45;}}
 .fn-row{{display:flex;justify-content:center;margin-bottom:12px;}}
 .fn-row:last-child{{margin-bottom:0;}}
 .fn-bar{{height:60px;display:flex;align-items:center;justify-content:space-between;padding:0 28px;}}
 .fn-lbl{{font-size:{S['li']}px;font-weight:500;}}
 .fn-val{{font-family:var(--mono);font-size:{S['li']}px;font-weight:500;font-variant-numeric:tabular-nums;}}
 .quote-card{{position:relative;padding:6px 0 0 0;}}
 .q-mark{{font-family:var(--mono);font-size:130px;line-height:.7;font-weight:600;opacity:.16;position:absolute;top:-10px;left:-6px;}}
 .q-body{{font-size:{S['hl']+5}px;font-weight:500;line-height:1.55;position:relative;z-index:2;padding-top:34px;}}
 .q-src{{font-family:var(--mono);font-size:{S['caption']}px;margin-top:22px;font-weight:500;letter-spacing:.1em;text-align:right;}}
 .ck-row{{display:flex;align-items:baseline;gap:18px;font-size:{S['li']}px;line-height:1.5;padding:13px 0;border-top:1px solid var(--seam);}}
 .ck-row:first-child{{border-top:0;}}
 .ck-box{{font-size:{S['li']+1}px;font-weight:600;flex:0 0 auto;}}
 .ck-done .ck-t{{opacity:.5;}}
 .sr-grid{{display:flex;gap:0;}}
 .sr-cell{{text-align:center;flex:1;padding:6px 0;}}
 .sr-cell + .sr-cell{{border-left:1px solid var(--seam);}}
 .sr-num{{font-size:62px;font-weight:400;line-height:1;letter-spacing:-1px;font-variant-numeric:tabular-nums;}}
 .sr-lbl{{font-size:{S['caption']}px;margin-top:12px;font-weight:400;letter-spacing:.04em;}}
 .tag-wrap{{display:flex;flex-wrap:wrap;gap:13px;}}
 .tag{{font-size:{S['caption']+2}px;font-weight:400;padding:11px 22px;border-radius:30px;}}
 .notice{{display:grid;grid-template-columns:auto 1fr;gap:20px;align-items:start;padding-left:24px;border-left:3px solid var(--acc);}}
 .nt-tag{{font-family:var(--mono);font-size:{S['caption']-1}px;font-weight:600;letter-spacing:.16em;padding:6px 12px;align-self:start;white-space:nowrap;}}
 .nt-body{{font-size:{S['li']}px;line-height:1.6;font-weight:400;}}
 .rk-row{{display:flex;align-items:baseline;gap:22px;padding:16px 0;border-top:1px solid var(--seam);font-size:{S['li']}px;}}
 .rk-row:first-child{{border-top:0;}}
 .rk-no{{font-family:var(--mono);font-size:{S['li']+2}px;font-weight:500;font-variant-numeric:tabular-nums;flex:0 0 auto;width:42px;}}
 .rk-name{{flex:1;font-weight:500;}}
 .rk-score{{font-family:var(--mono);font-weight:500;font-variant-numeric:tabular-nums;}}
 .py-row{{display:flex;justify-content:center;margin-bottom:9px;}}
 .py-row:last-child{{margin-bottom:0;}}
 .py-tier{{padding:16px 20px;text-align:center;font-size:{S['li']}px;font-weight:500;}}
 .qd-grid{{display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr;border-top:1px solid var(--seam);border-left:1px solid var(--seam);aspect-ratio:1.5;}}
 .qd-cell{{padding:26px;font-size:{S['li']}px;font-weight:500;line-height:1.4;display:flex;align-items:center;border-right:1px solid var(--seam);border-bottom:1px solid var(--seam);}}
 .gauge{{text-align:center;}}
 .gg-wrap{{position:relative;width:240px;height:130px;margin:0 auto;overflow:hidden;}}
 .gg-arc{{width:240px;height:240px;border-radius:50%;}}
 .gg-val{{position:absolute;bottom:6px;left:0;right:0;font-family:var(--mono);font-size:48px;font-weight:500;font-variant-numeric:tabular-nums;}}
 .gg-lbl{{font-size:{S['caption']+2}px;margin-top:16px;font-weight:400;letter-spacing:.04em;}}
 .cd-grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:34px;}}
 .cd-cell{{padding-top:18px;border-top:2px solid var(--acc);}}
 .cd-t{{font-size:{S['li']+2}px;font-weight:600;margin-bottom:11px;}}
 .cd-d{{font-size:{S['caption']+2}px;line-height:1.55;}}
 /* author header + signature */
 .author-header{{display:flex;align-items:center;gap:22px;margin-bottom:40px;padding-bottom:26px;border-bottom:1px solid var(--seam);}}
 .author-header img{{width:96px;height:96px;border-radius:50%;object-fit:cover;}}
 .author-header .name{{font-size:32px;font-weight:600;color:var(--secc);}}
 .author-header .meta{{font-family:var(--mono);font-size:18px;color:var(--dimc);margin-top:8px;letter-spacing:.08em;}}
 .author-header .tags{{font-family:var(--mono);font-size:17px;color:var(--acc);margin-top:6px;letter-spacing:.1em;}}
 .signature{{margin-top:48px;padding-top:24px;border-top:1px solid var(--seam);font-family:var(--mono);font-size:{S['caption']}px;color:var(--dimc);letter-spacing:.1em;}}
"""


def theme_css(c):
    head_on = c.get('tbl_head_on', c['text'])
    return f"""
 :root{{--mono:'IBM Plex Mono',ui-monospace,monospace;--acc:{c['accent']};--ring:{c['tbl_line']};
        --seam:{c['tbl_line']};--dimc:{c['dim']};--secc:{c['sec']};}}
 body{{background:{c['bg']};color:{c['text']};}}
 .title{{color:{c['title']};}} .subtitle{{color:{c['accent']};}}
 .para{{color:{c['text']};}} .li{{color:{c['text']};}}
 .highlight{{color:{c['text']};}}
 .callout{{color:{c['text']};}} .callout-gold{{color:{c['accent']};}}
 .fig .cap{{color:{c['dim']};}}
 .tbl th{{background:{c['tbl_head']};color:{head_on};border-bottom:2px solid {c['accent']};}}
 .tbl td{{border-bottom:1px solid {c['tbl_line']};color:{c['text']};}}
 .tbl tbody tr:nth-child(even){{background:{c['tbl_alt']};}}
 .chart-title{{color:{c['sec']};}}
 .bar-lbl{{color:{c['text']};}} .bar-val{{color:{c['accent']};}}
 .bar-track{{background:{c['tbl_line']};}} .bar-fill{{background:{c['accent']};}}
 .kpi-num{{color:{c['accent']};}} .kpi-lbl{{color:{c['dim']};}}
 .mx-nb{{color:{c['dim']};}} .mx-t{{color:{c['text']};}}
 .mx-cell.is-accent .mx-nb{{color:{c['accent']};}} .mx-cell.is-accent .mx-t{{color:{c['accent']};font-weight:600;}}
 .cmp-h{{color:{c['sec']};}} .cmp-old .cmp-h{{color:{c['dim']};}}
 .cmp-col li{{color:{c['text']};}}
 .cmp-old li::before{{background:{c['dim']};}} .cmp-new li::before{{background:{c['accent']};}}
 .step-nb{{color:{c['accent']};}} .step-t{{color:{c['text']};}} .step-d{{color:{c['dim']};}}
 .hero-num{{color:{c['accent']};}} .hero-lbl{{color:{c['dim']};}}
 .dn-hole{{background:{c['bg']};color:{c['accent']};}} .dn-lbl{{color:{c['dim']};}}
 .pg-lbl{{color:{c['text']};}} .pg-val{{color:{c['accent']};}}
 .pg-track{{background:{c['tbl_line']};}} .pg-fill{{background:{c['accent']};}}
 .tl-dot{{background:{c['accent']};}} .tl-list::before{{background:{c['tbl_line']};}}
 .tl-time{{color:{c['accent']};}} .tl-ev{{color:{c['text']};}}
 .fn-bar{{background:{c['accent']};color:{head_on};}}
 .q-mark{{color:{c['accent']};}} .q-body{{color:{c['text']};}} .q-src{{color:{c['dim']};}}
 .ck-done .ck-box{{color:{c['accent']};}} .ck-todo .ck-box{{color:{c['dim']};}} .ck-t{{color:{c['text']};}}
 .sr-num{{color:{c['accent']};}} .sr-lbl{{color:{c['dim']};}}
 .tag{{background:transparent;border:1px solid {c['tbl_line']};color:{c['text']};}}
 .tag-acc{{border-color:{c['accent']};color:{c['accent']};}}
 .nt-tag{{background:transparent;border:1px solid {c['accent']};color:{c['accent']};}} .nt-body{{color:{c['text']};}}
 .rk-no{{color:{c['dim']};}} .rk-top .rk-no{{color:{c['accent']};}}
 .rk-name{{color:{c['text']};}} .rk-score{{color:{c['accent']};}}
 .py-tier{{background:{c['accent']};color:{head_on};opacity:.5;}}
 .py-row:last-child .py-tier{{opacity:1;}}
 .qd-cell{{color:{c['text']};}} .qd-1{{color:{c['accent']};font-weight:600;}}
 .gg-val{{color:{c['accent']};}} .gg-lbl{{color:{c['dim']};}}
 .cd-t{{color:{c['sec']};}} .cd-d{{color:{c['dim']};}}
"""


def full_css(theme_key):
    _, fk, c = THEMES[theme_key]
    fonts, fam = FONTS[fk]
    css = f".content{{font-family:{fam};}}\n" + base_css(SCALE) + theme_css(c)
    return css, fonts, c


# ── Measurement ────────────────────────────────────────────────────

def measure_blocks(page, blocks, css, fonts):
    inner = PAGE_W - PAD_X * 2
    containers = ''.join(
        f'<div id="block-{i}" style="width:{inner}px">{block_to_html(b)}</div>'
        for i, b in enumerate(blocks))
    html = (f'<!DOCTYPE html><html><head><meta charset="utf-8">'
            f'<link rel="stylesheet" href="{fonts}"><link rel="stylesheet" href="{MONO_URL}">'
            f'<style>{css} body{{width:{PAGE_W}px;padding:0 {PAD_X}px;}}</style></head>'
            f'<body>{containers}</body></html>')
    page.set_content(html, timeout=120000)
    try:
        page.evaluate("document.fonts.ready")
    except Exception:
        pass
    page.wait_for_timeout(700)
    heights = []
    for i in range(len(blocks)):
        h = page.evaluate(f'document.getElementById("block-{i}").getBoundingClientRect().height')
        heights.append(int(h) + BLOCK_GAP)
    return heights


def measure_content(page, css, fonts, content_html):
    inner_css = (f'{css} body{{width:{PAGE_W}px;}} .content{{padding:0 {PAD_X}px;}}')
    html = (f'<!DOCTYPE html><html><head><meta charset="utf-8">'
            f'<link rel="stylesheet" href="{fonts}"><link rel="stylesheet" href="{MONO_URL}">'
            f'<style>{inner_css}</style></head>'
            f'<body><div class="content" id="mc">{content_html}</div></body></html>')
    page.set_content(html, timeout=120000)
    page.wait_for_timeout(300)
    return int(page.evaluate('document.getElementById("mc").getBoundingClientRect().height'))


# ── Page builder ───────────────────────────────────────────────────

def build_page_html(css, fonts, colors, content_html, page_num, total,
                    watermark, center_offset, bg_url=''):
    pad_top = PAD_TOP + center_offset
    texture = (f'<div style="position:fixed;inset:0;background-image:url(\'{bg_url}\');'
               f'background-size:100% auto;background-repeat:repeat-y;opacity:.10;z-index:0"></div>'
               if bg_url else '')
    pn = (f'<div style="position:fixed;top:32px;right:42px;font-family:var(--mono);font-size:18px;'
          f'color:{colors["accent"]};opacity:.6;letter-spacing:2px;z-index:20">{page_num:02d} / {total:02d}</div>')
    wm = (f'<div style="position:fixed;bottom:30px;right:42px;font-family:var(--mono);font-size:16px;'
          f'color:{colors["dim"]};opacity:.65;letter-spacing:2px;z-index:20">{watermark}</div>')
    return (f'<!DOCTYPE html><html><head><meta charset="utf-8">'
            f'<link rel="stylesheet" href="{fonts}"><link rel="stylesheet" href="{MONO_URL}">'
            f'<style>{css}'
            f' html,body{{width:{PAGE_W}px;height:{PAGE_H}px;overflow:hidden;-webkit-font-smoothing:antialiased;}}'
            f' .content{{position:relative;z-index:10;padding:{pad_top}px {PAD_X}px {PAD_BOT}px;}}'
            f'</style></head><body>{texture}{pn}{wm}'
            f'<div class="content">{content_html}</div></body></html>')


def balance_tail(pages, heights):
    """Avoid a near-empty last page (a 'widow'). If the last page is sparse,
    pull trailing blocks down from the previous page until the two are roughly
    balanced (or moving one more would overflow the last page)."""
    if len(pages) < 2:
        return pages
    cap = USABLE_H - SAFETY_MARGIN

    def ph(pg):
        return sum(heights[i] for i in pg)

    last, prev = pages[-1], pages[-2]
    # only intervene when the last page is clearly under-filled
    while len(prev) > 1 and ph(last) < 0.45 * USABLE_H:
        cand = prev[-1]
        if ph(last) + heights[cand] > cap:
            break
        if ph(last) + heights[cand] >= ph(prev) - heights[cand]:
            # moving it would make the last page heavier than prev — would just
            # shift the imbalance; take it only if it leaves both reasonably full
            if ph(last) + heights[cand] < 0.55 * USABLE_H:
                prev.pop(); last.insert(0, cand)
            break
        prev.pop(); last.insert(0, cand)
    return pages


def apply_orphan_guard(pages, blocks):
    """Move a section/subtitle heading off the bottom of a page if it would be
    the last block there (and the page has other content)."""
    fixed = []
    carry = []
    for pg in pages:
        pg = carry + pg
        carry = []
        if len(pg) > 1:
            last = blocks[pg[-1]]
            if last['type'] in ('section', 'subtitle'):
                carry = [pg.pop()]
        fixed.append(pg)
    if carry:
        fixed.append(carry)
    return [p for p in fixed if p]


# ── Main ───────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description='astra-graphic Mode B editorial card renderer')
    ap.add_argument('--input', '-i', required=True)
    ap.add_argument('--output', '-o', required=True)
    ap.add_argument('--theme', '-t', default=DEFAULT_THEME, help=f'one of: {", ".join(THEMES)}')
    ap.add_argument('--background', '-bg', default='', help='optional paper-texture image')
    ap.add_argument('--avatar', default='')
    ap.add_argument('--author', default=DEFAULT_SIGNATURE)
    ap.add_argument('--date', default='')
    ap.add_argument('--tags', default='')
    ap.add_argument('--watermark', default=DEFAULT_SIGNATURE)
    ap.add_argument('--no-author', action='store_true', help='skip author header')
    ap.add_argument('--no-signature', action='store_true', help='skip closing signature')
    args = ap.parse_args()

    if args.theme not in THEMES:
        print(f"⚠️  unknown theme '{args.theme}', falling back to {DEFAULT_THEME}")
        args.theme = DEFAULT_THEME

    css, fonts, colors = full_css(args.theme)
    blocks = parse_markdown(Path(args.input).read_text())
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    name = THEMES[args.theme][0]
    print(f"🎨 theme: {args.theme} ({name})")

    bg_url = img_to_base64(args.background) if args.background else ''

    # author header / signature
    author_html = ''
    if args.avatar and not args.no_author:
        av = img_to_base64(args.avatar)
        if av:
            tags = f'<div class="tags">{args.tags}</div>' if args.tags else ''
            date = f'<div class="meta">{args.date}</div>' if args.date else ''
            author_html = (f'<div class="author-header"><img src="{av}">'
                           f'<div><div class="name">{args.author}</div>{date}{tags}</div></div>')
    signature_html = '' if args.no_signature else f'<div class="signature">— {args.author}</div>'

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width': PAGE_W, 'height': PAGE_H}, device_scale_factor=2)

        print("📐 measuring blocks...")
        heights = measure_blocks(page, blocks, css, fonts)

        author_h = 0
        if author_html:
            author_h = measure_content(page, css, fonts, author_html) + BLOCK_GAP

        # ── bin-pack (each non-divider block = one group) ──
        cap = USABLE_H - SAFETY_MARGIN
        pages_content = []
        cur = []
        remaining = cap - author_h
        for i, b in enumerate(blocks):
            if b['type'] == 'divider':
                continue
            h = heights[i]
            if h <= remaining:
                cur.append(i); remaining -= h
            elif h <= cap:
                if cur:
                    pages_content.append(cur)
                cur = [i]; remaining = cap - h
            else:
                # too tall — shrink image if possible, else give own page
                if b['type'] == 'image':
                    overflow = h - cap
                    new_h = IMG_MAX_H - overflow - 20
                    if new_h >= IMG_MIN_H:
                        b['_shrunk_h'] = new_h
                        heights[i] = max(h - overflow - 20, new_h + BLOCK_GAP)
                        h = heights[i]
                        if h <= remaining:
                            cur.append(i); remaining -= h; continue
                if cur:
                    pages_content.append(cur); cur = []
                pages_content.append([i]); remaining = cap
        if cur:
            pages_content.append(cur)

        pages_content = apply_orphan_guard(pages_content, blocks)
        pages_content = balance_tail(pages_content, heights)
        pages_content = apply_orphan_guard(pages_content, blocks)
        total = len(pages_content)
        print(f"📄 {total} pages planned")

        first_para_done = False
        rendered = []
        pi = 0
        while pi < len(pages_content):
            idxs = pages_content[pi]
            is_first = (pi == 0)
            is_last = (pi == len(pages_content) - 1)

            def build(idxs, is_first, is_last):
                nonlocal first_para_done
                parts = []
                if is_first and author_html:
                    parts.append(author_html)
                local_first = False
                for bi in idxs:
                    b = blocks[bi]
                    dc = False
                    if is_first and not first_para_done and not local_first and b['type'] == 'para':
                        dc = True; local_first = True
                    parts.append(block_to_html(b, dropcap=dc))
                if is_last and signature_html:
                    parts.append(signature_html)
                return '\n'.join(parts)

            content_html = build(idxs, is_first, is_last)
            content_h = measure_content(page, css, fonts, content_html)

            # overflow rollback
            it = 0
            while content_h > USABLE_H and len(idxs) > 1 and it < 12:
                it += 1
                spill = idxs.pop()
                is_last = False
                content_html = build(idxs, is_first, False)
                content_h = measure_content(page, css, fonts, content_html)
                if pi + 1 < len(pages_content):
                    pages_content[pi + 1].insert(0, spill)
                else:
                    pages_content.append([spill]); total += 1

            first_para_done = first_para_done or (is_first and '<p class="para dropcap"' in content_html)

            # center any under-filled page vertically — incl. a sparse last page,
            # so a short closing page reads as intentional, not "ran out of content"
            center_offset = 0
            if content_h < USABLE_H:
                center_offset = (USABLE_H - content_h) // 2

            html = build_page_html(css, fonts, colors, content_html,
                                   pi + 1, total, args.watermark, center_offset, bg_url)
            page.set_viewport_size({'width': PAGE_W, 'height': PAGE_H})
            page.set_content(html, timeout=120000)
            try:
                page.evaluate("document.fonts.ready")
            except Exception:
                pass
            page.wait_for_timeout(420)
            out_path = out_dir / f'{pi+1:02d}.png'
            page.screenshot(path=str(out_path), type='png')
            rendered.append(out_path)
            fill = min(100, int(content_h / USABLE_H * 100))
            print(f'✅ {out_path.name}  ({content_h}px / {USABLE_H}px = {fill}%)')
            pi += 1

        browser.close()
    print(f'\nDone! {len(rendered)} pages → {out_dir}')


if __name__ == '__main__':
    main()
