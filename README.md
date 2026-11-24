# Steplan SkillHub

阶梯计划（Steplan）团队的 AI 技能仓库。每个技能是 `skills/` 下的一个目录，可被 Claude Code 以及兼容 Agent Skills 的工具（openskills 等）直接加载。

## 技能列表

| 技能 | 用途 | 触发示例 |
|---|---|---|
| [steplan-wechat](skills/steplan-wechat/SKILL.md) | 按 Steplan 品牌 VI 排公众号文章，生成可一键复制到公众号编辑器的预览页。内置 5 套模板：实战干货、深度观点、案例战报、阶梯周刊、招募发布 | 「用阶梯模板排这篇」「排一期阶梯周刊」 |
| [steplan-poster](skills/steplan-poster/SKILL.md) | 按 Steplan VI 出海报 PNG：课程海报（大纲、讲师、报名二维码，长图 + 9:16）、活动招生、产品推广、金句 / 数据、公众号与小红书封面；品牌字体内置 | 「做一张训练营海报」「出一套公众号封面」 |

## 安装

```bash
git clone https://github.com/vines90/steplan-skillhub.git ~/Projects/steplan-skillhub
~/Projects/steplan-skillhub/install.sh
```

`install.sh` 把 `skills/` 下的每个技能软链接到 `~/.claude/skills/`。以后 `git pull` 后技能自动是最新的；新增了技能再跑一次 `install.sh`。

依赖：Python 3。`steplan-wechat` 的预览截图和 `steplan-poster` 出图需要 Python 版 playwright 和本机 Chrome；`steplan-poster` 生成二维码用的 segno 已内置在 `scripts/_vendor/`（BSD 协议）。

## 新增技能

1. 在 `skills/<技能名>/` 下放 `SKILL.md`（frontmatter 只写 `name` 和 `description`，`name` 与目录名一致），按需加 `scripts/`、`references/`、`assets/`。
2. 用 skill-creator 校验：`python3 ~/.claude/skills/skill-creator/scripts/quick_validate.py skills/<技能名>`
3. 在上面的技能列表里加一行，跑 `./install.sh`，提交。

## 约定

- 品牌规范以「深空黑 #16171C / 骨白 #F4F5F0 / 石墨灰 #8A8D94 / 酸性绿 #C8FF2E」为准，酸性绿只做强调。
- 不在仓库里放密钥和账号信息；需要的凭证通过环境变量读取。
- 技能里打包的字体（Unbounded、得意黑、JetBrains Mono）均为 SIL OFL 1.1 授权，版权声明与许可证见 `skills/steplan-wechat/assets/fonts/OFL.txt`；新增字体时同样附上许可证。
