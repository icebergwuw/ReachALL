#!/bin/bash
# 一键推送并部署
# 用法: ./deploy.sh "commit message"
# 需要设置环境变量: export VERCEL_TOKEN=xxx  (或写入 ~/.zshrc)

MSG=${1:-"update"}

VERCEL_TOKEN=${VERCEL_TOKEN:-""}
VERCEL_SCOPE="icebergwuws-projects-8bbc9b0e"

if [ -z "$VERCEL_TOKEN" ]; then
  echo "❌ 未设置 VERCEL_TOKEN，请先运行: export VERCEL_TOKEN=你的token"
  exit 1
fi

echo "→ git push..."
git add -A
git commit -m "$MSG" 2>/dev/null || true
git push github master

echo "→ vercel deploy..."
npx vercel deploy --prod \
  --token "$VERCEL_TOKEN" \
  --scope "$VERCEL_SCOPE" \
  --yes 2>&1 | grep -E "Aliased|Error|status"
