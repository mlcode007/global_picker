# 改动记录 — 数据看板功能

> **日期**：2026-03-19  
> **目标**：新增数据看板页面，一屏总览项目关键运营指标与功能模块状态

---

## 新增文件

### `backend/app/api/v1/dashboard.py`
**看板统计 API，提供 1 个聚合接口。**

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/dashboard/stats` | 返回全部看板统计数据（单次请求） |

主要统计维度：

| 维度 | 字段 | 说明 |
|------|------|------|
| 商品概览 | `products.total / today / week` | 商品总数、今日新增、本周新增 |
| 选品状态 | `products.by_status` | pending / selected / abandoned 各自数量 |
| 区域分布 | `products.by_region` | PH / MY / TH / SG / ID / VN 各区域商品数 |
| 采集任务 | `crawl_tasks.by_status / total` | pending / running / done / failed 分布 |
| 拼多多比价 | `pdd_matches.total / confirmed / match_rate / by_source` | 匹配总数、确认数、匹配率、按来源分布 |
| 利润分析 | `profit.avg_profit / avg_profit_rate / positive_count / high_margin_count` | 平均利润、平均利润率、盈利数、高利润率(≥20%)数 |
| 拍照购 | `photo_search.total / success / success_rate / by_status` | 任务总数、成功率、各状态分布 |
| 设备 | `devices.total / by_status` | 设备总数、idle / busy / offline / error 分布 |
| 7日趋势 | `daily_trend[]` | 近 7 天每日新增商品数 |
| 最近商品 | `recent_products[]` | 最新 8 条商品摘要（含图片、价格、区域、状态） |

实现要点：
- 过滤已软删除商品（`is_deleted == 0`）
- 利润取每个商品最新一条 `ProfitRecord`（子查询 `MAX(id) GROUP BY product_id`）
- 匹配率 = 有匹配的商品数 / 商品总数（`COUNT(DISTINCT product_id)`）
- 使用 `datetime.now()` 而非 `utcnow()`，匹配数据库本地时区
- 返回值使用 `Response(data=...)` 包装，符合项目统一响应格式 `{code: 0, message: "ok", data: ...}`

---

### `frontend/src/views/Dashboard.vue`
**数据看板前端视图（690 行），纯 CSS 可视化，无第三方图表库依赖。**

页面布局（4 行卡片）：

```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│  商品总数    │  拼多多匹配  │  平均利润率  │  采集任务    │
│  today/week │  匹配率/确认 │  盈利/高利润 │  运行/失败   │
├─────────────┼─────────────┼─────────────┤─────────────┤
│ 商品选品状态  │  销售区域分布 │  比价来源分布              │
│ 进度条+数量  │  国旗+进度条  │  图标+数量+汇总            │
├─────────────┴──────┬──────┴──────┬──────┴─────────────┤
│  近7天新增趋势      │  拍照购任务  │  设备状态            │
│  CSS柱状图          │  成功率+明细 │  状态点+设备总数      │
├────────────────────┼────────────┴──────────────────────┤
│  利润分析概览        │  最近添加的商品（表格）             │
│  5项指标卡片        │  图片+标题+价格+区域+状态+时间      │
└────────────────────┴──────────────────────────────────┘
```

技术细节：
- 使用 Ant Design Vue 组件：`a-statistic`、`a-progress`、`a-badge`、`a-tag`、`a-table`、`a-image`
- 趋势图为纯 CSS 柱状图（`flex` + 动态 `height%`），无需 ECharts
- 所有数据从 `dashboardApi.getStats()` 单次请求获取
- 响应式布局：`a-col :xs="24" :sm="12" :lg="6/8/12"`
- 复用 `utils/index.js` 中的 `STATUS_MAP`、`REGION_MAP`、`profitRateColor`

---

## 修改文件

### `backend/app/api/v1/__init__.py`

注册 dashboard 路由：

```diff
- from app.api.v1 import products, pdd, profit, export, auth, tasks, settings, photo_search
+ from app.api.v1 import products, pdd, profit, export, auth, tasks, settings, photo_search, dashboard
  ...
+ router.include_router(dashboard.router)
```

---

### `frontend/src/api/products.js`

新增 `dashboardApi` 导出：

```javascript
export const dashboardApi = {
  getStats: () => http.get('/dashboard/stats'),
}
```

---

### `frontend/src/router/index.js`

**两处改动：**

1. 根路径默认重定向改为看板
2. 新增 Dashboard 路由

```diff
  children: [
-   { path: '', redirect: '/products' },
+   { path: '', redirect: '/dashboard' },
+   { path: 'dashboard', name: 'Dashboard', component: () => import('@/views/Dashboard.vue'), meta: { title: '数据看板' } },
    { path: 'products', ... },
    ...
  ]
```

---

### `frontend/src/components/AppLayout.vue`

**两处改动：**

1. 侧边栏菜单新增"数据看板"入口（置于首位）
2. 引入 `DashboardOutlined` 图标

```diff
  import {
+   DashboardOutlined,
    UnorderedListOutlined,
    ImportOutlined
  } from '@ant-design/icons-vue'
```

```diff
  <a-menu ...>
+   <a-menu-item key="Dashboard">
+     <template #icon><DashboardOutlined /></template>
+     数据看板
+   </a-menu-item>
    <a-menu-item key="ProductList">
    ...
```

---

## Bug 修复记录

### 1. API 响应格式不匹配（首次加载报错"请求失败"）

**现象**：看板页面加载后所有数据为 0，顶部弹出"请求失败"错误提示。

**根因**：项目统一响应拦截器（`request.js`）要求 API 返回 `{code: 0, data: ...}` 格式，检查 `data.code !== 0` 则判定失败。dashboard API 初版直接返回原始 dict，无 `code` 字段，`undefined !== 0` 触发错误分支。

**修复**：

```diff
# backend/app/api/v1/dashboard.py
+ from app.schemas.common import Response
  ...
- return { "products": { ... }, ... }
+ return Response(data={ "products": { ... }, ... })
```

```diff
# frontend/src/views/Dashboard.vue
- const { data } = await dashboardApi.getStats()
- stats.value = data
+ stats.value = await dashboardApi.getStats()
```

### 2. 时区不一致导致"今日新增"统计偏差

**现象**：`daily_trend` 日期比实际日期少一天，"今日新增"数据不准。

**根因**：使用 `datetime.utcnow()` 计算 `today_start`，而数据库 `created_at` 使用服务器本地时间（UTC+8），导致时间窗口偏移 8 小时。

**修复**：

```diff
- now = datetime.utcnow()
+ now = datetime.now()
```

---

## 文件变更清单

| 操作 | 文件路径 | 行数 |
|------|----------|------|
| **新增** | `backend/app/api/v1/dashboard.py` | 185 |
| **新增** | `frontend/src/views/Dashboard.vue` | 690 |
| 修改 | `backend/app/api/v1/__init__.py` | +2 行 |
| 修改 | `frontend/src/api/products.js` | +4 行 |
| 修改 | `frontend/src/router/index.js` | +2 行，改 1 行 |
| 修改 | `frontend/src/components/AppLayout.vue` | +5 行，改 1 行 |

---

## 看板指标说明

| 指标 | 计算方式 | 关注点 |
|------|----------|--------|
| 商品总数 | `COUNT(products WHERE is_deleted=0)` | 整体规模 |
| 今日/本周新增 | `created_at >= today/week_start` | 运营节奏 |
| 匹配率 | `有匹配商品数 / 商品总数` | 比价覆盖度 |
| 平均利润率 | 每个商品最新利润记录的 `profit_rate` 平均值 | 选品质量 |
| 高利润率 | `profit_rate >= 20%` 的商品数 | 优质选品 |
| 拍照购成功率 | `success / total` | 自动化效率 |
| 采集任务状态 | 按 `pending/running/done/failed` 分组 | 系统健康度 |
| 设备状态 | 按 `idle/busy/offline/error` 分组 | 设备可用性 |
