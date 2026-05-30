#!/usr/bin/env bash
# 从本机 SSH 到线上服务器：可选同步 backend/.env → 拉代码 → 装依赖 → 构建前端 → 重启后端服务与 Nginx（前后端）。
# backend/.env 已在 .gitignore，不会提交；部署时由本机 scp 覆盖服务器同名文件。
# 用法:
#   chmod +x scripts/deploy-prod.sh
#   ./scripts/deploy-prod.sh
#   DEPLOY_HOST=1.2.3.4 ./scripts/deploy-prod.sh
#
# 环境变量: DEPLOY_HOST DEPLOY_USER REMOTE_DIR GIT_BRANCH（默认见下）
#   DEPLOY_HOST     服务器地址，默认 47.238.72.198（见 dev/deploy_server.md）
#   DEPLOY_USER     SSH 用户，默认 root
#   REMOTE_DIR      服务器上项目路径，默认 /root/global_picker
#   GIT_BRANCH      要部署的分支，默认 xubin（与日常开发分支一致）。
#                   若线上跟踪的是 main，可: GIT_BRANCH=main ./scripts/deploy-prod.sh
#
# 前置: 本机已配置对该主机的 SSH 公钥登录，否则会出现 Permission denied (publickey).

# ls -la ~/.ssh
# ssh -o BatchMode=yes root@47.238.72.198 'echo ok'
# ssh-keygen -t ed25519 -C "你的邮箱或备注" -f ~/.ssh/id_ed25519
# ssh-copy-id -i ~/.ssh/id_ed25519.pub root@47.238.72.198


set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_LOCAL="$REPO_ROOT/backend/.env"

DEPLOY_HOST="${DEPLOY_HOST:-47.238.72.198}"
DEPLOY_USER="${DEPLOY_USER:-root}"
REMOTE_DIR="${REMOTE_DIR:-/root/global_picker}"
GIT_BRANCH="${GIT_BRANCH:-}"

SSH_OPTS=(
  -o BatchMode=yes
  -o StrictHostKeyChecking=accept-new
  -o ConnectTimeout=20
)

if [[ -f "$ENV_LOCAL" ]]; then
  echo "==> scp 本机 backend/.env -> ${DEPLOY_USER}@${DEPLOY_HOST}:${REMOTE_DIR}/backend/.env"
  scp "${SSH_OPTS[@]}" "$ENV_LOCAL" "${DEPLOY_USER}@${DEPLOY_HOST}:${REMOTE_DIR}/backend/.env"
else
  echo "==> 跳过: 本机无 $ENV_LOCAL（不覆盖服务器现有 .env）"
fi

# 同步支付宝相关环境变量（这些值以本机 .env 为准）
ALIPAY_KEYS=("ALIPAY_APP_ID" "ALIPAY_PRIVATE_KEY" "ALIPAY_PUBLIC_KEY" "ALIPAY_SANDBOX")
if [[ -f "$ENV_LOCAL" ]]; then
  echo "==> 同步支付宝相关环境变量到服务器"
  for key in "${ALIPAY_KEYS[@]}"; do
    value=$(grep "^${key}=" "$ENV_LOCAL" | head -1 | cut -d'=' -f2-)
    if [[ -n "$value" ]]; then
      # 通过 SSH 更新服务器上的 .env 文件
      ssh "${SSH_OPTS[@]}" "${DEPLOY_USER}@${DEPLOY_HOST}" bash <<INNER_EOF
cd '$REMOTE_DIR/backend'
if grep -q "^${key}=" .env; then
  sed -i "s|^${key}=.*|${key}=${value}|" .env
else
  echo "${key}=${value}" >> .env
fi
INNER_EOF
      echo "    synced ${key}"
    else
      echo "    skip ${key} (not found in local .env)"
    fi
  done
fi

echo "==> SSH ${DEPLOY_USER}@${DEPLOY_HOST} ${REMOTE_DIR}"

# heredoc 未加引号：注入本机 REMOTE_DIR / GIT_BRANCH；远程 shell 中的 \$ 已转义
ssh "${SSH_OPTS[@]}" "${DEPLOY_USER}@${DEPLOY_HOST}" bash <<EOF
set -euo pipefail
cd '$REMOTE_DIR'
echo "==> \$(hostname) \$(pwd)"
if [[ -n '${GIT_BRANCH}' ]]; then
  git fetch origin
  git checkout '${GIT_BRANCH}'
  git pull --ff-only origin '${GIT_BRANCH}'
else
  git pull --ff-only
fi
echo "==> backend: pip install"
cd backend
# shellcheck source=/dev/null
source venv/bin/activate
pip install -r requirements.txt -q
# 安装 Playwright 浏览器
echo "==> installing Playwright browsers"
python -m playwright install --with-deps
deactivate
echo "==> frontend: npm install & build"
cd ../frontend
npm install --silent
npm run build
# 确保服务器上使用无头模式
echo "==> ensuring headless mode on server"
cd ../backend
if grep -q "TIKTOK_HEADLESS" .env; then
  sed -i "s/TIKTOK_HEADLESS=.*/TIKTOK_HEADLESS=True/" .env
else
  echo "TIKTOK_HEADLESS=True" >> .env
fi
echo "==> ensuring production env"
if grep -q "APP_ENV" .env; then
  sed -i "s/APP_ENV=.*/APP_ENV=production/" .env
else
  echo "APP_ENV=production" >> .env
fi
echo "==> start adb service"
adb kill-server
adb start-server
adb devices
echo "==> restart services"
systemctl restart global_picker_backend
systemctl reload nginx
systemctl is-active global_picker_backend nginx
echo "==> deploy OK"
echo "==> cleanup old artifacts (remove files older than 4 days)"
find artifacts/pdd_photo/ -type d -mtime +7 -exec rm -rf {} +
EOF
