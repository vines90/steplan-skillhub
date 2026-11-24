---
name: steplan-poster
description: 阶梯计划（Steplan）品牌海报生成。按 Steplan VI（深空黑 #16171C、骨白、酸性绿 #C8FF2E，得意黑 / 思源黑体 / Unbounded，品牌字体随技能打包）把文案渲染成高清 PNG。内置模板：课程海报（长图 + 9:16，含课程大纲、讲师、价格、报名二维码，可由报名链接自动生成二维码）、训练营 / 活动招生、产品推广（sohobot、Step 1 等）、金句 / 数据观点、封面图（公众号封面 2.35:1 + 次图 1:1 + 小红书封面 3:4）；尺寸 9:16 竖版与小红书 3:4。当用户说「做一张阶梯计划海报」「训练营 / 课程海报」「直播预告海报」「产品海报」「金句海报」「公众号封面」「小红书封面」「按我们品牌出图」时使用。
---

# Steplan 海报

文案 → `poster.json`（模板 + 字段）→ 脚本用本机 Chrome 渲染出 PNG。版式、字体、配色、自动缩字都由脚本保证，Claude 只负责选模板、整理文案。

技能目录：`~/.claude/skills/steplan-poster/`（下文的 `references/`、`assets/`、`scripts/` 都相对于它）。

## 流程

1. **收集文案**。缺关键信息就问用户：课程海报要大纲、讲师、时间、价格、报名链接或二维码图片；产品海报要网址与卖点。
2. **选模板**：

   | template | 用途 | 输出 |
   |---|---|---|
   | course | 课程 / 训练营（大纲、讲师、报名二维码） | 长图 + 9:16 |
   | camp | 活动 / 直播 / 简版招生 | 9:16 + 3:4 |
   | product | 产品推广 | 9:16 + 3:4 |
   | quote | 金句、观点、数据卡 | 9:16 + 3:4 |
   | cover | 公众号封面 + 次图 + 小红书封面 | 三张 |

3. **写 poster.json**：先读 `references/templates.md`（字段、长度建议），再复制 `assets/examples/` 里同模板的范例改内容。默认存到当前目录的 `海报/YYYYMMDD-短标题/poster.json`。
4. **渲染**：

   ```bash
   python3 ~/.claude/skills/steplan-poster/scripts/steplan_poster.py render 海报/…/poster.json
   ```

   默认 2 倍分辨率（9:16 出 2160×3840）。有 ⚠ 提示（放不下、已缩到最小字号）就精简文案或去掉可选块，再渲染。
5. **看图验收**：长图按 2000px 切片看。检查标题断行、卡片内文字是否挤、二维码是否完整。
6. **交付**：给出 PNG 路径；提醒替换占位内容（讲师、价格 X,XXX、示例二维码链接）。

## 规则

- **不编造**：讲师经历、价格、数据、名额只用用户给的；没有就用明显占位并告诉用户。
- **二维码**：课程海报用 `signup.qr`（图片路径）或 `signup.qr_url`（报名链接，自动生成）；没给就是占位框，交付时提醒。公众号文章模板不放二维码，海报可以放。
- **品牌固定项**：页脚左「● STEPLAN 阶梯计划」、右「steplan.ai」由脚本加，不要重复写；酸性绿只做色块或深色底上的强调。
- **标记**：`[[反白色块]]` 用在标题最想强调的短语上，每张最多一两处；`\n` 控制大标题断行，每行约 6–9 个字。

## 扩展

新增模板：在 `scripts/steplan_poster.py` 里写 `模板函数(spec, size, theme) → (body_html, css, style)` 并登记到 `TEMPLATES`。可伸缩的文字加 `data-fit="最小字号"`；装饰图用 `tex()` 放进裁切图层，避免被误判为溢出。

## 模板总览

阶梯计划项目里的 `海报模板/` 是全部范例的出图和总览：

```bash
python3 ~/.claude/skills/steplan-poster/scripts/steplan_poster.py render ~/.claude/skills/steplan-poster/assets/examples/*.json -o 海报模板
```
