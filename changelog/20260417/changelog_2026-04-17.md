# 修改日报 — 2026-04-17

## 一、商品删除与列表筛选

**问题**：需支持批量/单条删除入口与接口；列表需按利润率等维度筛选。

**改动文件**：
- `frontend/src/views/ProductList.vue`、`backend/app/api/v1/products.py` — 删除交互与路由
- `backend/app/services/product_service.py` — 利润等筛选条件

## 二、导出与用户偏好

**问题**：Excel 导出需可选列、账号级偏好、大文件超时与鉴权。

**改动文件**：
- `backend/app/services/export_service.py`、`api/v1/export.py`、`schemas/export_schema.py` — 导出列与逻辑
- `backend/app/api/v1/user.py`、`models/user.py`、迁移 — 用户偏好列存储
- `frontend/src/views/ProductList.vue`、`ProductDetail.vue`、`BatchImport.vue`、`api/products.js`、`request.js` — 导出 UI 与请求超时

---

## 涉及文件汇总

| 文件 | 改动点 |
|------|--------|
| export_service.py | 导出列与业务字段 |
| ProductList.vue | 删除、筛选、导出弹窗 |
| user 偏好迁移 | 列选择持久化 |

---

## 总结

列表从「看数」扩展到「删、筛、导出」闭环；导出支持个性化列并服务运营对账与归档需求。
