# 🩺 Global Picker — TikTok 采集管道诊断报告

> **生成时间**：2026-03-16  
> **诊断范围**：采集流程全链路（前端 → API → 数据库 → 抓取执行层）  
> **结论摘要**：采集入口完整，但执行层完全缺失，系统目前处于"会接单但不会干活"的状态。

---

## 一、现状全景图

```
用户操作           前端                    后端 API                  数据库
─────────────────────────────────────────────────────────────────────────────
粘贴 URL     →   BatchImport.vue      →   POST /products/batch   →  crawl_tasks (pending)
                                                                     products (空壳)
                    ↓
             导入成功提示
             "新增 N 条" ✓

                    ↓
             跳转商品列表

             商品列表里看到：
             ┌──────────────────────────────────────────────────────┐
             │  图片：[空]   标题：（待抓取）   价格：0   销量：0   │  ← 永远如此
             └──────────────────────────────────────────────────────┘

```

**核心问题**：`CrawlTask` 状态永远停在 `pending`，因为**没有任何 Worker 去执行它**。

---

## 二、逐层诊断

### 2.1 前端层 — ✅ 基本完整，有小缺陷

| 文件 | 问题 | 严重程度 |
|------|------|----------|
| `BatchImport.vue` | 导入后无法追踪任务进度，不知道抓取是否完成 | 🟡 中 |
| `BatchImport.vue` | `importResult` 只显示"新增 N 条"，没有 `task_ids` 可轮询 | 🟡 中 |
| `ProductList.vue` | 列表无"抓取状态"列，用户不知道哪些商品还在等待 | 🟡 中 |
| `ProductDetail.vue` | 拼多多匹配完全依赖手动录入，无自动搜索触发 | 🟢 低（设计如此） |

**BatchImport.vue 关键代码段（问题所在）：**

```javascript
// 第 148 行
importResult.value = await productApi.batchImport(urls)
message.success(`导入完成：新增 ${importResult.value.created} 条`)
// 问题：只拿到数量，没有 task_ids，无法追踪后续抓取状态
```

---

### 2.2 API 层 — ✅ 结构完整，接口设计合理

| 接口 | 状态 | 说明 |
|------|------|------|
| `POST /products` | ✅ 正常 | 单条添加，创建 CrawlTask(pending) |
| `POST /products/batch` | ✅ 正常 | 批量添加，但返回值未含 task_ids |
| `GET /products` | ✅ 正常 | 分页、过滤、排序完整 |
| `GET /products/{id}` | ✅ 正常 | 商品详情 |
| `PATCH /products/{id}` | ✅ 正常 | 状态/备注更新 |
| `GET /tasks/{id}` | ❌ **缺失** | 任务状态查询接口不存在 |
| `GET /tasks/stream` | ❌ **缺失** | SSE 实时推送接口不存在 |

**product_service.py 关键问题（第 37-55 行）：**

```python
def batch_create_products(db, urls):
    # ...
    return {"created": len(created), "duplicates": len(duplicates)}
    # ❌ 缺失：没有返回 task_ids，前端无法轮询任务状态
```

---

### 2.3 数据库层 — ✅ 表结构设计优秀，一处小缺陷

**表结构评分：**

| 表名 | 评分 | 说明 |
|------|------|------|
| `products` | ⭐⭐⭐⭐⭐ | 字段完整，关联关系清晰 |
| `crawl_tasks` | ⭐⭐⭐⭐ | 状态机设计好，缺少 `product_id` 反向关联 |
| `pdd_matches` | ⭐⭐⭐⭐⭐ | 匹配置信度、确认标志设计完善 |
| `profit_records` | ⭐⭐⭐⭐⭐ | 历史计算记录完整 |

**crawl_task 模型缺失字段（`models/crawl_task.py`）：**

```python
class CrawlTask(Base):
    __tablename__ = "crawl_tasks"
    id = Column(BigInteger, ...)
    url = Column(String(1024), ...)
    status = Column(Enum("pending", "running", "done", "failed"), ...)
    retry_count = Column(SmallInteger, ...)
    error_msg = Column(Text, ...)
    # ❌ 缺失：没有 product_id 字段，拿到 task_id 后无法反查是哪个商品
```

---

### 2.4 抓取执行层 — ❌ 完全缺失（核心断点）

**requirements.txt 中的采集相关依赖：**

```
httpx==0.28.1   # ✅ HTTP 客户端已引入
# ❌ playwright 未引入
# ❌ celery 未引入
# ❌ beautifulsoup4 未引入
```

**整个 `backend/app/` 目录中没有以下任何一个文件：**

- `workers/` 目录（任务执行 Worker）
- `crawlers/` 目录（页面解析逻辑）
- `tasks.py`（Celery 任务定义）
- 任何触发 CrawlTask 状态从 `pending → running → done` 的代码

**这意味着**：即使用户导入了 1000 条链接，系统也只是把 1000 条 `pending` 记录存入数据库，然后什么都不做。

---

### 2.5 TikTok Partner Center — ✅ 账号已具备，未被利用

已在 `tiktok_partner.txt` 中记录了 Partner Center 账号，这是**官方 API 的正规入口**，但当前代码中完全没有接入。

与爬取方案对比：

| 维度 | Playwright 爬取 | Open Platform API |
|------|----------------|-------------------|
| 稳定性 | 60%（反爬风险） | 99%（官方支持） |
| 数据完整性 | 有限（公开信息） | 完整（含库存/SKU） |
| 维护成本 | 高（页面结构变更即失效） | 低（API 版本稳定） |
| 合规性 | 灰色 | 白名单 ✅ |
| 当前可用性 | 需要开发 | 需要申请权限 + 开发 |

---

## 三、问题优先级汇总

```
严重程度   问题描述                                          位置
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔴 P0     抓取 Worker 完全不存在，商品数据永远为空           需新建
🔴 P0     没有任务状态查询接口，前端无法感知进度             需新建 API
🟡 P1     batch_create_products 未返回 task_ids              product_service.py:55
🟡 P1     CrawlTask 缺少 product_id 关联字段                 models/crawl_task.py
🟡 P1     前端导入后无进度反馈，用户体验断层                  BatchImport.vue
🟡 P1     Partner Center API 未接入（已有权限）              待开发
🟢 P2     商品列表无抓取状态列                                ProductList.vue
🟢 P2     拼多多匹配无自动触发（全手动）                      pdd_service.py
🟢 P2     Redis 已配置但仅用于连接配置，未实际缓存任何数据    config.py
```

---

## 四、修复路径建议（最小可行路径）

### Step 1：补齐数据关联（30 分钟）

**`models/crawl_task.py`** — 新增 `product_id` 字段：
```python
product_id = Column(BigInteger, ForeignKey("products.id"), nullable=True)
```

**`services/product_service.py`** — `batch_create_products` 返回 task_ids：
```python
return {
    "created": len(created),
    "duplicates": len(duplicates),
    "task_ids": [t.id for t in created_tasks]
}
```

---

### Step 2：新增任务查询接口（1 小时）

```
GET  /api/v1/tasks/{task_id}      → 单任务状态
GET  /api/v1/tasks?ids=1,2,3      → 批量查询
```

前端导入完成后轮询这两个接口，展示进度条。

---

### Step 3：实现最简抓取 Worker（1-2 天）

**方案 A（推荐过渡）**：用 `httpx` + TikTok Open API

```python
# backend/app/workers/tiktok_crawler.py
async def crawl_by_api(product_id: int, tiktok_product_id: str):
    """通过 TikTok Open Platform API 获取商品信息"""
    # 需先在 Partner Center 申请 product.read 权限
    resp = await client.get(
        "https://open-api.tiktokshop.com/api/products/search",
        params={"product_id": tiktok_product_id},
        headers={"x-tts-access-token": settings.TIKTOK_ACCESS_TOKEN}
    )
    # 解析并更新 products 表，更新 crawl_tasks 状态为 done
```

**方案 B（临时兜底）**：用 `httpx` 直接请求（有反爬风险）

```python
async def crawl_by_http(task_id: int, url: str):
    """直接 HTTP 请求，适用于结构化 API 响应"""
    # TikTok Shop 的商品详情 API
    product_id = extract_product_id(url)
    resp = await client.get(
        f"https://shop.tiktok.com/api/v1/products/{product_id}",
        headers={"User-Agent": "...", "region": "PH"}
    )
```

---

### Step 4：前端添加进度感知（半天）

`BatchImport.vue` 导入完成后，利用 `task_ids` 轮询状态：

```javascript
// 导入完成后，每 3 秒轮询一次任务状态
watch(importResult, async (result) => {
  if (!result?.task_ids?.length) return
  const timer = setInterval(async () => {
    const tasks = await taskApi.batchQuery(result.task_ids)
    progressList.value = tasks
    if (tasks.every(t => ['done', 'failed'].includes(t.status))) {
      clearInterval(timer)
      await store.fetchList()  // 刷新商品列表
    }
  }, 3000)
})
```

---

## 五、长期架构演进

```
当前（无执行层）                     目标（完整管道）
─────────────────            ──────────────────────────────────────
前端 → API → DB              前端 → API → DB
                                      ↓
                              Celery Worker (Redis Broker)
                                      ↓
                         ┌────────────┴────────────┐
                         ↓                         ↓
                  TikTok Open API          Playwright（兜底）
                  (官方，稳定)             (爬取，高风险)
                         ↓                         ↓
                  更新 products 表          更新 products 表
                  更新 crawl_tasks → done   更新 crawl_tasks → done
                         ↓
                  触发自动以图搜图（可选）
                         ↓
                  写入 pdd_matches（候选）
```

---

## 六、采集体验最终形态（Chrome 插件）

当上述后端采集链路稳定后，可进一步开发 Chrome Extension：

```
用户在 TikTok Shop 商品页浏览
        ↓
点击插件图标（悬浮按钮）
        ↓
插件从当前页面 DOM 提取数据（无需服务端请求，绕过反爬）
        ↓
POST 到 /api/v1/products
        ↓
页面内显示"✓ 已添加到 Global Picker"
```

**优势**：
- 数据来自用户已登录的浏览器，信息最完整
- 完全绕过服务端反爬检测
- 操作摩擦为零（无需复制粘贴 URL）

---

*本报告基于代码静态分析生成，不含运行时诊断数据。*  
*如需进一步诊断特定模块，请告知。*
