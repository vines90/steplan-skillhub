---
name: steplan-brand
description: 阶梯计划（Steplan）品牌视觉规范与资源包。含标志（全部 SVG / PNG / favicon、概念、安全空间、最小尺寸、正误用法）、色彩（深空黑 #16171C / 骨白 #F4F5F0 / 石墨灰 #8A8D94 / 酸性绿 #C8FF2E 及占比、扩展中性色）、字体（Unbounded、得意黑、思源黑体、JetBrains Mono，及 PowerPoint / Keynote / WPS / 网页里的字体名与回退坑）、图形元素（圆点、三横杠、阶梯、阶段胶囊、点阵插图）、版式规则、品牌文案与产品口径；附 tokens.css / tokens.json、PPT 模板、标志导出脚本。做任何阶梯计划 / Steplan 的设计或物料（网页、PPT、海报、名片、视频、周边、文档、头像、邮件签名）之前先用它；用户问「品牌色 / 字体 / logo 怎么用」「给我一个 XX 尺寸的 logo」「这个设计符不符合品牌规范」时使用。
---

# 阶梯计划 · 品牌视觉规范

定稿：方案四 v2「跃迁 Leap」· 配色 E「深空黑」（2026-10-30）。已拍板，不再提新方向、新配色；改标志几何前先问用户。

技能目录：`~/.claude/skills/steplan-brand/`（下文路径都相对于它）。看图核对用 `assets/brand-kit/VI展示板.png` 和 `assets/brand-kit/使用规范.png`。

## 一页速查

- **品牌**：阶梯计划 / Steplan（中英一个品牌，不拆子品牌）。slogan「只带最核心的，去最远的地方。」/ Send only what matters.　官网 steplan.ai
- **四色**：深空黑 #16171C（46%）· 骨白 #F4F5F0（28%）· 石墨灰 #8A8D94（14%）· 酸性绿 #C8FF2E（12%）
- **字体**：中文标题 / 大数字 得意黑；英文标识 / 产品名 Unbounded SemiBold 斜 8°；正文 思源黑体；小标签 JetBrains Mono（字距 0.12–0.16em）
- **标志**：主体只用深空黑或白；酸性绿只给圆点。浅底用全黑（圆点也是黑）；深底用白 + 绿点；酸性绿底用全黑
- **元素**：圆点（= 大脑）、三横杠（短 / 中 / 满，表示进度和层级）、逐级升高的卡片（阶梯）、阶段胶囊「第 1 阶 · 已完成」、点阵插图（点阵球逐级推进，飞出酸性绿圆点）
- **禁用**：电光紫 #5B2EFF 等其他品牌色；浅底上的绿色文字或绿点；拉伸、旋转、改倾角

## 按需阅读

| 要做的事 | 读 |
|---|---|
| 用标志、导出某个尺寸的 logo、做头像 / favicon | `references/logo.md` |
| 配色、深浅底搭配、印刷色 | `references/color.md` |
| 选字体、在 Office / Keynote / WPS / 网页里设置字体 | `references/typography.md` |
| 画图形元素（圆点、横杠、阶梯、胶囊、插图） | `references/elements.md` |
| 写品牌文案、产品介绍、各类物料的版式规则 | `references/voice-and-layout.md` |

## 资源

- `assets/brand-kit/`：定稿交付包（`logo/svg`、`logo/png`（@2x 为高清）、`favicon/`、三张规范图、`色值.txt`）
- `assets/fonts/`：Unbounded、得意黑、Noto Sans SC（可变字体，网页用）、思源黑体 CN 常规 / 粗体（静态，Office 用）、JetBrains Mono，均为开源授权
- `assets/tokens.css`、`assets/tokens.json`：颜色、字体、品牌口径的设计变量，网页和脚本直接引用
- `assets/texture/`：点阵插图（透明底，竖版 / 横版）
- `assets/templates/Steplan-PPT模板.pptx`：PPT 模板（11 种版式 + 23 页示例）
- `scripts/logo.py`：导出任意尺寸、任意底色的标志 PNG（带安全空间）

  ```bash
  python3 ~/.claude/skills/steplan-brand/scripts/logo.py export logo-horizontal-reverse --width 1200 --bg '#16171C' --pad 1 -o logo.png
  ```

## 现成的物料技能

公众号文章排版用 **steplan-wechat**，海报和封面图用 **steplan-poster**，PPT 用上面的模板。这些技能已经内置本规范，直接用即可。

## 品牌自查清单

交付任何物料前逐条过一遍：

1. 只用四色和扩展中性色；没有电光紫或其他「品牌色」
2. 酸性绿只做色块、圆点、横杠，或深色底上的强调；浅底上没有绿色文字
3. 整套物料里酸性绿约占 12%；整版绿底（金句页）一套最多一两页
4. 标志用对版本（浅 / 深 / 绿底），四周至少留 1 个圆点直径；没有拉伸、旋转、改色
5. 标志不小于最小尺寸：图形标志高度 ≥ 24px（更小用 mark-small），横版宽度 ≥ 96px / 印刷 20mm
6. 标题用得意黑，正文用思源黑体，英文产品名用 Unbounded 斜 8°；字体真的生效了，没有回退成系统字体
7. 标题区只有一层：不叠「品牌页眉 + 双语小标签 + 标题」；品牌标识放页脚左、steplan.ai 放页脚右
8. 一页 / 一屏只讲一件事；数据、价格、案例都是真的，占位已替换
9. 公众号文章不放二维码；海报可以放报名二维码
10. 导出清晰：屏幕物料按 2 倍分辨率出图
