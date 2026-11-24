# article.json 与块参考

目录：文件格式 · 行内标记 · 五套模板骨架 · 块参考（通用 / 干货 / 观点 / 战报 / 周刊 / 招募）· 主题兼容

完整范例见 `assets/examples/01-sop.json` … `05-camp.json`，写新文章时先复制最接近的一份再改。
字段签名以 `python3 scripts/steplan_wechat.py blocks` 的输出为准。

## 文件格式

```json
{
  "template": "sop",                 // sop | essay | case | weekly | camp（essay 为深色整篇）
  "title": "公众号标题",              // 只用于预览页模拟微信标题，不进正文
  "name": "可选，预览页左侧显示名",
  "date": "可选，如 2026年12月1日",
  "footer": true,                    // 默认自动追加品牌尾卡；false 则不加
  "blocks": [
    "纯字符串 = 一个正文段落",
    {"type": "step", "n": 1, "total": 3, "kicker": "画像", "title": "……"}
  ]
}
```

## 行内标记

所有 text / title / items 文本里可用：`**粗体**`、`==酸性绿色块==`、`[[反白色块]]`、`` `等宽` ``、`\n` 强制换行。
提示词卡片 `prompt.lines` 里用 `{变量}` 标绿。`==` 每节最多一两处，`[[ ]]` 留给标题和金句。

## 五套模板骨架

按顺序列出常用块，可增删、可重复；文章没有对应内容的块就不用。

- **sop 实战干货**：masthead → meta → gets → p… → [step → p → prompt / callout / image / kv / bullets]×N → keypoint → checklist → end → related
- **essay 深度观点**（深色）：masthead → kicker → headline → byline → lead → [section → p… → stat / pullquote / shift / ladder]×N → epilogue → related
- **case 案例战报**：masthead → case_hero → stepper → [numhead → p / timeline / table / testimonial / actions]×N → cta → related
- **weekly 阶梯周刊**：weekly_masthead → p（导语）→ toc → [secbar → news / tools / briefs]×N → weekquote → related
- **camp 招募发布**：hero_lime → info → [blockhead → pains / stage×3 / fit / faq]… → price → join

## 块参考

### 通用（任何模板）

| type | 字段 | 说明 |
|---|---|---|
| p | text, size=15 | 正文；blocks 里直接写字符串等价 |
| bullets | items | 方块圆点列表 |
| image | caption, hint, height | 虚线图片位 + 图注；用户粘贴后换成真图 |
| screenshot | src, caption, alt? | 真实截图 + 图注；src 为相对 article.json 的 PNG/JPG/WebP 路径，渲染时内嵌为 data URI |
| masthead | column, no | 报头：栏目名 + 期号（No.018 / CASE 07 / ESSAY 06） |
| blockhead | title, kicker? | 英文小字（可省）+ 大标题 + 短横杠，最通用的小标题。后面紧跟 step 时不要再放 blockhead，两个大标题会叠在一起 |
| keypoint | text, tag | 酸性绿金句卡，全文最多 1 张 |
| end | — | 三横杠 + END 结束标记 |
| related | items | 往期推荐标题列表（可选，没有就不放） |

### 干货（sop）

- `meta`：read（"8 分钟"）、level（1–3）、level_text（入门/进阶/高阶）、fit（适合人群）
- `gets`：items（读完你将得到，3 条左右）
- `step`：n、total、title、kicker（可省，两字关键词）。横杠点亮 n 级，所以 total 最好是 3；超过 3 步改用 blockhead。一组步骤直接用 step，不必先放 blockhead
- `prompt`：name、lines（每行一段）、note（底部说明）
- `callout`：tag（避坑 / 注意 / 技巧，2 字最好）、text
- `kv`：title（"FILTER · 三条筛选标准"）、rows `[[键, 值]]`，键 ≤ 6 字
- `checklist`：title、items

### 观点（essay，也可用于浅色模板）

- `kicker` 开场小字 · `headline` 28px 大字（用 `\n` 断行，`==` 标一个词）· `byline` 署名 · `lead` 导语
- `section`：no（"01"）、kicker（英文短语）、title
- `stat`：big（"8 → 3"、"73%"，≤ 6 字符）、text、tag
- `pullquote`：text、source（默认"—— 阶梯计划"）
- `shift`：pairs `[[旧, 新]]`，新的一侧 ≤ 14 字
- `ladder`：steps 正好 3 个 `[[编号, 名称, 结论]]`，名称 ≤ 9 字（三栏很窄）
- `epilogue`：text、tag

### 战报（case）

- `case_hero`：title、facts `[[键, 值]]`×3、stats `[[数字, 单位, 说明]]`×3、badge（可选角标，如"示例数据"）
- `stepper`：steps `[[名称, 状态, done|now|todo]]`×3，状态 ≤ 7 字
- `numhead`：no、title
- `timeline`：stages `[{stage, when, title, text, output, kind}]`，kind=now 的那段用绿色产出条
- `table`：headers 正好 3 列 `[指标, 之前, 之后]`；rows `[[指标, 之前, 之后, 涨幅?]]`，涨幅可省；note
- `testimonial`：text、name（首字做头像）、role
- `actions`：items `[[标题, 说明]]`
- `cta`：title、text、button、tag

### 周刊（weekly）

- `weekly_masthead`：vol（"VOL.012"）、dates（"11.17 — 11.23"）、tagline
- `toc`：items `[[标题, 分类]]`，分类 2 字
- `secbar`：no、cn（4 字栏目名）、en、count（"2 ITEMS"）
- `news`：no、cat、title、tags、body、comment（阶梯点评）、source
- `tools`：no、cat、title、tools `[[名称, 一句话, 评分 1–3]]`
- `briefs`：items `[{no, cat, title, text}]`
- `weekquote`：no、text

### 招募（camp）

- `hero_lime`：series、headline（`\n` 断行，`[[ ]]` 包住最想强调的短语）、sub
- `info`：cells `[[标签, 值]]`×3，值 ≤ 5 字符
- `pains`：items
- `stage`：n、name、week、title、items、output、peak（最后一阶 true）
- `fit`：yes、no（各 3 条，≤ 10 字）
- `price`：price、orig、includes、note、tag。没有真实价格就写 "X,XXX" 占位并告诉用户
- `faq`：items `[[问, 答]]`
- `join`：how（如"后台回复==训练营=="）、text、urgent（可省）。不放二维码

## 主题兼容

essay 是深色整篇，只用这些块：p、bullets、image、masthead、blockhead、end、related、keypoint、kicker、headline、byline、lead、section、stat、pullquote、shift、ladder、epilogue、gets、callout、kv、meta、step。
战报 / 周刊 / 招募的专属块（黑底卡片、白底胶囊）只放在浅色模板里。观点类块（section、stat、pullquote、shift、ladder 等）会跟随主题，浅色模板里也能用。
