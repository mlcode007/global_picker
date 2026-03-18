# 改动记录 — TikTok 采集管道补全

> **日期**：2026-03-16  
> **目标**：打通"批量粘贴 URL → 后台自动采集 → 前端实时进度"完整链路

---

## 新增文件

### `backend/app/workers/__init__.py`
空包文件，使 `workers` 目录成为 Python 包。

---

### `backend/app/workers/tiktok_crawler.py`
**TikTok 商品采集 Worker 核心模块。**

主要逻辑：
- `extract_product_id(url)` — 从 URL 正则提取商品 ID
- `extract_region(url)` — 从 URL 提取地区参数（默认 PH）
- `_fetch_page_html(url)` — 用 `httpx` 携带浏览器 Headers 请求页面
- `_extract_next_data(html)` — 解析页面内嵌 `__NEXT_DATA__` JSON（TikTok Shop 基于 Next.js）
- `_parse_product_from_next_data(raw)` — 多路径尝试提取商品数据（兼容不同版本页面结构）
- `_apply_product_data(product, data)` — 将解析结果写入 `Product` 模型（标题、价格、销量、评分、店铺、图片、品类）
- `run_crawl_task(task_id)` — **后台任务入口**，独立创建 DB Session，驱动 `CrawlTask` 状态机：`pending → running → done / failed`，失败时记录 `error_msg` 并自增 `retry_count`

> 升级路径注释：预留了接入 TikTok Open Platform API 和 Playwright 的替换说明。

---

### `backend/app/api/v1/tasks.py`
**抓取任务状态查询 API，新增 3 个接口。**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/tasks?ids=1,2,3` | 批量查询任务状态（前端轮询用） |
| GET | `/api/v1/tasks/{task_id}` | 查询单个任务状态 |
| POST | `/api/v1/tasks/{task_id}/retry` | 手动重试失败任务 |

---

## 修改文件

### `backend/app/services/product_service.py`

**函数**：`batch_create_products`

```diff
- return {"created": len(created), "duplicates": len(duplicates)}
+ return {"created": len(created), "duplicates": len(duplicates), "task_ids": task_ids}
```

新增 `task_ids` 列表字段，记录本次批量导入创建的所有 `CrawlTask.id`，供后续轮询。

---

### `backend/app/api/v1/products.py`

**两处改动：**

1. 引入 `BackgroundTasks` 和 `run_crawl_task`
2. 单条添加（`POST /products`）和批量导入（`POST /products/batch`）均在响应返回后，自动将新任务加入后台执行队列

```python
# 单条
background_tasks.add_task(run_crawl_task, task.id)

# 批量
for task_id in result.get("task_ids", []):
    background_tasks.add_task(run_crawl_task, task_id)
```

---

### `backend/app/api/v1/__init__.py`

注册 tasks router：

```diff
- from app.api.v1 import products, pdd, profit, export, auth
+ from app.api.v1 import products, pdd, profit, export, auth, tasks
  ...
+ router.include_router(tasks.router)
```

---

### `frontend/src/api/products.js`

新增 `taskApi` 导出：

```javascript
export const taskApi = {
  queryBatch: (ids) => http.get('/tasks', { params: { ids: ids.join(',') } }),
  get: (id) => http.get(`/tasks/${id}`),
  retry: (id) => http.post(`/tasks/${id}/retry`),
}
```

---

### `frontend/src/views/BatchImport.vue`

**改动幅度最大，重构了导入后的交互逻辑。**

#### 新增 `<template>` 区块
原"导入结果"卡片替换为**采集进度面板**，包含：
- 整体进度条（显示 X/N 完成，自动计算百分比）
- 每条任务的状态行：状态图标 + 商品 ID + 状态标签 + 错误提示 Tooltip + 失败重试按钮
- 全部完成后显示"前往商品列表"按钮

#### 新增 `<script setup>` 逻辑

| 变量/函数 | 说明 |
|-----------|------|
| `taskList` | 当前批次任务列表，轮询时实时更新 |
| `doneCount` | 已完成（done/failed）任务数 |
| `crawlPercent` | 进度百分比 |
| `crawlDone` | 是否全部完成 |
| `crawlProgressStatus` | 进度条状态（active/success/exception） |
| `startPolling(ids)` | 启动轮询，每 2.5 秒请求一次任务状态 |
| `stopPolling()` | 停止轮询，组件卸载时自动调用 |
| `retryTask(task)` | 对失败任务调用重试接口 |
| `statusIconComp/Color/TagColor/Label` | 四个状态展示辅助函数 |
| `truncateUrl(url)` | 将完整 URL 显示为"商品 {ID}"短文本 |

#### 新增 `<style scoped>`
`.task-list` / `.task-row` / `.task-url` 样式，限高可滚动列表。

---

## 完整数据流（改动后）

```
用户粘贴多条 URL
        ↓
POST /products/batch
        ↓
DB: 创建 products（空壳）+ crawl_tasks（pending）
返回: { created: N, duplicates: M, task_ids: [1,2,...N] }
        ↓
前端进度面板出现，开始每 2.5s 轮询 GET /tasks?ids=...
        ↓                              ↓
BackgroundTasks 并发触发           轮询拿到最新 status
run_crawl_task(task_id) × N              ↓
        ↓                      每条状态实时更新到 task-row
httpx 请求 TikTok 页面
        ↓
解析 __NEXT_DATA__ JSON
        ↓
写入 products 字段
        ↓
crawl_tasks.status → done / failed
        ↓
轮询检测到全部完成 → 停止轮询 → 显示"前往商品列表"
```

---

## 注意事项

1. **httpx 抓取成功率**：TikTok Shop 页面为 Next.js SSR，`__NEXT_DATA__` 通常可解析；但部分地区/版本可能返回空，需后续接入 Playwright 或 Open API 提升成功率。
2. **并发限制**：`BackgroundTasks` 在同一进程内并发，批量导入数量较多时建议限制在 20 条以内，或改用 Celery 队列控制并发数。
3. **重试机制**：`retry_count` 已记录，前端可手动触发重试；后续可加定时任务自动重试 `retry_count < 3` 的失败任务。
