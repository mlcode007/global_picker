# 改动记录 — Playwright 采集升级 + 反爬突破

> **日期**：2026-03-16  
> **目标**：将 httpx 静态请求升级为 Playwright 浏览器自动化，并实现 Cookie/代理/有头模式三种绕过 CAPTCHA 方案

---

## 背景

上一版 httpx 采集的问题：TikTok Shop 产品页为纯客户端渲染（CSR），httpx 拿到的 HTML 是空壳，无 `__NEXT_DATA__`，导致三层策略均返回空。

升级为 Playwright 后，执行 JS 后页面正常渲染，但服务器 IP 被 TikTok 识别为数据中心，触发 **CAPTCHA（Security Check）**。

**最终诊断：是 IP 信誉问题，非浏览器指纹问题。**

---

## 改动明细

### 1. `backend/requirements.txt`

新增两个依赖：

```diff
+ # 浏览器自动化（JS 渲染页面采集）
+ playwright>=1.49.0
+ playwright-stealth>=1.0.0
```

安装命令（已执行）：
```bash
pip install playwright playwright-stealth
playwright install chromium
```

---

### 2. `backend/app/config.py`

新增三个采集配置项：

```python
# 代理：http://user:pass@host:port 或 socks5://host:port，留空不使用
TIKTOK_PROXY: str = ""

# Cookie：从浏览器 DevTools 复制，JSON 格式 {"name":"value",...}
TIKTOK_COOKIES: str = ""

# 有头模式：False=显示浏览器窗口(可手动过验证)  True=无界面后台
TIKTOK_HEADLESS: bool = False
```

---

### 3. `backend/.env`

新增三个对应环境变量（默认值）：

```ini
TIKTOK_PROXY=
TIKTOK_COOKIES=
TIKTOK_HEADLESS=False
```

---

### 4. `backend/app/workers/tiktok_crawler.py`（核心重写）

**架构升级：httpx → Playwright + stealth + 三层策略**

#### 4.1 启动配置

```python
launch_opts = {
    "headless": settings.TIKTOK_HEADLESS,
    "slow_mo": 0 if headless else 200,  # 有头模式减速，更像人类
    "args": ["--no-sandbox", "--disable-blink-features=AutomationControlled"],
}
if proxy_cfg:
    launch_opts["proxy"] = proxy_cfg
```

#### 4.2 Cookie 注入

```python
cookies = _load_cookies()   # 解析 JSON 或 key=value 格式
if cookies:
    await context.add_cookies(cookies)
```

#### 4.3 Stealth 反指纹

```python
from playwright_stealth import Stealth
await Stealth().apply_stealth_async(page)
```

#### 4.4 三层采集策略

| 层级 | 方式 | 原理 |
|------|------|------|
| Layer 1 | 网络拦截 | 监听 TikTok 内部 API 响应（`api/v1/product` 等），拦截 JSON |
| Layer 2 | window 变量 | `page.evaluate()` 读取 `__NEXT_DATA__` 等全局变量 |
| Layer 3 | DOM 选择器 | 等待渲染完成后用 CSS 选择器提取标题/价格/图片等 |

#### 4.5 CAPTCHA 处理（核心新增）

```python
is_captcha = "security" in page_title.lower() or "captcha" in page_title.lower()

if is_captcha:
    if not headless:
        # 有头模式：等待用户在弹出窗口手动过验证，最多 120 秒
        await page.wait_for_function(
            """() => {
                const t = document.title.toLowerCase();
                return !t.includes('security') && !t.includes('captcha');
            }""",
            timeout=120_000,
        )
        # 验证通过，继续采集...
    else:
        # 无头模式：直接报错，给出三条解决建议
        raise RuntimeError("触发 CAPTCHA 安全验证。解决方案：①代理 ②Cookie ③有头模式")
```

---

### 5. `backend/app/api/v1/settings.py`（新增文件）

Cookie 和代理的**在线管理 API**，无需重启服务器即可更新配置。

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/settings/crawl` | 获取当前采集配置 |
| POST | `/api/v1/settings/crawl/cookies` | 更新 Cookie |
| POST | `/api/v1/settings/crawl/proxy` | 更新代理 |
| DELETE | `/api/v1/settings/crawl/cookies` | 清除 Cookie |

特性：
- 支持 JSON 和 `key=value` 两种 Cookie 格式
- 更新后同时写入 `.env` 文件（持久化）并刷新运行时 `lru_cache`
- 代理格式校验（必须以 `http://` 或 `socks5://` 开头）

---

### 6. `backend/app/api/v1/__init__.py`

注册 settings router：

```diff
- from app.api.v1 import products, pdd, profit, export, auth, tasks
+ from app.api.v1 import products, pdd, profit, export, auth, tasks, settings
  ...
+ router.include_router(settings.router)
```

---

### 7. `frontend/src/api/products.js`

新增 `settingsApi`：

```javascript
export const settingsApi = {
  getConfig:     ()       => http.get('/settings/crawl'),
  updateCookies: (cookies) => http.post('/settings/crawl/cookies', { tiktok_cookies: cookies }),
  updateProxy:   (proxy)   => http.post('/settings/crawl/proxy',   { tiktok_proxy: proxy }),
  clearCookies:  ()        => http.delete('/settings/crawl/cookies'),
}
```

---

### 8. `frontend/src/views/BatchImport.vue`

右侧新增**「采集配置」卡片**：

- Cookie 未配置时显示橙色警告横幅
- Cookie 已配置时显示绿色成功横幅
- 「配置 TikTok Cookie」按钮 → 弹窗，含获取步骤说明
- 「配置代理」按钮 → 弹窗，支持 HTTP/SOCKS5 代理
- 「清除 Cookie」按钮（在 Cookie 弹窗内）
- 页面加载时自动读取当前配置状态

---

## 绕过 CAPTCHA 的三种方案

### 方案 A：有头模式 + 手动过验证（当前默认，立即可用）

```
.env: TIKTOK_HEADLESS=False

流程：
导入链接 → Chromium 弹出 → CAPTCHA 出现
→ 用户手动滑块验证 → 页面跳转 → 自动继续采集
```

### 方案 B：Cookie 注入（一次配置，长期有效）

```
流程：
① 在自己浏览器打开 shop.tiktok.com，通过验证
② F12 → Application → Cookies → 复制字段
③ 在 Global Picker「采集配置」页粘贴保存
④ 后续采集携带已验证 Cookie，不再触发 CAPTCHA
⑤ 可切换为 TIKTOK_HEADLESS=True 无头后台运行
```

### 方案 C：住宅代理（最稳定）

```
.env: TIKTOK_PROXY=http://user:pass@residential-proxy:8080

推荐服务商：BrightData、Oxylabs、SmartProxy
住宅 IP 信誉高，TikTok 不会触发 CAPTCHA
```

---

## 推荐路径

```
短期：方案 A（手动过验证）
        ↓ 通过后复制 Cookie
中期：方案 B（Cookie 注入）→ 切换无头模式
        ↓ Cookie 过期后
长期：方案 C（住宅代理）+ TikTok Open Platform API
```

---

## 测试结果

| 测试 | 结果 | 说明 |
|------|------|------|
| httpx 静态请求 | ❌ | HTTP 200 但无结构化数据 |
| Playwright headless=True | ❌ | CAPTCHA 拦截（IP 问题） |
| Playwright + stealth headless=True | ❌ | CAPTCHA 拦截（IP 问题） |
| Playwright headless=False | ✅ 弹窗等待 | 浏览器窗口弹出，等待手动验证 120s |
| Playwright + Cookie 注入 | ✅（预期） | Cookie 有效时直接跳过验证 |

---

*本次改动不影响已有功能（商品列表、拼多多比价、利润计算、导出），仅升级采集层。*
