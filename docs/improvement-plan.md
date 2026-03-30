# Global Picker 系统改进计划

> 生成日期：2026-03-31
> 基于全量代码审查（后端 API/服务/模型/Worker + 前端路由/状态/视图 + 数据库/部署）

---

## 一、安全性问题（P0 - 必须修复）

### 1. 水平越权漏洞（IDOR）

多个 API 接口未校验资源归属，已登录用户可操作其他人的数据：

| 文件 | 问题 |
|------|------|
| `backend/app/api/v1/tasks.py` | `query_tasks` / `get_task` / `retry_task` 仅按 `CrawlTask.id` 查询，未按 `Product.user_id` 校验 |
| `backend/app/api/v1/photo_search.py` | `get_task`、`retry_task`、`cancel_task`、`get_task_logs`、`sync_task_images_to_matches` 未校验任务对应商品是否属于当前用户 |
| `backend/app/api/v1/pdd.py` | `update_match`、`delete_match` 仅按 `match_id` 操作，未校验所属 `product_id` 归属 |
| `backend/app/api/v1/profit.py` | `calculate` 未校验 `req.product_id` 及 `pdd_match_id` 归属 |

**修复方案**：统一通过 `product_id → user_id` 或 JOIN 校验资源归属，建议在 service 层封装 `assert_product_owner(db, product_id, user_id)` 复用。

### 2. 采集配置越权

`backend/app/api/v1/settings.py` 允许任意已登录用户修改 TikTok Cookie/代理等全局配置，且直接读写磁盘 `.env` 文件。

**修复方案**：增加角色/权限校验（仅管理员可操作）；配置变更下沉到 service 层并增加审计日志。

### 3. SECRET_KEY 默认值风险

`backend/app/config.py` 中 `SECRET_KEY = "change_me_in_production"`，生产环境未覆盖则 JWT 可被伪造。

**修复方案**：启动时校验 `SECRET_KEY` 非默认值，否则拒绝启动或打印醒目警告。

### 4. 敏感文件

`db_info.txt` 包含 RDS/Redis 密码、私钥等敏感信息。虽已 `.gitignore`，但若曾提交过历史需轮换密钥。

**修复方案**：确认 git 历史中无泄露；如有，使用 `git filter-repo` 清理并轮换所有密钥。

---

## 二、可靠性问题（P1 - 尽快改进）

### 5. 任务恢复不完整

`backend/app/main.py` 的 `_startup_recover()` 仅 `limit(1)` 取一条 queued 任务恢复，多条中断任务时其余不会被自动调度。

**修复方案**：去掉 `limit(1)`，对所有恢复的 queued 任务逐一启动线程（或引入队列机制串行消费）。

### 6. 无自动重试策略

TikTok 爬虫失败后仅递增 `retry_count`，需用户手动触发重试。

**修复方案**：增加可配置的自动重试（如最多 3 次、指数退避），在 worker 内 catch 后自动重新入队。

### 7. 无全局异常处理

未配置 FastAPI 全局 `exception_handler`，未捕获异常可能暴露堆栈信息到客户端。

**修复方案**：
```python
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.exception("Unhandled error")
    return JSONResponse(status_code=500, content={"code": -1, "msg": "服务器内部错误"})
```

### 8. 依赖声明缺失

`backend/app/workers/tiktok_crawler.py` 使用 `playwright_stealth`，但 `requirements.txt` 未声明，新环境部署会 ImportError。

**修复方案**：`requirements.txt` 补充 `playwright-stealth>=1.0.6`。

---

## 三、性能问题（P1）

### 9. N+1 查询

`backend/app/services/export_service.py` 的 `export_products_excel` 遍历商品时逐条查询 `ProfitRecord`，典型 N+1。

**修复方案**：使用 `joinedload` / `selectinload` 预加载，或一次性子查询聚合最新利润再映射。

### 10. Redis 未实际使用

配置了 Redis 连接但业务代码无任何引用，缓存能力完全闲置。

**可用场景**：
- 汇率缓存（避免重复查库）
- 任务状态缓存（减少轮询压力）
- 接口限流（短信发送频率控制）
- 分布式锁（多 Worker 设备调度）

---

## 四、工程化问题（P2 - 中期改进）

### 11. 无数据库迁移工具

仅靠手工 SQL 文件管理 schema 变更，无 Alembic，环境间容易出现 schema 漂移。

**修复方案**：引入 Alembic，基于当前 ORM 模型生成 baseline migration，后续变更通过 `alembic revision --autogenerate`。

### 12. ORM 与数据库不一致

`backend/app/models/product.py` 中 `tiktok_url` 为单列 `unique=True`，但 `db_migration_auth.sql` 已改为 `(user_id, tiktok_url)` 联合唯一。

**修复方案**：模型改为 `UniqueConstraint('user_id', 'tiktok_url', name='idx_user_tiktok_url')`，移除单列 unique。

### 13. 无自动化测试

全项目无 `test_*.py`，无 pytest/vitest 依赖，无测试覆盖。

**修复方案**：
- 后端：引入 pytest + httpx（TestClient），优先覆盖认证、IDOR 校验、核心业务接口
- 前端：引入 vitest，优先覆盖 store 逻辑和 API 封装

### 14. 无 CI/CD 流水线

无 GitHub Actions / GitLab CI 配置，部署依赖手动操作。

**修复方案**：创建 `.github/workflows/ci.yml`，包含 lint、test、build 步骤。

### 15. 无 docker-compose

仅有 `backend/Dockerfile`，无根级 compose 编排完整环境。

**修复方案**：创建 `docker-compose.yml`，编排 backend + frontend + MySQL + Redis，支持一键启动开发/测试环境。

---

## 五、前端问题（P2）

### 16. API 文件过于集中

`frontend/src/api/products.js` 承载了商品、PDD、拍照购、利润、任务、设置、看板等所有接口。

**修复方案**：按模块拆分为 `pdd.js`、`photo-search.js`、`profit.js`、`tasks.js`、`settings.js`、`dashboard.js`。

### 17. 页面缺失

| 缺失页面 | 对应 API |
|----------|---------|
| 账号设置 | `authApi.updateProfile` |
| 设备监控 | `photoSearchApi.getDevices` |
| 任务日志 | `photoSearchApi.getTaskLogs` |
| 404 页面 | 路由通配符 |

### 18. fetchMe 从未调用

auth store 定义了 `fetchMe()` 但全项目无调用，用户信息不会与后端同步刷新。

**修复方案**：在 `AppLayout.vue` 的 `onMounted` 或路由守卫中调用 `fetchMe()`。

### 19. 死代码清理

`frontend/src/components/HelloWorld.vue` 为 Vite 脚手架遗留，全项目无引用，应删除。

### 20. 无代码规范工具

前端无 ESLint / Prettier / TypeScript。

**修复方案**：引入 ESLint + Prettier，配置 `.eslintrc` 和 `.prettierrc`，可选逐步迁移 TypeScript。

---

## 六、运维与可观测性（P2）

### 21. 日志原始

仅 `logging.basicConfig`，无结构化日志、无 request ID、无按环境分级。

**修复方案**：引入 `structlog` 或 `python-json-logger`，中间件注入 request ID，按环境配置日志级别。

### 22. 无监控

仅 `/health` 返回 ok，无 Prometheus 指标、无 APM。

**修复方案**：引入 `prometheus-fastapi-instrumentator`，暴露 `/metrics`；关键业务指标（任务成功率、采集耗时）自定义 Counter/Histogram。

### 23. artifacts 目录硬编码

`backend/app/main.py` 中静态目录为硬编码绝对路径 `/Users/smzdm/global_picker/artifacts`。

**修复方案**：改为 `config.py` 中可配置的 `ARTIFACTS_DIR`，默认相对路径 `./artifacts`。

---

## 实施路线图

| 阶段 | 内容 | 预计工作量 | 优先级 |
|------|------|-----------|--------|
| **第 1 周** | 修复 IDOR 越权 + SECRET_KEY 校验 + 全局异常处理 | 1-2 天 | P0 |
| **第 2 周** | 补全 requirements.txt + 修复 N+1 + 任务恢复改进 | 1-2 天 | P1 |
| **第 3-4 周** | 引入 Alembic + ORM 对齐 + docker-compose | 2-3 天 | P2 |
| **第 5-6 周** | 补充核心接口测试 + CI/CD + 结构化日志 | 3-5 天 | P2 |
| **持续迭代** | 前端页面补全 + Redis 缓存 + 监控接入 + 代码规范 | 按需 | P2 |

---

## 状态跟踪

| # | 改进项 | 优先级 | 状态 |
|---|--------|--------|------|
| 1 | IDOR 越权修复 | P0 | ⬜ 待开始 |
| 2 | 采集配置越权 | P0 | ⬜ 待开始 |
| 3 | SECRET_KEY 校验 | P0 | ⬜ 待开始 |
| 4 | 敏感文件清理 | P0 | ⬜ 待开始 |
| 5 | 任务恢复完善 | P1 | ⬜ 待开始 |
| 6 | 自动重试策略 | P1 | ⬜ 待开始 |
| 7 | 全局异常处理 | P1 | ⬜ 待开始 |
| 8 | 依赖声明补全 | P1 | ⬜ 待开始 |
| 9 | N+1 查询优化 | P1 | ⬜ 待开始 |
| 10 | Redis 缓存启用 | P1 | ⬜ 待开始 |
| 11 | Alembic 迁移 | P2 | ⬜ 待开始 |
| 12 | ORM 与库表对齐 | P2 | ⬜ 待开始 |
| 13 | 自动化测试 | P2 | ⬜ 待开始 |
| 14 | CI/CD 流水线 | P2 | ⬜ 待开始 |
| 15 | docker-compose | P2 | ⬜ 待开始 |
| 16 | 前端 API 拆分 | P2 | ⬜ 待开始 |
| 17 | 前端页面补全 | P2 | ⬜ 待开始 |
| 18 | fetchMe 调用 | P2 | ⬜ 待开始 |
| 19 | 死代码清理 | P2 | ⬜ 待开始 |
| 20 | ESLint/Prettier | P2 | ⬜ 待开始 |
| 21 | 结构化日志 | P2 | ⬜ 待开始 |
| 22 | 监控指标 | P2 | ⬜ 待开始 |
| 23 | artifacts 路径配置化 | P2 | ⬜ 待开始 |
