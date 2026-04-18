# 修改日报 — 2026-04-15

## 一、采集与部署能力增强

**问题**：需在服务端跑通 TikTok 商品采集（含验证码场景）、云手机与拍照购链路，并完善部署依赖。

**改动文件**：
- `backend/requirements.txt`、`backend/.env.example`、`scripts/deploy-prod.sh` — Python 依赖与生产部署脚本补充
- `backend/app/config.py` — 无头采集等配置
- `backend/app/workers/tiktok_crawler.py`、`tiktok_captcha_solver.py`、`image_captcha_solver.py` — Playwright 采集、滑块验证码处理
- `backend/app/services/product_service.py`、`api/v1/products.py` — 商品录入与去重等
- `backend/app/data/tiktok_security_check.txt` — 安全校验相关数据
- `frontend/src/views/ProductList.vue`、`BatchImport.vue`、`utils/crawlTask.js` — 列表采集与任务展示

## 二、数据库

**问题**：采集任务状态需扩展。

**改动文件**：
- `db_schema.sql`、迁移脚本 `add_crawl_task_status_detail_column.py` — 任务状态明细字段

---

## 涉及文件汇总

| 文件 | 改动点 |
|------|--------|
| backend/workers、tiktok_crawler | 无头采集、验证码、Cookie |
| frontend ProductList | 列表采集交互 |
| deploy / requirements | 依赖与部署 |

---

## 总结

打通「列表页采集 + 验证码 + 云手机/拍照购」主路径，服务端可无人值守跑页面级采集，为后续批量运营打基础。部署脚本与依赖同步，降低环境漂移风险。
