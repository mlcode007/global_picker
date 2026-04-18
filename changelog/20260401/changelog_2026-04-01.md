# 修改日报 — 2026-04-01

## 一、服务器部署上线

**问题**：项目代码仅在本地开发，未部署到线上服务器，无法远程访问使用。

**改动文件**：
- `dev/deploy_server.md` — 完整记录服务器部署命令（系统依赖、Python 虚拟环境、Node.js、Nginx、systemd 服务）
- `dev/global_picker_nginx.conf` — Nginx 站点配置（前端静态文件 + 后端 API 反向代理）
- `dev/global_picker_backend.service` — systemd 服务单元文件
- `dev/fix_env.sh` — 生产环境 .env 修复脚本
- `backend/requirements.txt` — 补充 `playwright-stealth` 依赖（服务器采集报错修复）

## 二、修复商品列表刷新报错 [object Object]

**问题**：刷新商品列表页面时，顶部弹出 `[object Object]` 错误提示。原因是 FastAPI 返回 422 验证错误时，`detail` 字段为数组对象，前端拦截器直接传给 `message.error()` 导致显示为 `[object Object]`。

**改动文件**：
- `frontend/src/api/request.js` — 错误拦截器中对 `detail` 字段做类型判断，仅在 `typeof detail === 'string'` 时使用
- `backend/app/main.py` — 新增 `RequestValidationError` 和 `ResponseValidationError` 全局异常处理器，统一返回 `{code, message, data}` 格式，并记录详细错误日志

## 三、商品列表页 UI 优化与拼多多匹配展开

**问题**：商品列表页图片过小（56px）看不清商品，拼多多匹配商品需要手动点击才能查看，操作效率低。

**改动文件**：
- `frontend/src/views/ProductList.vue` — 
  - TikTok 商品图从 56px 放大到 80px，拼多多匹配图从 40px 放大到 56px
  - 拼多多匹配行默认全部展开，无需手动点击
  - 新增"拼多多匹配"列显示匹配数量，支持折叠/展开切换
  - 展开行内显示拼多多商品的销量、拼多多商品页链接等详细信息
  - 整体排版优化：间距、圆角、hover 效果

## 四、商品列表新增预估利润列与自动计算

**问题**：用户无法在列表页直接看到每个商品的利润情况，需要逐个进入详情页手动计算，选品效率低。

**改动文件**：
- `backend/app/models/product.py` — Product 模型新增 `estimated_profit`（预估利润）和 `profit_rate`（利润率）字段
- `backend/app/schemas/product.py` — ProductOut 响应 schema 新增这两个字段
- `backend/app/services/pdd_service.py` — 新增 `_update_product_profit()` 函数，在设置主参照（`add_pdd_match` / `update_pdd_match`）时自动计算利润（TikTok 人民币价 - 拼多多价）并写入 products 表
- `frontend/src/views/ProductList.vue` — 新增"预估利润"列，显示利润金额和利润率百分比，颜色根据利润高低变化（绿 ≥20 / 黄 ≥0 / 红 <0）
- `frontend/src/stores/product.js` — store filters 新增价格和利润范围筛选参数

**数据库迁移**：products 表新增 `estimated_profit DECIMAL(12,2)` 和 `profit_rate DECIMAL(7,4)` 两列及索引。

## 五、商品列表新增价格与利润范围筛选

**问题**：商品列表缺少按价格和利润筛选的能力，用户无法快速定位高利润或特定价格区间的商品。

**改动文件**：
- `backend/app/api/v1/products.py` — 商品列表 API 新增 `price_cny_min/max`、`profit_min/max` 四个可选查询参数
- `backend/app/services/product_service.py` — `get_products` 函数新增对应的数据库过滤条件
- `frontend/src/views/ProductList.vue` — 筛选栏新增"TikTok¥"和"利润¥"两组范围输入框
- `frontend/src/stores/product.js` — filters 新增 `price_cny_min/max` 和 `profit_min/max`

## 涉及文件汇总

| 文件 | 改动点 |
|------|--------|
| `dev/deploy_server.md` | 服务器部署命令记录 |
| `dev/global_picker_nginx.conf` | Nginx 配置 |
| `dev/global_picker_backend.service` | systemd 服务配置 |
| `dev/fix_env.sh` | 生产环境修复脚本 |
| `backend/requirements.txt` | 补充 playwright-stealth 依赖 |
| `backend/app/main.py` | 全局异常处理器（422/500 统一格式） |
| `backend/app/models/product.py` | 新增 estimated_profit、profit_rate 字段 |
| `backend/app/schemas/product.py` | ProductOut 新增利润字段 |
| `backend/app/api/v1/products.py` | 商品列表 API 新增价格/利润筛选参数 |
| `backend/app/api/v1/pdd.py` | 新增批量获取匹配接口 |
| `backend/app/services/pdd_service.py` | 设置主参照时自动计算利润、批量查询 |
| `backend/app/services/product_service.py` | get_products 支持价格/利润范围过滤 |
| `frontend/src/api/request.js` | 修复 [object Object] 错误提示 |
| `frontend/src/stores/product.js` | filters 新增筛选参数 |
| `frontend/src/views/ProductList.vue` | 图片放大、默认展开、利润列、范围筛选 |

---

## 总结

今日完成项目首次服务器部署上线（阿里云 ECS + Nginx + systemd），修复了商品列表页刷新报错问题。核心功能升级：商品列表页新增预估利润自动计算与展示，设置主参照时自动写入利润数据，新增价格和利润范围筛选，大幅提升选品决策效率。同时优化了列表页 UI，放大商品图片、默认展开拼多多匹配行，减少操作步骤。
