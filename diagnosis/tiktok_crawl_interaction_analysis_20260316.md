# TikTok 商品采集 × 系统交互优化分析

> **记录时间**：2026-03-16  
> **来源**：AI 对话分析

---

## 现状诊断

当前系统的采集流程存在一个**断点**：

```
用户粘贴URL → 创建 CrawlTask(pending) → ❓ 没有 Worker 自动执行 → 商品数据为空
```

`CrawlTask` 表设计很好，但**没有实际的抓取执行层**，任务永远停在 `pending`。这是最核心的问题。

---

## 一、采集层：让采集真正跑起来

### 方案A：浏览器插件（最丝滑，推荐优先实现）

这是体验最好的方案 —— 用户在 TikTok Shop **正在浏览的页面**直接一键采集，无需复制链接：

```
用户在浏览器看 TikTok 商品页 
→ 点击插件图标 
→ 插件自动提取页面 DOM 数据（标题/价格/图片/评分/销量）
→ POST 到你的后端 /api/v1/products
→ 页面显示"已添加到 Global Picker ✓"
```

优点：
- **绕过反爬**：数据从用户自己的浏览器读取，不是服务端请求
- **数据完整**：登录态下能拿到更多数据（库存、SKU 详情等）
- **零延迟**：当前页数据，不需要再重新请求

### 方案B：TikTok Open Platform API（已有 Partner Center 权限）

通过 `product_id`（从 URL 中提取）直接调官方 API，返回结构化数据，不需要爬取页面。需要在 Partner Center 申请以下权限：
- `product.read` —— 读取商品信息
- `shop.read` —— 读取店铺信息

### 方案C：Playwright 服务端抓取（当前最可行的过渡方案）

在后端补充一个真正执行抓取的 Worker，对接现有的 `CrawlTask` 状态机：

```python
# 需要新增：backend/app/workers/tiktok_crawler.py
async def crawl_tiktok_product(task_id: int, url: str):
    task.status = "running"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(proxy={"server": "..."})
        page = await browser.new_page()
        await page.goto(url)
        await page.wait_for_selector(".product-title")
        
        title = await page.text_content(".product-title")
        price = await page.text_content(".price")
        # ... 提取其他字段
    
    # 更新 product 表，task.status = "done"
```

---

## 二、与系统交互：让流程真正闭环

### 问题：前端不知道抓取结果

用户导入后看到"成功导入 N 条"，但商品列表里全是空数据（只有 URL），没有标题、价格、图片。需要**实时反馈抓取进度**。

### 解决方案：SSE 实时推送任务状态

在后端新增一个 SSE（Server-Sent Events）接口：

```python
# GET /api/v1/tasks/stream?task_ids=1,2,3
@router.get("/tasks/stream")
async def task_stream(task_ids: str, db: Session = Depends(get_db)):
    async def event_generator():
        ids = [int(i) for i in task_ids.split(",")]
        while True:
            tasks = db.query(CrawlTask).filter(CrawlTask.id.in_(ids)).all()
            data = [{"id": t.id, "status": t.status} for t in tasks]
            yield f"data: {json.dumps(data)}\n\n"
            if all(t.status in ("done", "failed") for t in tasks):
                break
            await asyncio.sleep(2)
    
    return EventSourceResponse(event_generator())
```

前端 `BatchImport.vue` 导入完成后，自动监听状态：

```javascript
// 导入后自动轮询，显示进度条
const eventSource = new EventSource(`/api/v1/tasks/stream?task_ids=${taskIds}`)
eventSource.onmessage = (e) => {
  const tasks = JSON.parse(e.data)
  // 更新进度：X/N 已完成
}
```

### 完整交互流程优化

```
现在：
用户粘贴URL → 导入 → 跳转列表 → 看到空数据 → 困惑

优化后：
用户粘贴URL → 导入 → 页面内显示实时进度条（2/5 抓取完成）
→ 每条完成后行内刷新数据 → 全部完成后一键跳转列表
```

---

## 三、具体代码层面的改进点

### 1. `batch_create_products` 返回 task_id 列表

目前只返回数量，前端无法追踪任务：

```python
# 现在
return {"created": len(created), "duplicates": len(duplicates)}

# 改为
return {
    "created": len(created), 
    "duplicates": len(duplicates),
    "task_ids": [task.id for task in created_tasks]  # 新增
}
```

### 2. `CrawlTask` 补充 `product_id` 外键

目前 `CrawlTask` 没有关联到具体商品，前端拿到 task_id 后无法反查商品：

```python
# crawl_task 表加一列
product_id = Column(BigInteger, ForeignKey("products.id"), nullable=True)
```

### 3. 新增任务状态查询接口

```
GET /api/v1/tasks/{task_id}   → 查单个任务状态
GET /api/v1/tasks?ids=1,2,3  → 批量查询
```

---

## 四、优先级建议

| 优先级 | 任务 | 效果 |
|--------|------|------|
| 🔴 P0 | 实现一个最简单的抓取 Worker（哪怕同步的） | 让数据真正能采集进来 |
| 🔴 P0 | 新增任务状态查询接口 | 前端能知道抓取是否完成 |
| 🟡 P1 | 前端导入后轮询任务状态，显示进度 | 用户体验大幅提升 |
| 🟡 P1 | 对接 TikTok Open API（已有 Partner Center 权限） | 合规稳定，数据准确 |
| 🟢 P2 | 浏览器插件（Chrome Extension） | 最丝滑的采集体验 |
| 🟢 P2 | Celery 异步任务队列 | 支撑批量并发采集 |

---

## 五、最推荐的组合方案

考虑到已有 **TikTok Partner Center 账号**，最合理的路径是：

1. **短期**：先实现 Playwright 抓取 Worker，跑通完整流程（采集→入库→展示）
2. **中期**：申请 Open Platform `product.read` 权限，用官方 API 替换 Playwright，稳定性从 60% 提升到 99%
3. **长期**：做 Chrome 插件，用户在 TikTok 任意页面浏览时一键采集，零摩擦
