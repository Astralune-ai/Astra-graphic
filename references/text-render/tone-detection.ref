# Tone Detection Rules

> Automatic content tone classification for CSS variable injection.

## Tone Categories

| Tone | Accent | Secondary | Vibe |
|------|--------|-----------|------|
| `strategic` | `#D4A520` gold | `#2D6A4F` forest green | Business, growth, market analysis |
| `tech` | `#40B8B8` teal | `#3D5A80` steel blue | Engineering, AI, systems, code |
| `philosophical` | `#C4A55A` warm gold | `#8B5E3C` coffee brown | Cognition, first principles, meaning |
| `literary` | `#C08050` ochre | `#6B4E3D` deep umber | Narrative, writing craft, metaphor |

---

## Keyword Lists

### strategic

```
战略, 投资, 市场, 增长, ROI, 商业模式, 竞争, 壁垒, 利润, 营收,
融资, 估值, 赛道, 红利, 复利, 杠杆, 资产, 负债, 现金流, 客户,
定价, 渠道, 转化率, 留存, LTV, CAC, PMF, GTM, 护城河, 飞轮,
strategy, investment, market, growth, revenue, profit, valuation,
competitive, moat, leverage, scale, acquisition, retention, runway
```

### tech

```
架构, AI, 代码, 算法, 系统, API, 部署, 数据库, 框架, 模型,
训练, 推理, 微调, RAG, 向量, 嵌入, Token, GPU, 分布式, 微服务,
容器, Kubernetes, Docker, CI/CD, 延迟, 吞吐, 并发, 缓存, 索引,
architecture, algorithm, deploy, database, framework, model, training,
inference, fine-tune, embedding, distributed, container, latency,
throughput, pipeline, infrastructure, backend, frontend, DevOps
```

### philosophical

```
认知, 思维, 本质, 悖论, 第一性原理, 元认知, 心智模型, 范式,
存在, 意义, 自由意志, 意识, 涌现, 复杂性, 还原论, 整体论,
认识论, 方法论, 世界观, 底层逻辑, 反直觉, 非线性, 涌现,
cognition, paradigm, first-principles, emergence, complexity,
consciousness, epistemology, ontology, dialectic, reductionism,
mental-model, meta-cognition, non-linear, counterintuitive
```

### literary

```
故事, 写作, 文字, 叙事, 隐喻, 意象, 修辞, 散文, 诗意, 韵律,
小说, 人物, 场景, 对白, 伏笔, 转折, 结构, 节奏, 留白, 张力,
读者, 共鸣, 情绪, 温度, 质感, 画面感, 氛围,
narrative, metaphor, prose, imagery, rhetoric, voice, tone,
character, scene, dialogue, foreshadowing, tension, rhythm,
resonance, texture, atmosphere, literary, storytelling
```

---

## Weighted Counting Algorithm

Not boolean — uses weighted keyword hits:

```python
scores = {tone: 0 for tone in TONES}

for tone, keywords in KEYWORD_LISTS.items():
    for keyword in keywords:
        count = content.lower().count(keyword.lower())
        if count > 0:
            scores[tone] += min(count, 3)  # Cap at 3 per keyword
            # Prevents one repeated word from dominating

# Title keywords get 2x weight
for tone, keywords in KEYWORD_LISTS.items():
    for keyword in keywords:
        if keyword.lower() in title.lower():
            scores[tone] += 2
```

### Minimum Threshold

- A tone must score **≥ 3 keyword hits** to activate
- If no tone reaches threshold → use **default** colors

### Winner Selection

```python
winning_tone = max(scores, key=scores.get)
if scores[winning_tone] < 3:
    winning_tone = "default"
```

### Default Fallback

When no tone matches (score < 3 for all):
- Use brand's primary accent color as `--tone-accent`
- Use brand's secondary color as `--tone-secondary`
- If no brand loaded: `--tone-accent: #D4A520`, `--tone-secondary: #40B8B8`

---

## CSS Variable Injection

Detected tone maps to CSS variables injected into the HTML template:

```css
/* strategic */
:root { --tone-accent: #D4A520; --tone-secondary: #2D6A4F; }

/* tech */
:root { --tone-accent: #40B8B8; --tone-secondary: #3D5A80; }

/* philosophical */
:root { --tone-accent: #C4A55A; --tone-secondary: #8B5E3C; }

/* literary */
:root { --tone-accent: #C08050; --tone-secondary: #6B4E3D; }
```

These variables are used throughout the template:
- `.gold` (bold text) → `color: var(--tone-accent)`
- `.teal` (highlight) → `color: var(--tone-secondary)`
- `.highlight` border → `border-left: 4px solid var(--tone-accent)`
- `.highlight` bg → `background: var(--tone-accent) at 6% opacity`
- Dropcap color → `var(--tone-accent)`

---

## Brand Override

When `brand.json` includes `tone_variants`:

```json
{
  "ai_style": {
    "tone_variants": ["strategic", "tech"]
  }
}
```

- Only listed tones are available for that brand
- If detected tone is not in the list → fall back to first listed tone
- If `tone_variants` is null/missing → all tones available

This prevents a tech brand from accidentally rendering in literary ochre tones.

---

*Reference for: SKILL.md Section 6.3 — Tone Detection*
