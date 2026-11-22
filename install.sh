#!/usr/bin/env bash
# 把仓库里的每个技能软链接到 ~/.claude/skills（可用 CLAUDE_SKILLS_DIR 改目标目录）。
# 已有同名软链接会更新；同名的真实目录不会被覆盖，会提示你手动处理。
set -euo pipefail
repo="$(cd "$(dirname "$0")" && pwd)"
dest="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
mkdir -p "$dest"
for dir in "$repo"/skills/*/; do
  name="$(basename "$dir")"
  target="$dest/$name"
  if [ -L "$target" ]; then
    ln -sfn "${dir%/}" "$target" && echo "更新 $name"
  elif [ -e "$target" ]; then
    echo "跳过 $name：$target 已存在且不是软链接，请先手动处理"
  else
    ln -s "${dir%/}" "$target" && echo "安装 $name"
  fi
done
