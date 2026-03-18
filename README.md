# Global Picker

---

## 技术栈


| 层级  | 技术                                                       |
| --- | -------------------------------------------------------- |
| 前端  | Vue 3 + Vite 8 + Ant Design Vue 4 + Pinia + Vue Router 4 |
| 后端  | FastAPI + SQLAlchemy 2 + Pydantic                        |
| 数据库 | MySQL (阿里云 RDS)                                          |
| 缓存  | Redis (阿里云 Redis)                                        |
| 采集  | Playwright（浏览器自动化）                                       |
| 拍照购 | ADB + Android 设备（拼多多 App 拍照搜索）                           |
| 认证  | JWT (python-jose) + bcrypt                               |


---

## 快速开始

### 1. 克隆项目

```bash
git clone <repo-url>
cd global_picker
```

### 2. 配置环境变量

后端依赖 `backend/.env` 文件

首次部署需手动创建：

```bash
cp backend/.env.example backend/.env
# 编辑 .env 填入实际配置
```

### 3. 初始化数据库

执行项目根目录下的 SQL 建表脚本：

```bash
mysql -h <host> -u <user> -p <db_name> < db_schema.sql
mysql -h <host> -u <user> -p <db_name> < db_photo_search.sql
```

### 4. 启动后端

```bash
cd backend
pip install -r requirements.txt
playwright install chromium
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 5. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 [http://localhost:5173](http://localhost:5173)

---

## 环境变量配置说明

在 `backend/.env` 中配置以下变量：

### 数据库 (MySQL)


| 变量               | 说明         | 示例                   | 必填          |
| ---------------- | ---------- | -------------------- | ----------- |
| `MYSQL_HOST`     | MySQL 主机地址 | `127.0.0.1` 或 RDS 地址 | 是           |
| `MYSQL_PORT`     | MySQL 端口   | `3306`               | 否 (默认 3306) |
| `MYSQL_USER`     | MySQL 用户名  | `root`               | 是           |
| `MYSQL_PASSWORD` | MySQL 密码   | `your_password`      | 是           |
| `MYSQL_DB`       | 数据库名       | `global_picker`      | 是           |


### 缓存 (Redis)


| 变量               | 说明               | 示例                       | 必填          |
| ---------------- | ---------------- | ------------------------ | ----------- |
| `REDIS_HOST`     | Redis 主机地址       | `127.0.0.1` 或 Redis 实例地址 | 是           |
| `REDIS_PORT`     | Redis 端口         | `6379`                   | 否 (默认 6379) |
| `REDIS_USER`     | Redis 用户名（云实例需要） | `r-xxxxx`                | 否           |
| `REDIS_PASSWORD` | Redis 密码         | `your_password`          | 否           |
| `REDIS_DB`       | Redis 数据库编号      | `0`                      | 否 (默认 0)    |


### 应用


| 变量                            | 说明                    | 示例                           | 必填                 |
| ----------------------------- | --------------------- | ---------------------------- | ------------------ |
| `APP_ENV`                     | 运行环境                  | `development` / `production` | 否 (默认 development) |
| `SECRET_KEY`                  | JWT 签名密钥，**生产环境必须修改** | 32 位以上随机字符串                  | 是                  |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token 过期时间（分钟）        | `1440`（即 24 小时）              | 否 (默认 1440)        |


### 跨域 (CORS)


| 变量             | 说明                  | 示例                          | 必填  |
| -------------- | ------------------- | --------------------------- | --- |
| `CORS_ORIGINS` | 允许的前端域名列表 (JSON 数组) | `["http://localhost:5173"]` | 否   |


### TikTok 采集


| 变量                | 说明               | 示例                                                  | 必填           |
| ----------------- | ---------------- | --------------------------------------------------- | ------------ |
| `TIKTOK_PROXY`    | HTTP/SOCKS5 代理地址 | `http://user:pass@host:port` 或 `socks5://host:port` | 否 (留空不使用)    |
| `TIKTOK_COOKIES`  | TikTok 登录 Cookie | 从浏览器 DevTools > Application > Cookies 复制            | 否 (提升采集成功率)  |
| `TIKTOK_HEADLESS` | 浏览器模式            | `True`=无界面后台, `False`=显示窗口(可手动过验证)                  | 否 (默认 False) |


### .env.example 模板

```env
# ── 数据库 ──
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DB=global_picker

# ── Redis ──
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_USER=
REDIS_PASSWORD=
REDIS_DB=0

# ── 应用 ──
APP_ENV=development
SECRET_KEY=change_me_in_production_32chars!!
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# ── 跨域 ──
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

# ── TikTok 采集 ──
TIKTOK_PROXY=
TIKTOK_COOKIES=
TIKTOK_HEADLESS=False
```

---

## 项目结构

```
global_picker/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API 路由 (products, pdd, profit, dashboard...)
│   │   ├── config.py        # Pydantic Settings 配置
│   │   ├── core/            # 安全、认证
│   │   ├── database.py      # SQLAlchemy 连接
│   │   ├── models/          # ORM 模型
│   │   ├── schemas/         # Pydantic 请求/响应模型
│   │   ├── services/        # 业务逻辑层
│   │   └── workers/         # 后台任务 (TikTok 采集、拍照购)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env                 # 参考.env.example
├── frontend/
│   ├── src/
│   │   ├── api/             # Axios 封装
│   │   ├── components/      # 布局组件
│   │   ├── router/          # Vue Router
│   │   ├── stores/          # Pinia 状态
│   │   ├── utils/           # 常量、工具函数
│   │   └── views/           # 页面 (Dashboard, ProductList, ProductDetail, BatchImport)
│   └── package.json
├── diagnosis/               # 改动记录 / 问题诊断
├── .gitignore
└── README.md
```

---

## 功能模块


| 模块        | 说明                                      |
| --------- | --------------------------------------- |
| 数据看板      | 商品总览、选品状态、区域分布、采集任务、比价统计、利润分析、设备状态、7日趋势 |
| 商品管理      | 新增、批量导入 TikTok 链接、列表筛选排序、详情、状态标记、软删除    |
| TikTok 采集 | Playwright 浏览器自动化抓取商品详情、任务重试            |
| 拼多多比价     | 手动添加匹配、拍照购自动匹配、确认/设主参照                  |
| 利润计算      | TikTok 售价 vs 拼多多采购价、汇率换算、利润率、历史记录       |
| 拍照购       | ADB 控制 Android 设备，自动拍照搜索拼多多同款商品         |
| 报表导出      | 导出 Excel 商品比价报表                         |


---

## API 文档

启动后端后访问 Swagger 文档：[http://localhost:8000/docs](http://localhost:8000/docs)

---

## Docker 部署 (后端)

```bash
cd backend
docker build -t global-picker-api .
docker run -d -p 8000:8000 --env-file .env global-picker-api
```

