# Let's Encrypt + Certbot 配置 HTTPS 详细指南

## 前置准备

在开始之前，确保：
- 域名 `www.globalpicker.com` 已解析到服务器 IP `47.238.72.198`
- 服务器 80 和 443 端口已开放（阿里云安全组）
- 你有服务器的 SSH 访问权限

---

## 第一步：SSH 登录服务器

```bash
ssh root@47.238.72.198
```

---

## 第二步：确认 Web 服务器类型

```bash
# 检查是否安装了 Nginx
nginx -v

# 或检查 Apache
apache2 -v
# 或
httpd -v
```

根据你的服务器配置选择对应的 certbot 插件。

---

## 第三步：安装 Certbot

### Ubuntu/Debian 系统：

```bash
sudo apt update
sudo apt install certbot python3-certbot-nginx -y
# 如果是 Apache，用这个：
# sudo apt install certbot python3-certbot-apache -y
```

### CentOS/RHEL 系统：

```bash
sudo yum install epel-release -y
sudo yum install certbot python3-certbot-nginx -y
```

---

## 第四步：获取并安装证书

### 方式 A：自动配置 Nginx（推荐）

```bash
sudo certbot --nginx -d www.globalpicker.com -d globalpicker.com
```

执行后会提示：
1. 输入邮箱（用于证书续期通知）
2. 同意服务条款
3. 选择是否将 HTTP 重定向到 HTTPS（选 2 强制 HTTPS）

### 方式 B：仅获取证书（手动配置）

```bash
sudo certbot certonly --nginx -d www.globalpicker.com -d globalpicker.com
```

证书文件位置：
- 证书：`/etc/letsencrypt/live/www.globalpicker.com/fullchain.pem`
- 私钥：`/etc/letsencrypt/live/www.globalpicker.com/privkey.pem`

---

## 第五步：手动配置 Nginx（如果选择方式 B）

编辑 Nginx 配置文件：

```bash
sudo nano /etc/nginx/sites-available/default
# 或你的配置文件路径
```

添加/修改配置：

```nginx
# HTTP 服务器 - 重定向到 HTTPS
server {
    listen 80;
    server_name www.globalpicker.com globalpicker.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS 服务器
server {
    listen 443 ssl http2;
    server_name www.globalpicker.com globalpicker.com;
    
    # SSL 证书路径
    ssl_certificate /etc/letsencrypt/live/www.globalpicker.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/www.globalpicker.com/privkey.pem;
    
    # SSL 优化配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # 其他配置（根据你的项目调整）
    location / {
        proxy_pass http://localhost:你的端口;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

测试并重启 Nginx：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## 第六步：设置自动续期

Let's Encrypt 证书有效期为 **90 天**，需要自动续期。

### 测试自动续期：

```bash
sudo certbot renew --dry-run
```

### 添加定时任务（如果未自动创建）：

```bash
sudo crontab -e
```

添加以下行（每天凌晨 2 点检查续期）：

```cron
0 2 * * * /usr/bin/certbot renew --quiet --post-hook "systemctl reload nginx"
```

---

## 第七步：验证 HTTPS

### 浏览器访问：
```
https://www.globalpicker.com
```

### 命令行测试：
```bash
curl -I https://www.globalpicker.com
```

应该看到 `HTTP/2 200` 或 `HTTP/1.1 200 OK`

### 在线检测工具：
访问 [SSL Labs](https://www.ssllabs.com/ssltest/) 输入你的域名进行完整检测。

---

## 常见问题排查

### 1. 证书申请失败

```bash
# 检查 80 端口是否可访问
sudo lsof -i :80

# 检查阿里云安全组是否开放 80/443 端口
```

### 2. Nginx 配置错误

```bash
# 查看错误日志
sudo tail -f /var/log/nginx/error.log
```

### 3. 查看证书信息

```bash
sudo certbot certificates
```

### 4. 强制续期证书

```bash
sudo certbot renew --force-renewal
```

---

## 快速一键脚本（可选）

如果你想简化操作，可以创建这个脚本：

```bash
#!/bin/bash
# setup-https.sh

DOMAIN="www.globalpicker.com"
EMAIL="你的邮箱@example.com"

echo "正在安装 certbot..."
sudo apt update && sudo apt install certbot python3-certbot-nginx -y

echo "正在获取证书..."
sudo certbot --nginx -d $DOMAIN --non-interactive --agree-tos -m $EMAIL --redirect

echo "设置自动续期..."
sudo systemctl enable certbot.timer

echo "HTTPS 配置完成！"
```

使用方法：
```bash
chmod +x setup-https.sh
sudo ./setup-https.sh
```

---

## 注意事项

1. **证书有效期**：Let's Encrypt 证书有效期 90 天，务必设置自动续期
2. **端口开放**：确保阿里云安全组已开放 80 和 443 端口
3. **域名解析**：确保 `www.globalpicker.com` 和 `globalpicker.com` 都已解析到服务器 IP
4. **防火墙**：如果启用了 ufw/iptables，需要放行 443 端口

---

## 下一步

按照以上步骤操作后，你的网站就会启用 HTTPS。如果遇到任何问题，随时排查解决。
