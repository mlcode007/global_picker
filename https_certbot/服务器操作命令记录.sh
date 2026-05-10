#!/usr/bin/env bash
# HTTPS 升级 - 服务器操作命令记录
# 此脚本从本地通过 SSH 在服务器上执行所有 HTTPS 配置操作
# 用法: ./https_certbot/服务器操作命令记录.sh
# 这个脚本包含了刚才在服务器上执行的所有操作，通过本地 SSH 远程执行：
# 1. 检查服务器连接和状态
# 2. 安装 certbot
# 3. 备份 Nginx 配置
# 4. 获取 Let's Encrypt 证书
# 5. 配置 Nginx HTTPS
# 6. 测试并重启 Nginx
# 7. 设置自动续期
# 如果将来需要在其他服务器重新执行相同的 HTTPS 配置，直接运行这个脚本即可。

set -euo pipefail

DEPLOY_HOST="47.238.72.198"
DEPLOY_USER="root"
DOMAIN="www.globalpicker.com"
DOMAIN_ALT="globalpicker.com"
ADMIN_EMAIL="xubin_work@163.com"

SSH="ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new ${DEPLOY_USER}@${DEPLOY_HOST}"
SCP="scp -o BatchMode=yes -o StrictHostKeyChecking=accept-new"

echo "=========================================="
echo "  HTTPS 升级 - 服务器操作记录"
echo "=========================================="

# 第一步：检查服务器连接和当前状态
echo ""
echo "==> 第一步：检查服务器连接和当前状态"
$SSH 'echo "连接成功" && hostname && cat /etc/os-release | head -5 && nginx -v 2>&1 && systemctl status nginx --no-pager | head -10'

# 第二步：安装 certbot
echo ""
echo "==> 第二步：安装 certbot"
$SSH 'apt update -qq && apt install -y -qq certbot python3-certbot-nginx 2>&1 | tail -20 && echo "---CERTBOT_VERSION---" && certbot --version'

# 第三步：备份现有 Nginx 配置
echo ""
echo "==> 第三步：备份现有 Nginx 配置"
$SSH 'BACKUP_DIR="/root/nginx-backup-$(date +%Y%m%d-%H%M%S)" && mkdir -p "$BACKUP_DIR" && cp /etc/nginx/sites-available/global_picker "$BACKUP_DIR/" && cp /etc/nginx/sites-available/global_picker /etc/nginx/sites-available/global_picker.pre-https-backup && cp /etc/nginx/sites-available/global_picker /etc/nginx/sites-available/global_picker.backup-$(date +%Y%m%d) && echo "备份完成: $BACKUP_DIR" && ls -la "$BACKUP_DIR/"'

# 第四步：获取 Let's Encrypt 证书
echo ""
echo "==> 第四步：获取 Let's Encrypt 证书"
$SSH 'systemctl stop nginx && sleep 1 && certbot certonly --standalone -d '"$DOMAIN"' -d '"$DOMAIN_ALT"' --non-interactive --agree-tos -m '"$ADMIN_EMAIL"' --force-renewal 2>&1'

# 验证证书文件
echo ""
echo "==> 验证证书文件"
$SSH 'ls -la /etc/letsencrypt/live/'"$DOMAIN"'/ && echo "---" && openssl x509 -in /etc/letsencrypt/live/'"$DOMAIN"'/fullchain.pem -noout -subject -dates -issuer'

# 第五步：配置 Nginx HTTPS
echo ""
echo "==> 第五步：配置 Nginx HTTPS"

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

# 上传配置文件到服务器
$SCP /tmp/nginx-https-${DOMAIN}.conf ${DEPLOY_USER}@${DEPLOY_HOST}:/tmp/nginx-https.conf
rm /tmp/nginx-https-${DOMAIN}.conf

# 应用配置
$SSH 'cp /tmp/nginx-https.conf /etc/nginx/sites-available/global_picker && rm /tmp/nginx-https.conf && echo "配置已应用"'

# 第六步：测试并重启 Nginx
echo ""
echo "==> 第六步：测试并重启 Nginx"
$SSH 'nginx -t 2>&1 && echo "---配置测试通过---" && systemctl restart nginx && echo "---Nginx已重启---" && systemctl status nginx --no-pager | head -15'

# 验证 HTTPS
echo ""
echo "==> 验证 HTTPS"
$SSH 'echo "---测试 HTTPS---" && curl -skI --resolve '"$DOMAIN"':443:127.0.0.1 https://'"$DOMAIN"' 2>&1 | head -15 && echo "---测试 HTTP 跳转---" && curl -sI http://'"$DOMAIN"' 2>&1 | head -10'

# 第七步：设置自动续期
echo ""
echo "==> 第七步：设置自动续期"

# 修改续期配置为 webroot 模式
$SSH 'mkdir -p /var/www/html/.well-known/acme-challenge && sed -i "s/authenticator = standalone/authenticator = webroot/" /etc/letsencrypt/renewal/'"$DOMAIN"'.conf && echo "webroot_path = /var/www/html" >> /etc/letsencrypt/renewal/'"$DOMAIN"'.conf && echo "---新续期配置---" && cat /etc/letsencrypt/renewal/'"$DOMAIN"'.conf'

# 测试续期
echo ""
echo "==> 测试证书续期"
$SSH 'rm -f /var/run/lock/certbot.lock /run/lock/certbot.lock && sleep 2 && certbot renew --dry-run 2>&1'

# 设置 crontab
echo ""
echo "==> 设置 crontab 自动续期"
$SSH 'echo "0 2 * * * /usr/bin/certbot renew --quiet --post-hook \"systemctl reload nginx\"" | crontab - && echo "---crontab 已设置---" && crontab -l'

echo ""
echo "=========================================="
echo "  HTTPS 升级完成！"
echo "=========================================="
echo ""
echo "访问地址: https://${DOMAIN}"
echo "证书有效期: 90 天（自动续期）"
echo "备份位置: /root/nginx-backup-* 和 Nginx 配置文件的 .backup 文件"
