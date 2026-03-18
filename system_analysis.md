# Global Picker 系统设计方案分析与建议

> 文档日期：2026-03-16

---

## 一、整体评估

该系统的核心价值清晰——**跨平台价差套利工具**，目标用户是选品团队。设计思路合理，但有几个关键风险点需要提前规避。

---

## 二、主要风险与挑战

### 🔴 高风险：数据抓取合规性

**TikTok Shop 抓取**
- TikTok Shop 有严格的反爬机制（签名验证、设备指纹、IP 封锁）
- 直接抓取网页极易被封，建议优先考虑：
  - 使用 [TikTok Shop Open Platform](https://partner.tiktokshop.com/) 官方 API（有商家/代理权限）
  - 或采用浏览器自动化（Playwright/Selenium）配合代理池，稳定性较差

**拼多多抓取**
- 拼多多同样有强力反爬，且无公开搜索 API
- 以图搜图依赖第三方图片搜索服务（如必应图片搜索、百度图片搜索），精准度有限
- 建议预留人工补录通道作为兜底

### 🟡 中风险：以图搜图精准度

- 自动匹配同款商品准确率通常只有 60-70%
- 建议设计为"推荐 + 人工确认"双模式，而非全自动

### 🟡 中风险：数据实时性

- 拼多多价格波动频繁，缓存时间不能太长
- Redis 缓存建议设置较短 TTL（30 分钟以内）

---

## 三、技术架构建议

### 当前方案调整建议

```
原方案：前端 → 后端 API → 直接抓取
建议：  前端 → 后端 API → 任务队列（Celery + Redis）→ 异步抓取 Worker
```

**为什么需要任务队列？**
- 抓取是耗时操作（5-30 秒），同步接口会超时
- 支持批量导入时并发控制，避免触发反爬
- 失败可自动重试

### 推荐技术栈

| 层级 | 推荐 | 说明 |
|------|------|------|
| 后端框架 | FastAPI | 高性能，原生异步，自动生成接口文档 |
| 任务队列 | Celery + Redis | 异步抓取，避免请求超时 |
| 数据库 | MySQL（已有） | 主数据存储，阿里云 RDS |
| 缓存 | Redis | 价格缓存 + 任务队列 Broker |
| 抓取工具 | Playwright | 处理 JS 渲染页面 |
| 图片搜索 | 百度图片 / 必应图片搜索 | 以图搜图找拼多多同款 |
| 前端 | Vue 3 + Ant Design Vue | 适合数据管理后台 |
| 部署 | Docker Compose | 一键部署，便于运维 |

---

## 四、数据库设计建议

设计文档中未提及数据库表结构，建议至少包含以下核心表：

```sql
-- 商品主表
products
  - id, tiktok_url, title, price, sales, rating
  - shop_name, image_url, region
  - status ENUM('pending', 'selected', 'abandoned')
  - created_at, updated_at

-- 拼多多匹配结果
pdd_matches
  - id, product_id (FK)
  - pdd_title, pdd_price, pdd_sales, pdd_shop
  - pdd_image_url, pdd_product_url
  - match_confidence FLOAT   -- 匹配置信度 0~1
  - is_confirmed TINYINT(1)  -- 人工确认标志
  - created_at

-- 利润计算记录
profit_records
  - id, product_id (FK)
  - tiktok_price, pdd_price
  - logistics_cost, platform_fee  -- 可扩展成本字段
  - profit, profit_rate
  - calculated_at

-- 抓取任务表
crawl_tasks
  - id, url, task_type ENUM('tiktok', 'pdd')
  - status ENUM('pending', 'running', 'done', 'failed')
  - retry_count, error_msg
  - created_at, updated_at
```

---

## 五、功能优先级建议

建议按以下顺序迭代开发，避免一次性铺开：

### Phase 1 — MVP（预计 2-3 周）
- [ ] 数据库表结构创建
- [ ] TikTok 商品链接手动粘贴 / 批量导入（先跑通流程）
- [ ] 商品列表、详情页基础前端
- [ ] 简单利润计算模块

### Phase 2 — 自动化（预计 2-3 周）
- [ ] TikTok 自动抓取（验证可行性，配合代理池）
- [ ] 拼多多以图搜图（接入第三方图搜服务）
- [ ] Celery 任务队列异步化

### Phase 3 — 增强功能（持续迭代）
- [ ] 销量趋势图
- [ ] 筛选 / 排序 / 收藏 / 导出报表
- [ ] 多语言切换（中 / 英）
- [ ] 日志监控与异常报警

---

## 六、需要提前明确的问题

1. **TikTok Shop 访问权限**：是否有合作商家账号或 Open Platform API 权限？
2. **拼多多数据来源**：是购买第三方数据服务（如蝉妈妈、魔镜市场），还是自行抓取？
3. **部署环境**：后端需要海外 IP 才能访问 TikTok 菲律宾站点，服务器部署在哪里？
4. **团队并发人数**：影响服务器配置与 Redis 缓存策略。

---

## 七、现有资源确认

| 资源 | 状态 | 备注 |
|------|------|------|
| MySQL RDS | ✅ 已就绪 | 阿里云北京，库名 `global_picker` |
| Redis | ❓ 待确认 | 建议同步开通阿里云 Redis 实例 |
| 服务器 / 容器 | ❓ 待确认 | 建议 ECS 或容器服务部署后端 |
| 前端托管 | ❓ 待确认 | 可用 OSS + CDN 静态托管 |
