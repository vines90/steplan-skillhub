# 模板字段参考

目录：通用 · course · camp · product · quote · cover

完整范例见 `assets/examples/`；`python3 scripts/steplan_poster.py fields` 打印字段一览。

## 通用

```json
{"template": "course", "theme": "dark", "sizes": ["long", "9:16"], "site": "steplan.ai", "...": "模板字段"}
```

- `theme`：dark / lime / bone（各模板有默认值；course 固定深色主视觉 + 分段配色）
- `sizes`：`9:16`（1080×1920）、`3:4`（1080×1440）、`long`（宽 1080，高度随内容，仅 course）
- 文字标记：`[[反白色块]]`、`==酸性绿色块==`、`**粗体**`、`\n` 换行
- 输出：`<json 文件名>-9x16.png` / `-3x4.png` / `-长图.png`，封面为 `-公众号封面.png` 等

## course 课程海报

| 字段 | 说明 |
|---|---|
| tag | 右上角胶囊，默认「招募中」 |
| kicker | 小标题，如「AI 外贸实战训练营 · 第 5 期」 |
| headline **必填** | 大标题，3 行以内，每行 6–9 字 |
| sub | 一句话副标题 |
| info | `[[标签, 值], …]`，建议 4 项（开营、周期、形式、名额） |
| gains | 你将收获，3–4 条（只出现在长图） |
| outline **必填** | `[{stage, week, title, lessons: [...]}]`，3 阶为宜，每阶 ≤ 3 节；9:16 只显示前 3 阶各前 3 节 |
| teachers | `[{name, title, bio, tags, photo}]`；photo 为本地图片路径，没有就显示姓氏首字；9:16 只显示第一位 |
| audience | 适合谁，3 条（长图） |
| price | `{label, now, orig, note}` |
| signup | `{qr 或 qr_url, title, note, deadline}`；qr 为二维码图片路径，qr_url 为报名链接 |

## camp 活动 / 简版招生

tag、kicker、headline **必填**、sub、`stages`（≤ 3 个 `{title, desc}`，逐级升高）或 `points`（要点列表）、info（3 项，值 ≤ 6 字）、`cta {how, note, qr | qr_url}`。3:4 会隐藏阶段说明。

## product 产品推广

tag、name **必填**（英文名用 Unbounded 斜 8°，≤ 8 个字符最好看）、tagline **必填**、sub、badge（如「免费」）、image（产品截图路径；没有则显示点阵插图占位）、features（≤ 3 个 `[标题, 说明]`）、url、cta（url 条右侧的短句）。

## quote 金句 / 数据

tag、text **必填**（3 行以内）、source、number `{value, unit, label}`（大数字，value ≤ 4 字符）。默认酸性绿底，数据卡建议用 dark。

## cover 封面图

series（如「AI 外贸实战 · No.018」）、title **必填**（≤ 14 字，两行）、title_square（次图用的更短标题，可省）、sub（只在小红书封面显示）、tag。一次输出：公众号封面 900×383、公众号次图 500×500、小红书封面 1080×1440（均为 2 倍像素）。
