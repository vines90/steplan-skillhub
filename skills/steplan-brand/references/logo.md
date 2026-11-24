# 标志

## 概念

取自《三体》阶梯计划：探测器太重 → 送一个人，还是太重 → 只送大脑。标志把字母 A 的顶尖摘下，化作独立飞出的**圆点**（只送大脑）；右腿断成**三级横杠**，把它一级级推向远方；整体**前倾 8°**。品牌要表达：极致效率、想象力、决心。

演进过程见 `assets/brand-kit/演进_原稿-v1-v2.png`。

## 版本与文件（`assets/brand-kit/logo/`）

| 场景 | 文件 |
|---|---|
| 浅色底（网站、PPT、文档） | `svg/steplan-logo-horizontal.svg` |
| 深色底 | `svg/steplan-logo-horizontal-reverse.svg` |
| 竖排（海报、封面） | `svg/steplan-logo-vertical(-reverse).svg` |
| 头像、社交媒体 | `png/steplan-app-icon@2x.png` |
| 只放图形 | `svg/steplan-mark(-reverse).svg` |
| 只放文字 | `svg/steplan-wordmark.svg` |
| 单色印刷、烫印、刻字 | `svg/steplan-mark-mono-black.svg` / `-mono-white.svg` |
| 酸性绿底 | `svg/steplan-logo-horizontal.svg`（全黑） |
| 24px 及以下 | `svg/steplan-mark-small.svg` |
| 网站图标 | `favicon/` 整个目录 |
| Word、微信等不支持 SVG 的场合 | `png/` 里对应文件（`@2x` 为高清） |

标志里的文字已经转成路径，打开不需要装字体。

> 注意：交付包 `README.md` 写「酸性绿底用 `-onbrand`」，那是生成脚本对所有配色的通用说法。深空黑配色下 `onbrand` 是白字 + 绿点（深色底用）；酸性绿底请用全黑的 `steplan-logo-horizontal.svg` 或 `-brand.svg`（以《使用规范》为准）。

网站 favicon：

```html
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
```

## 使用规则

- **颜色**：主体只用深空黑或白。酸性绿只给圆点。
  - 浅底：深空黑 + 黑点（浅底上绿点看不清，不用）
  - 深底：白 + 酸性绿点
  - 酸性绿底：全黑
  - 单色：全黑 / 全白
- **安全空间**：四周至少留 1 个「圆点直径」，其中不放任何文字或图形。
- **最小尺寸**：图形标志高度 ≥ 24px 用标准版；16–24px 用 `mark-small` / favicon。横版组合最小宽度：屏幕 96px，印刷 20mm；更小只用图形、不带文字。
- **禁止**：拉伸变形；旋转或改倾角（8° 前倾是标志本身的一部分）；换成其他颜色（尤其是电光紫）；加描边、阴影、渐变；在花哨的图片上直接放标志（先压一块深色或浅色底）。

## 导出

`scripts/logo.py export <版本> --width <px> [--bg <颜色>] [--pad <圆点直径倍数>] [-o 文件]`：用 Chrome 渲染 SVG，透明底或指定底色。`list` 列出所有版本名。例：

```bash
python3 scripts/logo.py export mark-reverse --width 512 --bg '#16171C' --pad 1.5 -o 头像.png
python3 scripts/logo.py export logo-horizontal --width 1600 -o logo-透明.png
```
