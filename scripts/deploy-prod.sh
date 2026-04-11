#!/usr/bin/env bash
# 从本机 SSH 到线上服务器：拉代码、装依赖、构建前端、重启后端服务与 Nginx（前后端）。
# 用法:
#   chmod +x scripts/deploy-prod.sh
#   ./scripts/deploy-prod.sh
#   DEPLOY_HOST=1.2.3.4 ./scripts/deploy-prod.sh
#
# 环境变量:
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

DEPLOY_HOST="${DEPLOY_HOST:-47.238.72.198}"
DEPLOY_USER="${DEPLOY_USER:-root}"
REMOTE_DIR="${REMOTE_DIR:-/root/global_picker}"
GIT_BRANCH="${GIT_BRANCH:-}"

SSH_OPTS=(
  -o BatchMode=yes
  -o StrictHostKeyChecking=accept-new
  -o ConnectTimeout=20
)

echo "==> SSH ${DEPLOY_USER}@${DEPLOY_HOST} (REMOTE_DIR=${REMOTE_DIR}) ..."

# heredoc 未加引号：注入本机 REMOTE_DIR / GIT_BRANCH；远程 shell 中的 \$ 已转义
ssh "${SSH_OPTS[@]}" "${DEPLOY_USER}@${DEPLOY_HOST}" bash <<EOF
set -euo pipefail
cd '$REMOTE_DIR'
echo "==> \$(hostname)  \$(pwd)"
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
deactivate
echo "==> frontend: npm install & build"
cd ../frontend
npm install --silent
npm run build
echo "==> restart services"
systemctl restart global_picker_backend
systemctl reload nginx
systemctl is-active global_picker_backend nginx
echo "==> deploy OK"
EOF
