# 字体

## 角色

| 角色 | 字体 | 文件（assets/fonts） | 说明 |
|---|---|---|---|
| 中文标题、大数字 | 得意黑 Smiley Sans | SmileySans.ttf | 自带斜体感；也用于数字 |
| 英文标识、产品名 | Unbounded SemiBold 600，斜 8° | Unbounded.ttf（可变） | 呼应标志 8° 前倾；只用于短词（steplan、sohobot、Step 1） |
| 正文 | 思源黑体 / Noto Sans SC | 网页用 NotoSansSC.ttf（可变）；Office 用 SourceHanSansCN-Regular / -Bold.otf | Regular 为主，强调用 Bold |
| 小标签、编号、网址 | JetBrains Mono | JetBrainsMono.ttf（可变） | 全大写英文 + 中文，字距 0.12–0.16em，如「CURRICULUM · 课程大纲」 |

全部为 SIL OFL 开源授权，可商用（`assets/fonts/OFL.txt`、`SourceHanSans-LICENSE.txt`）。

## 字号层级（参考）

| 媒介 | 标题 | 正文 | 标签 |
|---|---|---|---|
| PPT 16:9 | 30–34pt（封面 54pt，章节编号 130pt） | 16–20pt | 9–10pt |
| 海报 1080 宽 | 120–150px | 30–34px | 20–26px |
| 公众号文章 | 20–28px | 15px，行高 1.85 | 11px |
| 网页 | 48–96px | 16–18px | 12px |

## 各软件里的坑（实测）

- **PowerPoint / Keynote / WPS**：
  - 得意黑的字体名必须写中文「**得意黑**」。写「Smiley Sans」会回退成系统字体；写「Smiley Sans Oblique」时中文正常，英文会回退。
  - 正文**不要用 Noto Sans SC 可变字体**：它的默认字重是 Thin，Office 里容易显示成极细的字。改用静态版「**Source Han Sans CN**」（思源黑体 CN），常规和粗体各一个文件。
  - 新装字体后，正在运行的软件要**退出重开**才能识别。
  - 对方电脑没装字体就会回退成系统字体。外发用 PDF。
- **飞书文档 / 幻灯片**：不能用自定义字体，标题会变成默认字体；正式物料不要以飞书为终稿。
- **公众号文章**：只能用系统字体（苹方 / 微软雅黑），品牌字体的大标题要做成图片插入。
- **网页 / HTML 出图**：用 `@font-face` 直接加载 `assets/fonts` 里的文件（见 `assets/tokens.css`），可变字体在浏览器里能正常调字重。
