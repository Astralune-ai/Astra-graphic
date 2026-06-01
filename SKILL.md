---
name: astra-graphic
description: |
  Astra 社媒内容创作系统。融合 AI 图片直出 + 精排版引擎 + 品牌管理。
  三种模式：Mode A (AI 信息图直出), Mode B (HTML 精排版), Mode C (混合)。
  12 种 XHS 生图风格 × 8 布局 × 23+ 预设 + 23 种信息图布局 × 20 种信息图风格 + 6 种排版模具 × 6 种密度 + 5 个国风品牌（墨金/素启/暖荷/朱砂/青瓷）。
  触发词: /astra-graphic, 社媒, 小红书, 做卡片, 排版, 信息图, XHS, RedNote, 内容卡片
user-invocable: true
---

# Astra Social — 统一社媒内容创作系统

## 1. Overview + Quick Start

Astra Social 把四个独立技能融合为一个统一入口：AI 图片生成、精排版引擎、品牌系统、内容润色。

三种输出模式：

| Mode | Engine | Best For | Output |
|------|--------|----------|--------|
| **A: AI 直出** | Gemini AI image generation | 封面、海报、简单信息图 | AI-generated PNG |
| **B: 精排版** | HTML/CSS → Playwright → PNG | 长文、深度内容、多页卡片 | 1080×1440 PNG pages |
| **C: 混合** | A + B combined | 系列内容（封面AI + 内容精排） | Mixed PNG series |

### Quick Start

```bash
/astra-graphic [topic or content]                    # Auto-detect mode
/astra-graphic article.md --mode=text                # Force text layout
/astra-graphic --mode=ai --style=notion --preset=knowledge-card
/astra-graphic --brand=mojin                          # Use brand
/astra-graphic article.md --yes                      # Non-interactive, skip confirmations
```

### Options

| Flag | Values | Default | Description |
|------|--------|---------|-------------|
| `--mode` | `ai`, `text`, `hybrid`, `auto` | `auto` | 强制指定输出模式 |
| `--brand` | brand slug | project default | 使用指定品牌配置 |
| `--style` | 20 styles (see Section 5) | auto from analysis | AI 生图风格 |
| `--layout` | 8 layouts (see Section 5) | auto from analysis | AI 生图布局 |
| `--preset` | 23+ presets | none | 预设快捷方式（覆盖 style+layout） |
| `--mold` | `-m`, `-l`, `-i`, `-v`, `-c`, `-w` | `-m` | Mode B 排版模具 |
| `--yes` | flag | off | 非交互模式，跳过所有确认 |

---

## 2. Mode Routing Decision Tree ★ CRITICAL

**AI 必须先读本节再做任何事。** 所有请求先经过路由决策，确定输出模式。

```
STEP 1: Check explicit override
  --mode=ai     → Mode A
  --mode=text   → Mode B
  --mode=hybrid → Mode C
  --mode=auto   → continue to Step 2 (default)

STEP 2: Content signal analysis

  Compute these signals from input:
  - char_count        = total characters in source content
  - page_estimate     = char_count / 300
  - has_data          = content contains numbers/stats/percentages (bool)
  - is_visual_request = content mentions "封面", "海报", "cover", "poster" (bool)
  - text_density      = average chars per logical section
  - content_type      = inferred type (article/tutorial/list/visual/mixed)

  ROUTING TABLE:
  ┌──────────────────────────────────────────────┬────────┐
  │ Condition                                    │ Mode   │
  ├──────────────────────────────────────────────┼────────┤
  │ is_visual_request (封面/海报/单图)             │  A     │
  │ page_estimate ≤ 2 AND visual-first content   │  A     │
  │ page_estimate ≥ 4 AND text_density > 200     │  B     │
  │ content_type = long-form article             │  B     │
  │ content_type = tutorial AND pages ≥ 5        │  B     │
  │ page_estimate 3-5, mixed signals             │  C     │
  │ DEFAULT (ambiguous or short mixed content)   │  C     │
  └──────────────────────────────────────────────┴────────┘

STEP 3: Brand adjustment (optional)
  - If brand.json has ai_style.preferred_mode, treat as suggestion
  - Content signals ALWAYS override brand preference
  - Example: brand prefers Mode A, but 2000-char article → Mode B wins

STEP 4: Brief confirmation
  Output: "将以 [Mode X: 名称] 模式生成。确认？"
  If --yes flag → skip confirmation, proceed directly
```

**Edge cases:**
- Empty input (just a topic keyword) → Mode A (generate visual from topic)
- URL input → fetch content → re-analyze signals
- Image input → Mode A (use as reference)
- Markdown file → read file → analyze signals

Reference: `{skill_dir}/references/routing.ref` for extended decision logic.

---

## 3. Brand System

### 3.1 Loading a Brand

```
Step 0.1: Check --brand flag → if present, use it
Step 0.2: If no flag, scan {skill_dir}/brands/ for project default (default.json)
Step 0.3: If no brand found → offer first-time brand setup (see 3.3)
Step 0.4: Read {skill_dir}/brands/{brand}/brand.json
Step 0.5: Apply brand to current mode:
  - Mode A: Read {skill_dir}/brands/{brand}/ai-style.md
            → inject color constraints + negative prompts into Gemini prompt
  - Mode B: Read {skill_dir}/brands/{brand}/base.css
            → inject into HTML template as {{CUSTOM_CSS}}
  - Mode C: Both of the above
```

### 3.2 brand.json Schema

```json
{
  "name": "brand-slug",
  "display_name": "Brand Display Name",
  "description": "One-line brand description",
  "palette": {
    "primary": "#HEX",
    "secondary": "#HEX",
    "accent": "#HEX",
    "background": "#HEX",
    "text": "#HEX",
    "muted": "#HEX"
  },
  "typography": {
    "heading_font": "font-family string",
    "body_font": "font-family string",
    "accent_font": "font-family string or null"
  },
  "ai_style": {
    "preferred_mode": "A|B|C|null",
    "default_style": "style slug",
    "default_layout": "layout slug",
    "color_keywords": ["dark", "gold", "cyan"],
    "negative_prompts": ["cartoon", "childish"],
    "texture_keywords": ["grain", "matte"]
  },
  "assets": {
    "avatar": "{skill_dir}/brands/{brand}/avatars/avatar.jpg",
    "backgrounds": "{skill_dir}/brands/{brand}/backgrounds/",
    "logo": "{skill_dir}/brands/{brand}/logo.png"
  },
  "defaults": {
    "author": "Author Name",
    "watermark": "Watermark Text",
    "tags_separator": " × "
  }
}
```

### 3.3 First-Time Brand Setup

When no brand exists for a client, ask 3 questions:

1. **受众是谁？** — Target audience (e.g., "25-35岁职场人", "技术从业者")
2. **品牌个性用3个词描述** — (e.g., "专业、温暖、有深度")
3. **美学方向** — 暗色 / 亮色 / 温暖 / 极简 / 赛博 / 自定义

Then:
1. Fork the nearest existing brand as template
2. Generate `brand.json` with adjusted palette + typography
3. Generate `base.css` with CSS variables matching palette
4. Generate `ai-style.md` with color constraints for Gemini
5. Save all to `{skill_dir}/brands/{client}/`
6. Set as project default

### 3.4 Available Brands

| Brand | Slug | Look | Best For |
|-------|------|------|----------|
| 墨金 | `mojin` | 暗色+金/青，赛博学术，颗粒质感 | 深度知识分享，社群内容 |
| 素启 | `suqi` | 商务亮色+墨绿，专业干净 | 客户报告，方案交付 |
| 暖荷 | `nuanhe` | 暖纸质感，米色+赭，手写温度 | 小红书个人号，朋友圈 |
| 朱砂 | `zhusa` | 暗红+朱红+金，大胆冲击 | 强观点、高冲击内容 |
| 青瓷 | `qingci` | 淡青+翠绿，雅致清新 | 生活方式、美学分享 |

---

## 4. Shared Workflow

**所有模式共享 Step 0–4。Step 4 之后分流到各模式的专属流水线。**

### Step 0: Load Preferences + Brand ⛔ BLOCKING

加载顺序（优先级从高到低）：
1. 命令行参数 (`--brand`, `--style`, etc.)
2. 项目级 `EXTEND.md`（当前目录或 `.astra/EXTEND.md`）
3. XDG config: `$XDG_CONFIG_HOME/astra-graphic/EXTEND.md`
4. 用户级: `~/.astra-graphic/EXTEND.md`

加载品牌（见 Section 3.1）。

`--yes` 模式：找不到配置就用默认值，跳过 setup 向导。

### Step 1: Analyze Content → analysis.md

按 `{skill_dir}/references/ai-gen/workflows/analysis-framework.ref` 执行：

1. **内容分类** — article / tutorial / list / opinion / review / news / story
2. **Hook 分析** — 标题吸引力评分 (1-10)，改进建议
3. **目标受众** — 推断读者画像
4. **视觉机会点** — 哪些段落适合可视化、哪些数据适合图表
5. **关键信息提取** — 核心论点、金句、数据点
6. **自动推荐** — mode + strategy + style + layout + mold

保存到 `analysis.md`。

### Step 1.5: Fact-Check + Logic Gap Analysis

**主动检查用户原始内容中的问题：**

1. **事实核查** — 数据、引用、品牌名、价格、日期是否准确？
   - 可验证的声明：标注置信度 (✅ 确认 / ⚠️ 可疑 / ❌ 错误)
   - 不可验证的声明：标注"无法验证"
2. **逻辑漏洞** — 论证链条是否完整？有无跳跃、因果倒置、偷换概念？
3. **信息缺口** — 读者读完会不会有"然后呢？""怎么做？"的疑问？

Output format:
```
📋 内容理解确认
  主题：[topic]
  核心论点：[thesis]
  目标读者：[audience]

⚠️ 事实核查问题（如有）
  - [item]: [issue] → [suggestion]

🔗 逻辑补强建议（如有）
  - [gap]: [suggestion]

❓ 信息缺口（如有）
  - [question readers might have]
```

如果发现 ❌ 级别错误，**必须暂停**，通知用户修正后再继续。
⚠️ 级别：标注但继续。✅ 级别：无需提示。

### Step 2: Smart Confirm ⚠️ REQUIRED

**`--yes` 模式**: 跳过确认，使用 Step 1 的推荐方案直接执行。

**交互模式** — 展示推荐方案：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 内容分析
  主题：[topic] | 类型：[content_type]
  字数：[char_count] | 预估页数：[page_estimate]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎨 推荐方案
  模式：[A/B/C]（[reason]）
  策略：[A/B/C] | 风格：[style] | 布局：[layout]
  品牌：[brand] | 模具：[mold]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 事实核查：[N issues found / all clear]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

提供 3 个选项（AskUserQuestion）：
1. ✅ **确认，直接生成**（推荐）
2. 🎛️ **自定义调整** — 修改 mode/style/layout/brand/mold
3. 📋 **详细模式** — 生成 3 套大纲 → 用户选择

### Step 2.5: Humanize Content 🧹 (Optional)

**Purpose**: 用 humanizer-bilingual 润色，去AI味，加人味。

- **中文处理**：去官腔、去教科书病、去"值得注意的是"、加口语温度、保留专业度
- **英文处理**：去AI高频词 (delve, tapestry, landscape, leverage)、加 voice、varied sentence length
- **双语内容**：分别处理，保持各自语感

Rules:
- 保存润色结果到 `humanized.md`
- 原文 `source.md` 不动
- 如果用户内容本身已经很好（人味足），标注"无需润色"并跳过

### Step 2.6: Draft Confirmation ⚠️ BLOCKING

- 显示润色前后对比（diff 高亮关键变化）
- 用户满意 → 进入 Step 3
- 用户不满意 → 根据反馈修改 → 再次展示 → 循环
- **未确认前绝不进入 Step 3**
- `--yes` 模式：自动确认润色结果

### Step 3: Generate Outline

基于 `analysis.md` + `humanized.md`（定稿后文案），生成大纲。

三种策略可选：
- **Strategy A (Story-Driven)** — 叙事驱动，hook → conflict → insight → resolution
- **Strategy B (Information-Dense)** — 信息密集，模块化，每页一个核心点
- **Strategy C (Visual-First)** — 视觉优先，大图+少文字，冲击力导向

大纲包含：
- 每页的标题、核心内容、视觉方向
- 文字量估算（chars per page）
- Mode A 页面的 prompt 方向
- Mode B 页面的排版提示

保存到 `outline.md`。

### Step 4: Confirm Outline + Mode + Style

展示大纲概览，确认后分流：
- **Mode A** → Section 5
- **Mode B** → Section 6
- **Mode C** → Section 7

---

## 5. Mode A — AI Image Generation

### 5.1 Style Gallery (20 Styles)

| # | Style | Slug | Look | Best For |
|---|-------|------|------|----------|
| 1 | 甜美可爱 | `cute` | 粉色+爱心+贴纸 | 生活方式、美妆 |
| 2 | 清新自然 | `fresh` | 薄荷绿+天蓝+叶子 | 健康、有机 |
| 3 | 温暖亲切 | `warm` | 橙色+奶油色+阳光 | 个人故事 |
| 4 | 高冲击力 | `bold` | 红橙黑+箭头+感叹号 | 避坑、重要提醒 |
| 5 | 极简高级 | `minimal` | 黑白+单色强调 | 专业内容 |
| 6 | 复古怀旧 | `retro` | 半色调+复古徽章 | 经典盘点 |
| 7 | 活力四射 | `pop` | 多彩+气泡+彩纸 | 趣味冷知识 |
| 8 | 知性线条 | `notion` | 极简线条+涂鸦 | 知识卡片 |
| 9 | 粉笔黑板 | `chalkboard` | 彩色粉笔+黑板 | 教程 |
| 10 | 手写笔记 | `study-notes` | 蓝笔+红批注+黄高亮 | 学习笔记 |
| 11 | 丝网海报 | `screen-print` | 半色调+扁平色块 | 观点文、影评 |
| 12 | 墨金定制 | `tuisheng` | 暗色+金/青+学术+赛博 | 墨金社群内容 |
| 13 | 可爱卡通 | `kawaii` | Q版角色+彩虹+贴纸 | 日系可爱 |
| 14 | 像素艺术 | `pixel-art` | 8-bit 像素+复古游戏 | 游戏、怀旧 |
| 15 | 黏土动画 | `claymation` | 3D黏土+柔光+手工感 | 产品、创意 |
| 16 | 折纸 | `origami` | 几何纸折+白底+彩纸 | 日式美学 |
| 17 | 赛博霓虹 | `cyberpunk-neon` | 霓虹粉蓝紫+全息+故障 | 科技、未来 |
| 18 | 绘本水彩 | `storybook-watercolor` | 水彩晕染+柔和笔触 | 文艺、童话 |
| 19 | 宜家说明书 | `ikea-manual` | 扁平线稿+蓝黄配色 | 教程、步骤 |
| 20 | 莫兰迪日记 | `morandi-journal` | 灰粉+鼠尾草绿+低饱和 | 高级感、日记 |

### 5.2 Layout Gallery (8 Layouts)

| # | Layout | Slug | Structure | Best For |
|---|--------|------|-----------|----------|
| 1 | 中心标题 | `center-title` | 大标题居中+副标题+底部信息 | 封面 |
| 2 | 左右分栏 | `split` | 左文右图或左图右文 | 对比、产品 |
| 3 | 上图下文 | `top-image` | 60%图+40%文字 | 场景+说明 |
| 4 | 网格 | `grid` | 2×2 或 3×3 网格 | 多项列表 |
| 5 | 时间线 | `timeline` | 纵向时间轴+节点 | 流程、历史 |
| 6 | 数据仪表盘 | `dashboard` | 数字+图表+指标 | 数据展示 |
| 7 | 引用卡 | `quote` | 大引号+金句+署名 | 金句、观点 |
| 8 | 全出血 | `full-bleed` | 全幅背景图+叠加文字 | 封面、海报 |

### 5.3 Infographic Layouts & Styles (信息图模式)

当内容适合高密度信息可视化时，使用 infographic 引擎（23 布局 × 20 风格）。

**21 种信息图布局**：

| Layout | Best For |
|--------|----------|
| `bento-grid` | 多主题概览（默认） |
| `linear-progression` | 时间线、流程、教程 |
| `binary-comparison` | A vs B、优缺点 |
| `comparison-matrix` | 多维度对比 |
| `hierarchical-layers` | 金字塔、优先级 |
| `tree-branching` | 分类、知识树 |
| `hub-spoke` | 中心概念 + 关联项 |
| `structural-breakdown` | 分解图、解剖图 |
| `iceberg` | 表象 vs 深层 |
| `bridge` | 问题 → 解决方案 |
| `funnel` | 转化漏斗、筛选 |
| `isometric-map` | 空间关系 |
| `dashboard` | 指标、KPI |
| `periodic-table` | 分类集合 |
| `comic-strip` | 叙事、步骤序列 |
| `story-mountain` | 情节结构、张力弧 |
| `jigsaw` | 互相关联的部分 |
| `venn-diagram` | 交集概念 |
| `winding-roadmap` | 旅程、里程碑 |
| `circular-flow` | 循环流程 |
| `dense-modules` | 高密度模块、数据指南 |
| `swot-analysis` | SWOT 四象限分析 |
| `radar-chart` | 雷达图/蛛网图对比 |

**20 种信息图风格**：

| Style | Description |
|-------|-------------|
| `craft-handmade` | 手工质感（默认） |
| `aged-academia` | 古典学术 |
| `bold-graphic` | 大胆图形 |
| `chalkboard` | 黑板粉笔 |
| `claymation` | 黏土动画 |
| `corporate-memphis` | 企业孟菲斯 |
| `cyberpunk-neon` | 赛博霓虹 |
| `ikea-manual` | 宜家说明书 |
| `kawaii` | 可爱卡通 |
| `knolling` | 整齐排列 |
| `lego-brick` | 乐高积木 |
| `morandi-journal` | 莫兰迪日记 |
| `origami` | 折纸 |
| `pixel-art` | 像素艺术 |
| `pop-laboratory` | 波普实验室 |
| `retro-pop-grid` | 复古波普网格 |
| `storybook-watercolor` | 绘本水彩 |
| `subway-map` | 地铁路线图 |
| `technical-schematic` | 技术原理图 |
| `ui-wireframe` | UI 线框 |

Reference: `{skill_dir}/references/ai-gen/infographic-layouts/` + `{skill_dir}/references/ai-gen/infographic-styles/`

**路由规则**：xhs-images 的 12 风格 × 8 布局用于小红书卡片系列，infographic 的 23 布局 × 20 风格用于单张高密度信息图。AI 根据内容自动选择。

### 5.4 Preset Gallery

23+ 预设快捷方式，每个预设 = style + layout + 特定提示词组合。

Reference: `{skill_dir}/references/ai-gen/style-presets.ref`

常用预设：

| Preset | Style | Layout | Use Case |
|--------|-------|--------|----------|
| `knowledge-card` | notion | center-title | 知识点卡片 |
| `data-story` | academic | dashboard | 数据故事 |
| `quote-poster` | magazine | quote | 金句海报 |
| `tech-breakdown` | cyberpunk | grid | 技术拆解 |
| `warm-share` | paper-warm | top-image | 个人分享 |
| `tuisheng-cover` | tuisheng | full-bleed | 墨金封面 |

### 5.5 Generation Process

1. **Image 1 (cover)**: Generate without `--ref`，建立视觉基调
2. **Images 2+**: Generate with `--ref <image-01>`，确保视觉一致性
3. **Session ID**: `social-{slug}-{timestamp}`，同 session 所有图片共享

Generation per image:
```
1. Assemble prompt from: outline + style definition + layout template + brand constraints
2. Add text overlay instructions (exact text, position, size)
3. Send to Gemini image generation
4. Validate output: text legibility, layout compliance, color accuracy
5. If validation fails → adjust prompt → retry (max 2 retries)
6. Save to output directory with sequential naming
```

### 5.6 Brand Color Injection

Read `{skill_dir}/brands/{brand}/ai-style.md` → extract:
- **Color constraints**: "use #1A1A2E as background, #D4A520 as accent"
- **Negative prompts**: "avoid bright colors, no cartoon style"
- **Texture keywords**: "add film grain, matte finish"

Inject into Gemini prompt as hard constraints (placed before content-specific instructions).

### 5.7 Multi-Panel Stitch Mode

当风格为 tuisheng 或文字密度高时，自动切换到拼接模式：

1. 生成 3 张横向面板 (3:2 比例) 而非 1 张竖向图 (3:4)
2. 每张面板承载 ~1/3 内容 → 文字更清晰
3. 拼接命令：
```bash
convert panel-1.png panel-2.png panel-3.png -append combined.png
```

Auto-detection rules:
- `tuisheng` style → 默认启用拼接
- Other styles → 仅当 total text > 100 chars 时启用
- 可通过 `--no-stitch` 强制关闭

### 5.8 Image Generation Skill

优先使用 `image-gen` skill（如果可用）。Fallback 到 `nano-banana-pro`。

所有图片使用相同 Session ID，确保风格一致。

#### Model Selection（模型路由）

| 场景 | 模型 | 原因 |
|------|------|------|
| 封面、概念图、氛围图（无文字） | `gemini-3-pro-image-preview` (Pro) | 视觉冲击力强，画面质量高 |
| 金色粒子/暗黑概念艺术（无文字） | `gemini-3-pro-image-preview` (Pro) | 粒子效果、发光边缘 Pro 远胜 Flash |
| 三段拼接 panel（少量文字） | `gemini-3-pro-image-preview` (Pro) | 每 panel 文字量少，Pro 冲击力更强 |
| 中文信息图/知识卡（有文字） | `gemini-3.1-flash-image-preview` (Flash) | 中文渲染精准，Pro 中文会乱码 |
| 英文信息图（有文字） | 两者皆可，Pro 优先 | 英文渲染两个模型都稳定 |

**自动判断规则**：
- 图中无文字（概念艺术、氛围底图）→ Pro
- 图中有中文 → Flash（无论文字多少，Pro 中文不稳定）
- 图中仅英文 → Pro
- `--model` flag 可手动覆盖

#### Chinese Text Enhancement（中文渲染强化）

**Flash 模型生成中文信息图时，必须在 prompt 末尾追加以下指令：**

```
CREATIVE FREEDOM: Be bold and expressive with the visual design — use
unexpected color combinations, playful illustrations, creative icons,
dynamic asymmetric layouts, overlapping elements, decorative details.
Make it visually rich, fun, and full of personality.

CHINESE TEXT QUALITY (apply AFTER creative design is complete):
- All Chinese characters must be correctly formed with proper strokes
- No garbled, merged, or invented characters
- Use clean, bold Chinese font rendering — legible even at small sizes
- If a character cannot render clearly, simplify or omit — never render garbled text
```

**关键原则**：
- 先声明创意自由，再约束文字质量 — 顺序不能反，否则模型会因为怕出错而收缩画面
- 列出内容中所有关键中文术语，让模型 double-check
- 这条指令只对 Flash 生效；Pro 生成的图不含文字，不需要


---

## 6. Mode B — Precision Text Layout

### 6.1 Rendering Pipeline

`render_pages.py` is the **editorial engine** (v8). It renders hairline-rule
magazine layouts — no card-fill boxes — with mono kicker labels, "the larger,
the lighter" type, 20 data/structure blocks, tables, and 14 selectable themes.

```
Markdown
  → Parse blocks: title / subtitle / section / paragraph / callout / callout-gold
       / highlight / list / divider / image / table / 20 chart blocks (see 6.7)
  → Pick theme (--theme, or brand.json text_render.theme)  [see 6.3]
  → Measure every block (Playwright) → bin-pack into 1080×1440 pages
       → overflow rollback + image auto-shrink + orphan-heading guard + vertical centering
  → Playwright screenshot @2x → 1080×1440 PNG per page
```

The engine is a clean reimplementation (original Python + CSS). It was informed
by guizang's editorial *principles* (hairlines over cards, larger-lighter type,
type scale) — design ideas, not code — and copies no guizang HTML/CSS/JS, so it
carries **no AGPL obligation**.

### 6.2 Six Molds

| Mold | Flag | Dimensions | Best For |
|------|------|------------|----------|
| 多卡 (Multi-Card) | `-m` | 1080×1440 per page | 小红书系列卡片 **(DEFAULT)** |
| 长图 (Long Image) | `-l` | 1080×auto | 单张长图，朋友圈 |
| 信息图 (Infograph) | `-i` | 1080×auto | 数据可视化，流程图 |
| 视觉笔记 (Visual Note) | `-v` | 1080×auto | 手绘风格笔记 |
| 漫画 (Comic) | `-c` | 1080×auto | 黑白漫画分格 |
| 白板 (Whiteboard) | `-w` | 1080×auto | 结构化框图，思维导图 |

**Content density levels** (for multi-card mold `-m`):

| Level | 内容量 | 组件 | 典型场景 |
|-------|--------|------|---------|
| **Sparse** | 标题 + 1 句核心金句 | 居中标题、金句、accent bar | 封面页、宣言页 |
| **Light** | 标题 + 段落 + 数据卡 | 标题区、首字下沉段落、2 个数据卡 | 开篇介绍、数据亮点 |
| **Balanced** | 标题 + 数据卡 + 引用 | 标题区、2 个数据卡、callout | 要点展示、带引用 |
| **Medium** | 数据卡 + 对比表 + 引用 | 数据卡、对比表、金句高亮 | 对比分析、中等信息量 |
| **Dense** | 全量内容刚好填满一页 | 数据卡+对比表+段落+行动清单+结语 | 知识密集、行动导向 |
| **Ultra** | 极致密度，字号更小 | 4列数据+5行对比+段落+7条行动+结语，REF标签 | 数据手册、完整指南 |

AI 根据内容量自动选择密度。Dense 必须内容填满，不靠间距凑。

Auto-selection (when no `--mold` specified):
- 小红书系列内容 → `-m` (multi-card)
- 单张知识卡片 → `-l` (long)
- 数据密集型内容 → `-i` (infograph)
- 教程/步骤类 → `-v` (visual note) or `-w` (whiteboard)
- 故事/对话类 → `-c` (comic)

### 6.3 Themes (Mode B color/font skins)

Each page is rendered in one **theme** — a palette + font pairing. Pass `--theme <key>`;
if omitted, the engine reads the brand's default from `brand.json → text_render.theme`
(set per the brand→theme map below), else falls back to `mono` (classic black-on-white).
Default author / watermark / signature is **Astra Lune** (override with `--author` / `--watermark`).

14 themes (`--theme` keys):

| Group | Keys |
|-------|------|
| 黑白 | `mono` 经典黑白 · `mono-dark` 反相黑白 |
| 暖浅 | `morandi` 灰粉 · `nuanhe` 米白赭石 · `zhusa` 朱砂红 · `kraft` 牛皮赭 · `ouhe` 藕荷紫 |
| 冷浅 | `klein-serif` 蓝白 · `qingci` 青瓷(楷体) · `moink` 玄青 · `daiqing` 黛青(小薇) |
| 深色 | `forest` 墨绿 · `midnight` 墨蓝鎏金 · `mojin` 深黑鎏金 |

Fonts: 宋体 (Noto Serif SC) for most; 楷体 (LXGW WenKai) for `qingci`; 小薇 (ZCOOL XiaoWei) for `daiqing`.

**Brand → default theme** (in each `brand.json`):
`mojin→mojin` · `nuanhe→nuanhe` · `qingci→qingci` · `zhusa→zhusa` · `suqi→klein-serif`.
A theme (Mode B layout skin) is distinct from a brand (Mode A AI-gen identity) even when names coincide.

> Legacy keyword-based **tone detection** (strategic/tech/philosophical/literary → accent color)
> no longer drives `render_pages.py`; themes supply the full palette. The old tone logic
> survives only in `render_single.py` and `render_pages_legacy.py`.

### 6.4 Typography Rules

> **Editorial engine (v8) actuals — these override the legacy numbers below.**
> Body para 29px / line-height 1.74 · section headline 37px weight 600 + 18px mono kicker
> · dropcap 92px (first para, accent) · title 54px weight 600. "The larger, the lighter":
> giant numbers render at weight 400, small mono labels at 500–600. Page fill uses measured
> `center_offset` (short pages vertically centered) — not `flex justify-content`. The density
> guidance below is still conceptually useful, but the hard px values are superseded.

**Body text**: ≥ 38px (mobile readable, non-negotiable)

**Dropcap**: First page, first paragraph only
- Size: 128px
- Color: tone accent color
- Font: brand heading font
- Span: 3 lines of body text

**Golden sentence auto-highlight**:
- Detection: standalone sentence ≤ 25 characters, not a heading
- Style: gold left border (4px) + faint background (accent color at 8% opacity)
- Max 2 per page to avoid over-decoration

**Overflow protection** (critical for multi-card):
1. **Measure**: Calculate rendered height of all content blocks
2. **Bin**: Distribute blocks across pages with 1440px budget per page
3. **Verify**: Playwright renders → check actual height
4. **Rollback**: If overflow detected → re-bin with tighter budget → re-render

**Page fill rules** (critical — no empty bottom space):

每张 1080×1440 卡片必须看起来「刚好填满」，不能有明显的底部空白。根据内容密度选择不同策略：

| 密度 | 内容量 | CSS 策略 | 如果还有空白 |
|------|--------|---------|-------------|
| **Sparse** | 标题 + 1 句金句 | `justify-content: center` 垂直居中 | 留白是设计意图 |
| **Light** | 标题 + 段落 + 数据卡 | `justify-content: center` 垂直居中 | 自然间距 |
| **Balanced** | 标题 + 数据卡 + 引用 | `justify-content: center` 垂直居中 | 组件间距均匀 |
| **Medium** | 数据卡 + 对比表 + 引用 | `justify-content: center` 垂直居中 | 间距微调即可 |
| **Dense** | 全量内容填满整页 | `justify-content: space-between` | **必须增加内容量直到填满** |
| **Ultra** | 极致密度，字号缩小 | `justify-content: space-between` | **必须增加内容量 + 数据点** |

**Dense 模式的核心原则**：
- Dense = 内容量本身就该多到刚好撑满 1440px
- 如果 Dense 内容仍有底部空白 → **增加内容**（多加 1-2 条行动项、多加一段洞察、多加一个数据点）
- 绝不靠增大 padding/margin 来「凑满」— 那是假 dense
- 用 `justify-content: space-between` 只是兜底，不是主要手段

**通用规则**：
- 所有密度的 `.content` 容器都必须是 `display: flex; flex-direction: column`
- Footer 紧贴底部（`margin-top: auto`）
- 渲染后目视检查：底部空白不超过 footer 上方 40px

Reference: `{skill_dir}/references/text-render/typography.ref`

### 6.5 AI Images in Text Layout (Optional)

Mode B can embed AI-generated concept images inline:

1. Identify key sections that benefit from visual metaphor
2. Use Mode A engine to generate concept art (same brand constraints)
3. Insert into Markdown as `![metaphor description](path/to/generated.png)`
4. `render_pages.py` embeds images as base64 → renders inline in HTML
5. Image sizing: max 60% page width, centered, with 16px margin

This is **optional** and only triggered when:
- User requests it explicitly
- Analysis identifies high-impact visual opportunities
- `--no-inline-images` to disable

### 6.6 Rendering Commands

**Multi-card (default for Mode B):**
```bash
python3 {skill_dir}/scripts/render_pages.py \
  --input humanized.md \
  --output ./pages/ \
  --theme {brand.text_render.theme} \   # or any key from 6.3; omit → brand default → morandi
  --avatar {skill_dir}/brands/{brand}/avatars/avatar.jpg \
  --author "Author Name" \
  --date "2026-04-06" \
  --tags "Tag1 × Tag2" \
  --watermark "Brand"
  # optional: --background texture.png (subtle paper grain) · --no-author · --no-signature
```

**Single long image:**
```bash
python3 {skill_dir}/scripts/render_single.py \
  --input humanized.md \
  --output ./output/ \
  --mold long \
  --background {skill_dir}/brands/{brand}/backgrounds/texture.png \
  --avatar {skill_dir}/brands/{brand}/avatars/avatar.jpg \
  --author "Author Name"
```

**Playwright capture (for content-card molds):**
```bash
node {skill_dir}/scripts/capture.js <html-file> <output-png> 1080 1440
```

**Infograph / Visual Note / Comic / Whiteboard:**
```bash
python3 {skill_dir}/scripts/render_single.py \
  --input humanized.md \
  --output ./output/ \
  --mold [infograph|visual-note|comic|whiteboard]
```

### 6.7 Structure Blocks (charts & tables)

Beyond prose, the editorial engine renders **20 data/structure blocks** + Markdown tables.
Each block is a fenced code region: ` ```<kind> [optional title] ` … rows … ` ``` `.
All are CSS-only (no chart lib), data-bound, and themed. Use them to raise information density.

| Kind | Row syntax | Renders |
|------|-----------|---------|
| `bar` | `标签,数值` | 横向条形 + 比例细轨 |
| `kpi` | `标签,数值` (2) | 双栏大数字 + 中线 |
| `hero` | `数字\|说明` | 巨号大数字 |
| `statrow` | `数值,标签` | 横排统计（数值大、标签小） |
| `progress` | `标签,百分比` | 进度条（细轨） |
| `donut` | `标签,百分比` | 环形图（conic-gradient） |
| `gauge` | `标签,百分比` (1) | 半圆仪表 |
| `funnel` | `阶段,数值` | 漏斗（逐级收窄） |
| `pyramid` | 每行一层 | 金字塔（逐层加宽） |
| `ranking` | `名称,分数` | 排行榜（前 3 强调） |
| `matrix` | 每行一项，`*`前缀=强调 | 编号网格（细线） |
| `quadrant` | 4 行 = 4 格 | 四象限（细线，第1格强调） |
| `compare` | `标题\|要点;要点;…` (2) | 对比双栏（中线分隔） |
| `cards` | `标题\|描述` | 信息卡（顶部 accent 细线） |
| `steps` | `标题\|描述` | 步骤流水（编号细线行） |
| `timeline` | `时间,事件` | 时间线（圆点 + 竖线） |
| `checklist` | `x 完成` / `- 待办` | 清单（✓/○ 细线行） |
| `tags` | 逗号分隔，`*`前缀=强调 | 标签云（描边胶囊） |
| `notice` | `info\|文` / `warn\|文` / `ok\|文` | 提示条（左 accent 竖条） |
| `quote` | 第1行正文，第2行 `— 出处` | 金句卡（悬挂引号） |

Markdown tables (`| … |` + `|---|`) render in the theme's table style (already approved).

Example:
````
### 验证数据 metrics
```bar
可复现性,95
离线能力,90
上手成本,30
```
````

Inline: `**强调**` → accent bold · `^^次强调^^` → secondary color.
Section headers `### 中文 english` auto-split into a serif Chinese headline + a mono uppercase kicker.

---

## 7. Mode C — Hybrid

### 7.1 Structure

| Page | Mode | Engine | Why |
|------|------|--------|-----|
| Cover (P1) | A | Gemini AI | 视觉冲击力，抓眼球 |
| Content (P2–Pn) | B | HTML/Playwright | 精确排版，文字可读 |
| Ending (last) | A or B | Depends | A = 视觉收尾; B = CTA 文字 |

Decision for ending page:
- If ending has call-to-action text → Mode B
- If ending is a visual summary/mood → Mode A
- Default: Mode A (visual closure)

### 7.2 Color Consistency Rules

**This is the core value of Mode C** — unified visual language across AI and HTML pages.

- Brand colors used for **BOTH** AI generation **AND** HTML rendering
- AI cover: `brands/{brand}/ai-style.md` color constraints → Gemini prompt
- Text pages: `brands/{brand}/base.css` → matching CSS variables
- Tone detection colors are also aligned with brand palette
- Result: 翻页时颜色不跳，从封面到正文到结尾是一体的

### 7.3 Image Embedding Techniques (10 种嵌入技法)

Mode C 的核心能力是把 AI 生成的概念图无缝嵌入 HTML 精排版卡片。所有图片转 base64 内嵌，Playwright 截图完美渲染。

| # | 技法 | CSS/HTML | 适用场景 |
|---|------|---------|---------|
| 1 | **Hero 大图** | `background-image` + gradient overlay | 封面页、Banner |
| 2 | **内联配图** | Grid `260px 1fr` 图左文右 | 图文并排、产品介绍 |
| 3 | **全页底图** | `opacity: 0.15` + dark gradient | 氛围页、品牌宣言 |
| 4 | **异形裁切** | `clip-path: circle/polygon` | 头像、创意排版 |
| 5 | **图片网格** | CSS Grid 非对称布局 | 作品集、多图展示 |
| 6 | **CSS 滤镜** | `grayscale/sepia/contrast/blur` | 情绪渲染、背景虚化 |
| 7 | **文字叠加** | `filter: brightness(0.4)` + text | 封面图、引言卡 |
| 8 | **渐变边框** | `padding` + gradient bg + `box-shadow` | 焦点展示、人物特写 |
| 9 | **圆形头像** | `border-radius: 50%` + ring border | 作者介绍、用户证言 |
| 10 | **浮动卡片** | `transform: rotate(-2deg)` + shadow | 笔记风格、手账排版 |

**图片路径规则**：
- 所有图片必须转 base64 data URI 内嵌（Playwright 不支持外部 file://）
- AI 生成的概念图路径用 `{output_dir}/` 引用
- 品牌头像/logo 路径用 `{brand_dir}/` 引用

### 7.4 Workflow

1. Generate outline with page-level mode assignments (from Step 3)
2. Render Mode A pages first (cover + any visual pages)
3. Extract dominant colors from AI output → verify against brand palette
4. Render Mode B pages with brand CSS (already aligned)
5. Assemble final sequence with consistent file naming

### 7.4 File Naming

```
output/
├── 01-cover-[slug].png          # Mode A generated
├── 02-content-[slug].png        # Mode B rendered
├── 03-content-[slug].png        # Mode B rendered
├── 04-content-[slug].png        # Mode B rendered
├── ...
└── NN-ending-[slug].png         # Mode A or B
```

Sequential numbering ensures correct order on all platforms.

---

## 8. Output + Delivery

### 8.1 Output Directory Structure

```
{output_root}/astra-graphic/{topic-slug}/
├── source.md                    # Original content (untouched)
├── humanized.md                 # Humanized draft (if modified)
├── analysis.md                  # Content analysis results
├── outline.md                   # Selected outline
├── prompts/                     # AI generation prompts (Mode A/C only)
│   ├── 01-cover-[slug].md
│   ├── 02-[slug].md
│   └── ...
├── 01-cover-[slug].png          # Final output images
├── 02-content-[slug].png
├── 03-content-[slug].png
└── ...
```

`{output_root}` defaults to current working directory. Override with `--output`.

### 8.2 Completion Report

生成完成后输出：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Astra Social Complete!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Topic:    [topic]
  Mode:     [A/B/C] ([mode name])
  Brand:    [brand]
  Strategy: [A/B/C] ([strategy name])
  Style:    [style] | Layout: [layout]
  Mold:     [mold] (Mode B only)
  Images:   N total
  Location: [absolute path]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 8.3 Image Modification

生成后的修改操作：

| Action | Steps |
|--------|-------|
| **Edit single image** | 1. Update prompt (Mode A) or markdown section (Mode B) → 2. Regenerate that image only → 3. Replace in output |
| **Add image** | 1. Specify insertion position → 2. Create prompt/content → 3. Generate → 4. Renumber all subsequent files |
| **Delete image** | 1. Remove file → 2. Renumber remaining → 3. Update outline.md |
| **Regenerate all** | 1. Re-run from Step 4 with same outline → 2. Overwrite output |
| **Change style** | 1. Update style → 2. Regenerate all Mode A images → 3. Mode B unaffected unless brand changes |

---

## 9. Reference Index

### AI Generation References
- `{skill_dir}/references/ai-gen/presets/` — 12 style definition files
- `{skill_dir}/references/ai-gen/elements/canvas.ref` — canvas sizing, aspect ratios
- `{skill_dir}/references/ai-gen/elements/decorations.ref` — borders, corners, badges
- `{skill_dir}/references/ai-gen/elements/image-effects.ref` — grain, blur, glow
- `{skill_dir}/references/ai-gen/elements/typography.ref` — AI text rendering rules
- `{skill_dir}/references/ai-gen/workflows/analysis-framework.ref` — content analysis
- `{skill_dir}/references/ai-gen/workflows/outline-strategies.ref` — 3 outline strategies
- `{skill_dir}/references/ai-gen/workflows/prompt-assembly.ref` — prompt construction
- `{skill_dir}/references/ai-gen/style-presets.ref` — 23+ preset definitions

### Text Rendering References
- `{skill_dir}/references/text-render/engine.ref` — Playwright rendering pipeline
- `{skill_dir}/references/text-render/tone-detection.ref` — tone scoring + color mapping
- `{skill_dir}/references/text-render/typography.ref` — font sizes, dropcap, golden sentences, overflow

### Quality
- `{skill_dir}/references/taste.ref` — Anti-AI-slop quality gates, visual taste rules

### Config
- `{skill_dir}/references/config/first-time-setup.ref` — Brand setup wizard flow
- `{skill_dir}/references/config/preferences-schema.ref` — EXTEND.ref schema definition

### Brands
- `{skill_dir}/brands/{brand}/brand.json` — Visual identity config
- `{skill_dir}/brands/{brand}/base.css` — HTML rendering styles
- `{skill_dir}/brands/{brand}/ai-style.md` — AI generation color/style constraints
- `{skill_dir}/brands/{brand}/avatars/` — Avatar images
- `{skill_dir}/brands/{brand}/backgrounds/` — Background textures

---

## Notes

- **Portable paths**: Always use `{skill_dir}` prefix for file references within this skill
- **Image generation**: Prefer `image-gen` skill; fallback to `nano-banana-pro`
- **Environment**: `GEMINI_API_KEY` required for Mode A and Mode C
- **Playwright**: Required for Mode B; depends on content-card `node_modules`
- **ImageMagick**: Required for multi-panel stitch (`convert` command)
- **Font loading**: Ensure CJK fonts (Noto Sans CJK, LXGW WenKai) are installed on render host
- **Output size**: Target ≤ 500KB per PNG for social platform upload limits
