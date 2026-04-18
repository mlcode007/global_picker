# 修改日报 — 2026-04-19

## 一、同步 ERP 与选品状态

**问题**：批量「同步 ERP」需在妙手插件侧打开 TikTok 商品页；选品状态需区分「已同步 ERP」。

**改动文件**：
- `frontend/src/views/ProductList.vue` — 同步 ERP 批量流程、间隔随机、进度、成功后 `PATCH` 状态 `erp_synced`
- `backend/app/models/product.py`、`schemas/product.py`、`sql/alter_products_status_add_erp_synced.sql` — 状态枚举扩展
- `backend/app/services/export_service.py` — 导出中文状态文案
- `frontend/src/utils/index.js`、`Dashboard.vue`、`ProductDetail.vue` — 状态展示与看板统计

## 二、Chrome 扩展（妙手采集自动化）

**问题**：需在 TikTok 商品页自动点「集此商品」、验证码/未登录时不误点、失败刷新等。

**改动文件**：
- `chrome-extension/manifest.json`、`content.js`、`background.js` — MV3 内容脚本与关页逻辑

## 三、提示词摘要（当日）

同步 ERP 交互（间隔随机、不跟跳、进度）、弹窗与预开标签策略、浏览器插件采集与状态联动等（详见同目录 `prompts_2026-04-19.md`）。

---

## 涉及文件汇总

| 文件 | 改动点 |
|------|--------|
| ProductList.vue | 同步 ERP + 状态回写 |
| chrome-extension | 页面自动化 |
| product 模型/SQL | erp_synced |

---

## 总结

完成「运营列表 → 打开 TikTok → 插件采集 → 回写已同步 ERP」闭环；扩展侧兼顾验证码与未登录拦截，减少无效关页与误点。
