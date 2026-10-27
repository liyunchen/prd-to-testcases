#!/usr/bin/env bash
# Install the prd-to-xmind skill into a WorkBuddy skills directory.
# Usage: ./install.sh [skills-dir]
set -euo pipefail

DEST="${1:-$HOME/.workbuddy-ai/skills}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$HERE/skills/prd-to-xmind-testcases"
TARGET="$DEST/prd-to-xmind-testcases"

if [ ! -d "$SRC" ]; then
  echo "找不到 $SRC，请在仓库根目录执行本脚本" >&2
  exit 1
fi

mkdir -p "$DEST"
if [ -d "$TARGET" ]; then
  echo "已存在 $TARGET，将覆盖同名技能目录"
  rm -rf "$TARGET"
fi
cp -r "$SRC" "$TARGET"

echo "✅ 已安装到 $TARGET"
echo "   重启会话后技能才会出现在可用列表里"
