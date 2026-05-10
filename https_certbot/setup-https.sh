#!/usr/bin/env bash
# 从本机 SSH 到线上服务器，配置 Let's Encrypt HTTPS 证书。
# 用法:
#   chmod +x https_certbot/setup-https.sh
#   ./https_certbot/setup-https.sh
#
# 环境变量: DEPLOY_HOST DEPLOY_USER REMOTE_DIR ADMIN_EMAIL
#   DEPLOY_HOST     服务器地址，默认 47.238.72.198
#   DEPLOY_USER     SSH 用户，默认 root
#   REMOTE_DIR      服务器上项目路径，默认 /root/global_picker
#   ADMIN_EMAIL     证书通知邮箱，必填
#   DOMAIN          主域名，默认 www.globalpicker.com
#   DOMAIN_ALT      备用域名，默认 globalpicker.com

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DEPLOY_HOST="${DEPLOY_HOST:-47.238.72.198}"
DEPLOY_USER="${DEPLOY_USER:-root}"
REMOTE_DIR="${REMOTE_DIR:-/root/global_picker}"
DOMAIN="${DOMAIN:-www.globalpicker.com}"
DOMAIN_ALT="${DOMAIN_ALT:-globalpicker.com}"
ADMIN_EMAIL="${ADMIN_EMAIL:-}"

if [[ -z "$ADMIN_EMAIL" ]]; then
  echo "错误: 请设置 ADMIN_EMAIL 环境变量"
  echo "用法: ADMIN_EMAIL=your@email.com ./https_certbot/setup-https.sh"
  exit 1
fi

SSH_OPTS=(
  -o BatchMode=yes
  -o StrictHostKeyChecking=accept-new
  -o ConnectTimeout=20
)

echo "=========================================="
echo "  Let's Encrypt HTTPS 配置脚本"
echo "=========================================="
echo "服务器: ${DEPLOY_USER}@${DEPLOY_HOST}"
echo "域名: ${DOMAIN} / ${DOMAIN_ALT}"
echo "邮箱: ${ADMIN_EMAIL}"
echo "=========================================="
echo ""

# 第一步：检查连接
echo "==> 检查服务器连接..."
ssh "${SSH_OPTS[@]}" "${DEPLOY_USER}@${DEPLOY_HOST}" 'echo "连接成功"' || {
  echo "错误: 无法连接到服务器，请检查 SSH 配置"
  exit 1
}

# 第二步：安装 certbot
echo ""
echo "==> 安装 certbot..."
ssh "${SSH_OPTS[@]}" "${DEPLOY_USER}@${DEPLOY_HOST}" bash <<'EOF'
set -euo pipefail

# 检测系统类型
if command -v apt &>/dev/null; then
  echo "检测到 Debian/Ubuntu 系统"
  apt update -qq
  apt install -y -qq certbot python3-certbot-nginx
elif command -v yum &>/dev/null; then
  echo "检测到 CentOS/RHEL 系统"
  yum install -y epel-release
  yum install -y certbot python3-certbot-nginx
else
  echo "错误: 不支持的系统"
  exit 1
fi

echo "certbot 安装完成"
certbot --version
EOF

# 第三步：备份现有 Nginx 配置
echo ""
echo "==> 备份现有 Nginx 配置..."
ssh "${SSH_OPTS[@]}" "${DEPLOY_USER}@${DEPLOY_HOST}" bash <<'EOF'
set -euo pipefail

NGINX_CONF="/etc/nginx/nginx.conf"
SITES_DIR="/etc/nginx/sites-available"
SITES_ENABLED="/etc/nginx/sites-enabled"

BACKUP_DIR="/root/nginx-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

if [[ -f "$NGINX_CONF" ]]; then
  cp "$NGINX_CONF" "$BACKUP_DIR/"
  echo "已备份 nginx.conf"
fi

if [[ -d "$SITES_DIR" ]]; then
  cp -r "$SITES_DIR" "$BACKUP_DIR/"
  echo "已备份 sites-available"
fi

if [[ -d "$SITES_ENABLED" ]]; then
  cp -r "$SITES_ENABLED" "$BACKUP_DIR/"
  echo "已备份 sites-enabled"
fi

echo "备份目录: $BACKUP_DIR"
EOF

# 第四步：获取 Let's Encrypt 证书
echo ""
echo "==> 获取 Let's Encrypt 证书..."
ssh "${SSH_OPTS[@]}" "${DEPLOY_USER}@${DEPLOY_HOST}" bash <<EOF
set -euo pipefail

# 先停止 nginx 释放 80 端口（certbot standalone 模式需要）
systemctl stop nginx || true

# 使用 standalone 模式获取证书
certbot certonly --standalone \
  -d ${DOMAIN} \
  -d ${DOMAIN_ALT} \
  --non-interactive \
  --agree-tos \
  -m ${ADMIN_EMAIL} \
  --force-renewal || {
    echo "证书获取失败，尝试 webroot 模式..."
    # 如果 standalone 失败，尝试 webroot 模式
    systemctl start nginx
    
    # 确保 webroot 目录存在
    mkdir -p /var/www/html/.well-known/acme-challenge
    
    certbot certonly --webroot \
      -w /var/www/html \
      -d ${DOMAIN} \
      -d ${DOMAIN_ALT} \
      --non-interactive \
      --agree-tos \
      -m ${ADMIN_EMAIL}
  }

echo "证书获取成功"

# 验证证书文件
CERT_DIR="/etc/letsencrypt/live/${DOMAIN}"
if [[ -f "\$CERT_DIR/fullchain.pem" ]] && [[ -f "\$CERT_DIR/privkey.pem" ]]; then
  echo "证书文件验证通过"
  ls -la "\$CERT_DIR/"
else
  echo "错误: 证书文件不存在"
  exit 1
fi
EOF

# 第五步：配置 Nginx HTTPS
echo ""
echo "==> 配置 Nginx HTTPS..."

# 先在本地生成 Nginx 配置文件
CERT_DIR="/etc/letsencrypt/live/${DOMAIN}"

cat > /tmp/nginx-https-${DOMAIN}.conf <<NGINX_CONF
# HTTP 服务器 - 重定向到 HTTPS
server {
    listen 80;
    server_name ${DOMAIN} ${DOMAIN_ALT} 47.238.72.198;
    
    # Let's Encrypt 验证路径（用于证书续期）
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    # 其他所有请求重定向到 HTTPS
    location / {
        return 301 https://\$host\$request_uri;
    }
}

# HTTPS 服务器
server {
    listen 443 ssl http2;
    server_name ${DOMAIN} ${DOMAIN_ALT} 47.238.72.198;
    
    # SSL 证书路径
    ssl_certificate ${CERT_DIR}/fullchain.pem;
    ssl_certificate_key ${CERT_DIR}/privkey.pem;
    
    # SSL 优化配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_stapling on;
    ssl_stapling_verify on;
    
    # 安全头
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options SAMEORIGIN always;
    add_header X-Content-Type-Options nosniff always;
    
    # 前端静态文件
    root /root/global_picker/frontend/dist;
    index index.html;
    
    # gzip 压缩
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;
    gzip_min_length 1000;
    
    # API 反向代理到 FastAPI 后端
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        proxy_buffering on;
        proxy_buffer_size 64k;
        proxy_buffers 80 64k;
        proxy_busy_buffers_size 256k;
        proxy_max_temp_file_size 500m;
        
        proxy_read_timeout 300s;
        proxy_connect_timeout 60s;
    }
    
    # artifacts 静态资源代理
    location /artifacts/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
    
    # Swagger 文档代理
    location /docs {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
    
    location /openapi.json {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
    }
    
    # Vue Router history 模式 - 所有其他路由回退到 index.html
    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
NGINX_CONF

# 上传配置文件到服务器并应用
scp "${SSH_OPTS[@]}" "/tmp/nginx-https-${DOMAIN}.conf" "${DEPLOY_USER}@${DEPLOY_HOST}:/tmp/nginx-https.conf"
rm /tmp/nginx-https-${DOMAIN}.conf

ssh "${SSH_OPTS[@]}" "${DEPLOY_USER}@${DEPLOY_HOST}" bash <<'EOF'
set -euo pipefail

# 服务器上的 Nginx 配置文件路径
NGINX_SITE="/etc/nginx/sites-available/global_picker"
SITES_ENABLED="/etc/nginx/sites-enabled/global_picker"

echo "使用配置文件: $NGINX_SITE"

# 备份原配置
cp "$NGINX_SITE" "${NGINX_SITE}.pre-https-backup"
cp "$NGINX_SITE" "${NGINX_SITE}.backup-$(date +%Y%m%d)"

# 应用新配置
cp /tmp/nginx-https.conf "$NGINX_SITE"
rm /tmp/nginx-https.conf

# 确保 sites-enabled 有链接
if [[ ! -L "$SITES_ENABLED" ]] && [[ ! -f "$SITES_ENABLED" ]]; then
  ln -s "$NGINX_SITE" "$SITES_ENABLED"
  echo "已创建 sites-enabled 链接"
fi

echo "Nginx HTTPS 配置完成"
EOF

# 第六步：测试并重启 Nginx
echo ""
echo "==> 测试并重启 Nginx..."
ssh "${SSH_OPTS[@]}" "${DEPLOY_USER}@${DEPLOY_HOST}" bash <<'EOF'
set -euo pipefail

# 测试配置
echo "测试 Nginx 配置..."
nginx -t

# 重启 Nginx
echo "重启 Nginx..."
systemctl restart nginx

# 检查状态
echo "检查 Nginx 状态..."
systemctl status nginx --no-pager -l

echo "Nginx 重启成功"
EOF

# 第七步：设置自动续期
echo ""
echo "==> 设置证书自动续期..."
ssh "${SSH_OPTS[@]}" "${DEPLOY_USER}@${DEPLOY_HOST}" bash <<'EOF'
set -euo pipefail

# 测试续期
echo "测试证书续期..."
certbot renew --dry-run

# 添加定时任务
echo "添加自动续期定时任务..."
(crontab -l 2>/dev/null | grep -v certbot; echo "0 2 * * * /usr/bin/certbot renew --quiet --post-hook 'systemctl reload nginx'") | crontab -

echo "自动续期配置完成"
crontab -l
EOF

# 第八步：验证 HTTPS
echo ""
echo "==> 验证 HTTPS..."
ssh "${SSH_OPTS[@]}" "${DEPLOY_USER}@${DEPLOY_HOST}" bash <<EOF
set -euo pipefail

echo "测试 HTTPS 连接..."
curl -I https://${DOMAIN} 2>/dev/null | head -5 || echo "curl 测试失败，请手动检查"

echo ""
echo "查看证书信息..."
certbot certificates
EOF

echo ""
echo "=========================================="
echo "  HTTPS 配置完成！"
echo "=========================================="
echo ""
echo "访问地址: https://${DOMAIN}"
echo "证书有效期: 90 天（自动续期）"
echo "备份位置: /root/nginx-backup-* 和 Nginx 配置文件的 .backup 文件"
echo ""
echo "如需回滚，执行:"
echo "  ssh ${DEPLOY_USER}@${DEPLOY_HOST}"
echo "  cp /etc/nginx/nginx.conf.backup-* /etc/nginx/nginx.conf"
echo "  systemctl reload nginx"
echo ""
