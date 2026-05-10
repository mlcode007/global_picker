# HTTPS 升级 - 服务器变更记录

## 基本信息

| 项目 | 内容 |
|------|------|
| 操作日期 | 2026-05-11 04:24 CST |
| 服务器 IP | 47.238.72.198 |
| 域名 | www.globalpicker.com / globalpicker.com |
| 操作人 | AI 自动执行 (xubin) |
| 证书类型 | Let's Encrypt R13 (免费) |
| 证书有效期 | 2026-05-10 ~ 2026-08-08 (90 天) |
| 自动续期 | 每天凌晨 2:00 自动检查续期 |

---

## 执行结果摘要

| 步骤 | 状态 | 说明 |
|------|------|------|
| 安装 certbot | ✅ 成功 | certbot 1.21.0 |
| 备份 Nginx 配置 | ✅ 成功 | 3 份备份 |
| 获取 SSL 证书 | ✅ 成功 | standalone 模式 |
| 配置 Nginx HTTPS | ✅ 成功 | HTTP→HTTPS 301 跳转 |
| 重启 Nginx | ✅ 成功 | 无报错 |
| HTTPS 验证 | ✅ 成功 | HTTP/2 200 |
| 自动续期测试 | ✅ 成功 | webroot 模式 |
| crontab 设置 | ✅ 成功 | 每天 2:00 检查 |

---

## 服务器变更详情

### 1. 新增系统包

```
certbot 1.21.0
python3-certbot-nginx
```

**影响**: 新增约 20 个依赖包，无服务中断

---

### 2. 新增文件

| 文件路径 | 说明 |
|----------|------|
| `/etc/letsencrypt/live/www.globalpicker.com/` | SSL 证书目录（符号链接） |
| `/etc/letsencrypt/archive/www.globalpicker.com/` | 证书实际文件 |
| `/etc/letsencrypt/renewal/www.globalpicker.com.conf` | 续期配置（webroot 模式） |
| `/var/www/html/.well-known/acme-challenge/` | Let's Encrypt 验证目录 |

---

### 3. Nginx 配置变更

**原配置**: `/etc/nginx/sites-available/global_picker`（仅 HTTP）

**备份位置**:
- `/root/nginx-backup-20260511-042442/global_picker`
- `/etc/nginx/sites-available/global_picker.pre-https-backup`
- `/etc/nginx/sites-available/global_picker.backup-20260511`

**主要变更**:

```diff
# 变更前
server {
    listen 80;
    server_name 47.238.72.198;
    ...
}

# 变更后 - 两个 server 块
+ server {
+     listen 80;
+     server_name www.globalpicker.com globalpicker.com 47.238.72.198;
+     location /.well-known/acme-challenge/ { root /var/www/html; }
+     location / { return 301 https://$host$request_uri; }
+ }
+ 
+ server {
+     listen 443 ssl http2;
+     server_name www.globalpicker.com globalpicker.com 47.238.72.198;
+     
+     ssl_certificate /etc/letsencrypt/live/www.globalpicker.com/fullchain.pem;
+     ssl_certificate_key /etc/letsencrypt/live/www.globalpicker.com/privkey.pem;
+     
+     ssl_protocols TLSv1.2 TLSv1.3;
+     ssl_ciphers HIGH:!aNULL:!MD5;
+     ssl_stapling on;
+     
+     add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
+     add_header X-Frame-Options SAMEORIGIN always;
+     add_header X-Content-Type-Options nosniff always;
+     
+     # 保留原有所有 location 配置不变
+     ...
+ }
```

---

### 4. 新增 crontab 任务

```cron
0 2 * * * /usr/bin/certbot renew --quiet --post-hook "systemctl reload nginx"
```

**说明**: 每天凌晨 2 点检查证书是否需要续期，仅在到期前 30 天内才会真正续期

---

### 5. 续期配置修改

```diff
# /etc/letsencrypt/renewal/www.globalpicker.com.conf
[renewalparams]
- authenticator = standalone
+ authenticator = webroot
+ webroot_path = /var/www/html
```

**原因**: standalone 模式需要占用 80 端口，与 Nginx 冲突。改为 webroot 模式可在 Nginx 运行时续期。

---

## 验证结果

### HTTPS 访问测试

```
$ curl -skI --resolve www.globalpicker.com:443:127.0.0.1 https://www.globalpicker.com

HTTP/2 200 
server: nginx/1.18.0 (Ubuntu)
content-type: text/html
strict-transport-security: max-age=31536000; includeSubDomains
x-frame-options: SAMEORIGIN
x-content-type-options: nosniff
```

### HTTP 跳转测试

```
$ curl -sI http://www.globalpicker.com

HTTP/1.1 301 Moved Permanently
Location: https://www.globalpicker.com/
```

### 证书信息

```
subject=CN = www.globalpicker.com
notBefore=May 10 19:26:31 2026 GMT
notAfter=Aug  8 19:26:30 2026 GMT
issuer=C = US, O = Let's Encrypt, CN = R13
```

### 续期测试

```
Congratulations, all simulated renewals succeeded: 
  /etc/letsencrypt/live/www.globalpicker.com/fullchain.pem (success)
```

---

## 回滚方案

如需回滚到 HTTP，执行：

```bash
ssh root@47.238.72.198

# 恢复 Nginx 配置
cp /etc/nginx/sites-available/global_picker.pre-https-backup /etc/nginx/sites-available/global_picker

# 重启 Nginx
systemctl reload nginx

# 可选：删除证书和 crontab
certbot delete --cert-name www.globalpicker.com
crontab -r
```

---

## 注意事项

1. **ssl_stapling 警告**: Nginx 启动时有 `ssl_stapling` 警告，不影响使用（Let's Encrypt R13 证书无 OCSP URL）
2. **端口要求**: 80 和 443 端口必须保持开放（阿里云安全组）
3. **后端端口**: Nginx proxy_pass 指向 127.0.0.1:8000，与现有配置一致
4. **服务中断**: 配置期间 Nginx 重启约 1-2 秒，影响极小

---

## 相关文档

- [HTTPS配置指南.md](./HTTPS配置指南.md) - 详细操作手册
- [setup-https.sh](./setup-https.sh) - 自动化部署脚本
- [nginx-https.conf](./nginx-https.conf) - 最终 Nginx HTTPS 配置
- [deploy-prod.sh](../scripts/deploy-prod.sh) - 项目部署脚本
