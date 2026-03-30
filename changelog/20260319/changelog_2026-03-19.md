# 修改日报 — 2026-03-19

## 一、项目初始化（init 提交）

**问题**：项目从零开始搭建，需要完成前后端基础框架、数据库模型、核心业务功能的初始化。

**改动文件**：
- `backend/app/main.py` — FastAPI 应用入口，配置 CORS、路由
- `backend/app/config.py` — 统一配置管理（数据库、TikTok 采集参数等）
- `backend/app/database.py` — 数据库连接与 Session 管理
- `backend/app/models/` — 全部数据模型（Product、CrawlTask、PddMatch、ProfitRecord、User、Device、PhotoSearchTask 等）
- `backend/app/api/v1/` — REST API 路由（商品、任务、拍照购、比价、看板、导出、设置、认证）
- `backend/app/services/` — 业务服务层（商品管理、拍照购、利润计算、汇率、导出）
- `backend/app/workers/tiktok_crawler.py` — TikTok 商品采集爬虫（Playwright）
- `backend/app/workers/pdd_photo/` — 拼多多拍照购自动化（ADB 控制、设备管理、结果解析、截图管理）
- `backend/app/core/security.py` — JWT 认证与密码加密
- `frontend/src/views/` — 前端页面（商品列表、商品详情、批量导入、看板）
- `frontend/src/api/` — API 请求封装
- `frontend/src/components/AppLayout.vue` — 应用布局组件
- `frontend/src/router/index.js` — 前端路由配置
- `frontend/src/stores/product.js` — Pinia 商品状态管理
- `db_schema.sql` / `db_photo_search.sql` — 数据库建表脚本
- `diagnosis/` — 历史诊断与变更记录文档

## 二、TikTok 商品采集功能

**问题**：需要从 TikTok 商品页面自动采集商品信息（标题、价格、销量、图片、店铺等）。

**改动文件**：
- `backend/app/workers/tiktok_crawler.py` — 基于 Playwright 的 TikTok 商品页爬虫，支持 Cookie 认证、代理、商品 JSON 数据解析
- `backend/app/schemas/product.py` — 商品数据校验模型
- `backend/app/services/product_service.py` — 商品 CRUD 与批量导入逻辑

## 三、拼多多拍照购自动化

**问题**：需要通过 ADB 控制云手机，在拼多多 App 中执行拍照购流程，自动搜索并解析比价结果。

**改动文件**：
- `backend/app/workers/pdd_photo/adb_client.py` — ADB 命令封装（连接、截图、UI dump、点击、滑动）
- `backend/app/workers/pdd_photo/device_manager.py` — 设备池管理（获取、锁定、释放、心跳）
- `backend/app/workers/pdd_photo/pdd_photo_flow.py` — 拍照购完整流程编排
- `backend/app/workers/pdd_photo/result_parser.py` — 搜索结果页 XML 解析，提取候选商品
- `backend/app/workers/pdd_photo/worker.py` — 任务执行器（调度设备、执行流程、保存结果）
- `backend/app/workers/pdd_photo/artifact_manager.py` — 截图与日志文件管理

## 四、数据看板与利润计算

**问题**：需要一个看板页面展示项目整体运营指标，以及商品利润计算功能。

**改动文件**：
- `backend/app/api/v1/dashboard.py` — 看板统计 API（商品数、采集任务、比价、利润、设备状态）
- `backend/app/api/v1/profit.py` — 利润计算 API
- `backend/app/services/profit_service.py` — 利润计算服务
- `frontend/src/views/Dashboard.vue` — 看板前端页面

## 涉及文件汇总

| 文件 | 改动点 |
|------|--------|
| `backend/` 全部后端代码 | 项目初始化，含 API、模型、服务、爬虫、拍照购 |
| `frontend/` 全部前端代码 | Vue3 + Vite 项目初始化，含路由、页面、API 封装 |
| `db_schema.sql` / `db_photo_search.sql` | 数据库建表脚本 |
| `diagnosis/` | 历史诊断文档（5个文件） |
| `data_temp/product_info.json` | 商品数据样本 |

---

## 总结

完成了 Global Picker 项目的完整初始化，搭建了 TikTok 商品采集 + 拼多多拍照购比价的全链路系统。前端基于 Vue3 + Element Plus 构建了商品管理、批量导入、数据看板等核心页面；后端基于 FastAPI 实现了商品 CRUD、Playwright 爬虫采集、ADB 云手机自动化拍照购、利润计算等功能。项目具备了从商品发现到比价分析的完整业务闭环能力。
