# 解决 HTTPS 网页提示错误问题

## 问题描述

访问 `https://www.globalpicker.com/` 时 Chrome 显示异常警告。

## 原因分析

经过服务器全面检查，确认**网站本身完全正常**，无恶意代码、无钓鱼行为。

问题根源是 **Google Safe Browsing 误报**：
- 新域名刚上线，Google 安全浏览数据库尚未收录
- 阿里云香港 IP 可能被其他用户滥用过
- 网站包含登录+支付功能，容易触发钓鱼检测

## 解决方案

### 第一步：Google Search Console 域名验证

#### 1. 获取验证字符串

从 Google Search Console 页面复制 TXT 记录值，格式如：
```
google-site-verification=j1GYjFstLlVrMeOVDIGfUzVtODbNHMZyC6iavI4cHvQ
```

#### 2. 登录阿里云 DNS 控制台

访问：**https://dns.console.aliyun.com**

#### 3. 添加 TXT 记录

| 参数 | 值 |
|------|------|
| 记录类型 | TXT |
| 主机记录 | `@`（代表根域名） |
| 记录值 | `google-site-verification=j1GYjFstLlVrMeOVDIGfUzVtODbNHMZyC6iavI4cHvQ` |
| TTL | 600（默认） |

#### 4. 验证

- 等待 10 分钟 ~ 24 小时让 DNS 生效
- 回到 Google Search Console 点击 **验证**

#### 5. 验证成功标志

看到绿色对勾表示验证通过。

---

### 第二步：提交网站地图

验证通过后，进入 **索引 > 站点地图**，提交：
```
https://www.globalpicker.com/sitemap.xml
```

---

### 第三步：申请解除 Safe Browsing 警告

访问：**https://safebrowsing.google.com/safebrowsing/report_error/**

填写：
- URL: `https://www.globalpicker.com/`
- 说明：这是一个正常的跨境电商选品比价工具网站，不是钓鱼网站

---

### 第四步：提交 Bing 审查（可选）

访问：**https://www.bing.com/webmasters/urlsubmission**

---

## 后续维护

### 保留 TXT 记录

**不要删除**阿里云的 TXT 记录，它是域名所有权的证明，删除会导致验证失效。

### 建议添加备用验证方式

在 Google Search Console **设置 > 所有权验证** 中添加：
- HTML 文件上传验证
- Google Analytics 跟踪代码验证

### 日常维护

- 关注 Google 发来的邮件（检测到严重问题时会通知）
- 每月登录一次 Search Console 检查 **效果报告** 和 **索引覆盖范围**

---

## 服务器检查清单（确认无问题）

| 检查项 | 结果 |
|--------|------|
| 网站内容 | ✅ 正常的 Vue SPA，无恶意代码 |
| JS 文件 | ✅ 无 eval/document.write 等可疑代码 |
| 外部引用 | ✅ 无异常外部链接 |
| Nginx 配置 | ✅ 正常代理到本地 8000 |
| 恶意重定向 | ✅ 无 |
| 隐藏 iframe | ✅ 无 |
| 可疑进程 | ✅ 无 |
| 可疑定时任务 | ✅ 只有 certbot 续期 |

---

## 相关链接

- 申诉网站: https://safebrowsing.google.com/safebrowsing/report_error/
- Google Search Console: https://search.google.com/search-console
- Safe Browsing 报告: https://safebrowsing.google.com/safebrowsing/report_error/
- Bing Webmaster: https://www.bing.com/webmasters
- 阿里云 DNS: https://dns.console.aliyun.com
- 元宝问答: https://yb.tencent.com/s/iSILnx0mqX0f
- 元宝问答: "谷歌 申请解除 Safe Browsin..."点击查看元宝的回答 https://yb.tencent.com/s/ueIdtlbpOUM7