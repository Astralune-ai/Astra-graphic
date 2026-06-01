# Brand First-Time Setup

> Wizard flow when a client has no existing brand configuration.

## Detection

```python
brand_dir = f"{skill_dir}/brands/{client_slug}/"
if not os.path.exists(brand_dir):
    trigger_first_time_setup()
```

No `brands/{client}/` directory = no brand configured. Trigger setup wizard.

---

## Setup Flow

### Step 1: Ask 3 Questions

Use **AskUserQuestion** — all 3 in a single call to minimize back-and-forth.

```
Q1: 目标受众是谁？
    选项: 小红书用户 / 商务客户 / 社群成员 / 个人朋友圈 / Other (自填)

Q2: 用3个词描述你的品牌个性
    自由文本输入
    示例: 专业严谨沉稳 / 温暖真诚亲切 / 暗黑深度前卫 / 极简克制高级

Q3: 美学方向偏好？
    选项: 暗色赛博 / 亮色温暖 / 极简专业 / 复古文艺
```

### Step 2: Map Answers to Base Brand

Aesthetic direction determines which existing brand to fork:

| Q3 Answer | Fork From | Base Palette |
|-----------|-----------|-------------|
| 暗色赛博 | `tuisheng` | Dark bg `#0D0D0F`, gold `#D4A520`, teal `#40B8B8` |
| 亮色温暖 | `asher` | Warm `#FAFAF8`, brown `#8B5E3C`, ochre `#C08050` |
| 极简专业 | `qihe` | Clean white `#F5F5F5`, blue `#3D5A80`, gray `#666` |
| 复古文艺 | `asher` + color adjust | Paper `#F0E8D8`, sepia `#8B6914`, deep brown `#4A3728` |

### Step 3: Customize from Personality Words

Parse Q2 keywords and adjust the forked brand:

| Keyword Pattern | Adjustment |
|----------------|------------|
| 专业/严谨/商务 | Sans-serif headings, muted accents, low DESIGN_VARIANCE (5-6) |
| 温暖/亲切/真诚 | Serif body, warm palette shift (+10 hue), rounded corners |
| 暗黑/深度/前卫 | Darken bg by 10%, increase contrast, high DESIGN_VARIANCE (8-9) |
| 极简/克制/留白 | Reduce accent saturation, increase whitespace, fewer decorations |
| 文艺/诗意/质感 | Serif headings, paper texture, sepia tints, literary tone default |
| 科技/未来/赛博 | Monospace accents, teal/cyan palette, tech tone default |

### Step 4: Generate Files

Three files are created from the fork + customization:

#### brand.json

```json
{
  "name": "{client_slug}",
  "display_name": "{Client Name}",
  "description": "Auto-generated from setup wizard",
  "palette": { /* adjusted from fork */ },
  "typography": { /* adjusted from fork */ },
  "ai_style": {
    "preferred_mode": null,
    "default_style": "auto",
    "color_keywords": [/* from palette */],
    "negative_prompts": [/* from aesthetic direction */],
    "tone_variants": null
  },
  "assets": {
    "avatar": null,
    "backgrounds": "{skill_dir}/brands/{client}/backgrounds/",
    "logo": null
  },
  "defaults": {
    "author": "{from Q1 context}",
    "watermark": "@{client_slug}",
    "tags_separator": " × "
  }
}
```

#### base.css

CSS variables matching the palette + typography + tone overrides.

#### ai-style.md

Natural language color/style constraints for Gemini prompt injection.

### Step 5: Save

```
{skill_dir}/brands/{client_slug}/
├── brand.json
├── base.css
├── ai-style.md
├── avatars/          # Empty, user can add later
└── backgrounds/      # Copy default texture from forked brand
```

### Step 6: Confirm with User

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 品牌配置已创建: {client_slug}
━━━━━━━━━━━━━━━━━━━━━━━━━━━
  基于: {forked_brand}
  调色板: {primary} / {accent} / {secondary}
  字体: {heading_font} + {body_font}
  风格: {aesthetic_direction}
━━━━━━━━━━━━━━━━━━━━━━━━━━━
  随时可以修改: 编辑 brands/{client_slug}/brand.json
```

---

## --yes Mode Behavior

When `--yes` flag is set and no brand exists:
- Skip the 3-question wizard
- Fork `tuisheng` as default (most versatile dark brand)
- Auto-generate all files with defaults
- Print: "已使用默认品牌配置 (tuisheng fork)，可后续自定义。"

---

*Reference for: SKILL.md Section 3.3 — First-Time Brand Setup*
