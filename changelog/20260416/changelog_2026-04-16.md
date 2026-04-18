# 修改日报 — 2026-04-16

## 一、商品列表与拍照购自动化

**问题**：列表分页与缓存、拍照购需设备可用性检查、多设备并行、拼多多链接可选拉取以提速。

**改动文件**：
- `frontend/src/views/ProductList.vue`、`stores/product.js` — 列表上限 1000、缓存、批量拍照购与同步 ERP 相关交互基础
- `backend/app/workers/pdd_photo/device_manager.py`、`worker.py`、`photo_search_service.py` — 设备归属、并行、任务字段
- `backend/app/api/v1/cloud_phone.py`、`photo_search.py`、`tasks.py` — 云手机与拍照任务 API
- `backend/scripts/alter_photo_search_*.sql` — 拍照任务配置字段
- `docs/2026-04-16.md` — 当日说明文档

## 二、数据与爬虫

**问题**：越南站点样本与爬虫侧小优化。

**改动文件**：
- `backend/app/data/tiktok_VN_product.txt` — 样本数据体量较大
- `backend/app/workers/tiktok_crawler.py` — 采集逻辑调整

---

## 涉及文件汇总

| 文件 | 改动点 |
|------|--------|
| ProductList.vue | 拍照购批量、设备与进度 |
| pdd_photo worker | 多设备与链接可选 |
| tiktok_VN_product.txt | 数据样本 |

---

## 总结

将拍照购从「能跑」推进到「可配置、可并行、可限流」，并与云手机管理对齐；运营可在列表侧控制成本与速度。
