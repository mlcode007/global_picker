# 修改日报 — 2026-03-30

## 一、用户认证体系升级（短信验证码登录 + 注册）

**问题**：原有认证仅支持用户名密码登录，无法满足手机号注册、短信验证码登录的需求，也缺少用户资料管理功能。

**改动文件**：
- `backend/app/api/v1/auth.py` — 重构认证 API：新增短信发送、短信登录、手机号注册、获取/更新用户资料等接口
- `backend/app/core/security.py` — 密码加密从 passlib 迁移到 bcrypt 直接调用；新增 `get_current_user()`（强制鉴权）和 `get_optional_user()`（可选鉴权）
- `backend/app/models/user.py` — User 模型扩展：新增 phone、company_name、contact_name、business_type、target_regions、avatar 字段
- `backend/app/models/sms_verification.py` — 新增短信验证码模型（SmsVerification）
- `backend/app/schemas/user.py` — 新增 SmsSendRequest、SmsLoginRequest、UserRegisterRequest、UserProfileUpdate、LoginResponse 等 Schema
- `backend/app/services/sms_service.py` — 新增阿里云短信服务：验证码生成、发送、频率限制、校验
- `backend/app/config.py` — 新增阿里云 OSS、短信服务、拍照购链接提取等配置项
- `backend/requirements.txt` — 新增 bcrypt、oss2、httpx 等依赖
- `db_migration_auth.sql` — 认证相关数据库迁移脚本
- `frontend/src/views/Login.vue` — 新增登录页面（支持密码/短信两种方式）
- `frontend/src/views/Register.vue` — 新增注册页面
- `frontend/src/api/auth.js` — 新增认证 API 封装
- `frontend/src/stores/auth.js` — 新增 Pinia 认证状态管理
- `frontend/src/router/index.js` — 路由守卫：未登录跳转登录页
- `frontend/src/components/AppLayout.vue` — 顶部导航新增用户信息与退出登录

## 二、全接口鉴权 + 数据用户隔离

**问题**：所有 API 接口无鉴权保护，不同用户的商品数据混在一起，无法实现多用户独立使用。

**改动文件**：
- `backend/app/api/v1/products.py` — 商品 CRUD 接口全部加入 `get_current_user` 鉴权，按 user_id 隔离数据
- `backend/app/api/v1/dashboard.py` — 看板统计按当前用户过滤
- `backend/app/api/v1/photo_search.py` — 拍照购接口加入鉴权
- `backend/app/api/v1/profit.py` — 利润计算接口加入鉴权
- `backend/app/api/v1/export.py` — 导出接口加入鉴权，按用户过滤
- `backend/app/api/v1/tasks.py` — 任务查询接口加入鉴权
- `backend/app/api/v1/settings.py` — 设置接口加入鉴权
- `backend/app/api/v1/pdd.py` — PDD 比价接口加入鉴权
- `backend/app/services/product_service.py` — 商品服务全面支持 user_id 参数：创建、查询、更新、删除均按用户隔离
- `backend/app/services/export_service.py` — 导出服务支持 user_id 过滤
- `backend/app/models/product.py` — Product 模型新增 user_id 字段

## 三、商品采集数据跨用户共享

**问题**：不同用户导入相同 TikTok 商品链接时，需要重复采集，浪费采集资源。

**改动文件**：
- `backend/app/services/product_service.py` — 新增 `_find_shared_product()` 和 `_copy_crawl_data()`：当其他用户已成功采集同一商品时，直接复制采集数据，跳过重复抓取

## 四、TikTok 采集字段解析优化

**问题**：Playwright 采集的价格字段解析错误，从页面元素抽取不够准确。

**改动文件**：
- `backend/app/workers/tiktok_crawler.py` — 优化商品数据解析逻辑，改为从页面源码中的 JSON 数据格式抽取，提升价格等字段的解析准确性；支持多张商品图片采集与存储

## 五、拍照购结果增强（OSS 图片 + 商品链接提取）

**问题**：拍照购结果的商品图片存储在本地服务器，无法在外网访问；且缺少拼多多商品链接和 goods_id。

**改动文件**：
- `backend/app/services/oss_service.py` — 新增阿里云 OSS 上传服务（支持字节流和文件上传）
- `backend/app/workers/pdd_photo/link_extractor.py` — 新增商品链接提取器：在搜索结果页依次点击进入详情，通过 dumpsys 解析 goods_id，生成 H5 商品链接
- `backend/app/workers/pdd_photo/result_parser.py` — 结果解析增强
- `backend/app/workers/pdd_photo/worker.py` — 集成 OSS 上传和链接提取流程
- `backend/app/services/photo_search_service.py` — `save_candidates_to_matches()` 增强：同步 OSS 图片 URL、商品链接、goods_id 到比价记录；新增 `sync_match_images_from_task_result()` 回填方法
- `docs/oss-pdd-images.md` — OSS 图片上传方案文档

## 六、Git 敏感信息清理

**问题**：数据库密码文件（db_info.txt）和环境变量文件（.env）被误提交到 Git 仓库，存在安全风险。

**改动文件**：
- `.gitignore` — 新增 18 行规则，覆盖 db_info.txt、.env、data_temp/ 等敏感文件
- `scripts/restart-dev.sh` — 新增开发环境重启脚本

## 涉及文件汇总

| 文件 | 改动点 |
|------|--------|
| `backend/app/api/v1/auth.py` | 短信登录/注册/用户资料 API |
| `backend/app/core/security.py` | bcrypt 迁移 + 强制/可选鉴权 |
| `backend/app/models/user.py` | 用户模型扩展（手机号、公司信息等） |
| `backend/app/models/sms_verification.py` | 新增短信验证码模型 |
| `backend/app/models/product.py` | 新增 user_id 字段 |
| `backend/app/schemas/user.py` | 新增多个认证/用户 Schema |
| `backend/app/services/sms_service.py` | 阿里云短信服务 |
| `backend/app/services/oss_service.py` | 阿里云 OSS 上传服务 |
| `backend/app/services/product_service.py` | 用户隔离 + 跨用户数据共享 |
| `backend/app/services/photo_search_service.py` | OSS 图片/链接同步 |
| `backend/app/services/export_service.py` | 导出按用户过滤 |
| `backend/app/config.py` | OSS/短信/拍照购配置 |
| `backend/app/workers/tiktok_crawler.py` | 采集字段解析优化 |
| `backend/app/workers/pdd_photo/link_extractor.py` | 商品链接提取 |
| `backend/app/workers/pdd_photo/worker.py` | 集成 OSS + 链接提取 |
| `backend/app/api/v1/*.py` (8个文件) | 全接口加入鉴权 |
| `frontend/src/views/Login.vue` | 登录页面 |
| `frontend/src/views/Register.vue` | 注册页面 |
| `frontend/src/stores/auth.js` | 认证状态管理 |
| `frontend/src/router/index.js` | 路由守卫 |
| `frontend/src/components/AppLayout.vue` | 用户信息展示 |
| `.gitignore` | 敏感文件过滤规则 |
| `db_migration_auth.sql` | 认证数据库迁移 |
| `scripts/restart-dev.sh` | 开发环境重启脚本 |

---

## 总结

本次改动完成了三大核心升级：（1）用户认证体系从简单密码登录升级为手机号短信验证码登录+注册，接入阿里云短信服务；（2）全部 API 接口加入鉴权保护，商品数据实现用户级隔离，支持多用户独立使用，同时通过跨用户数据共享机制减少重复采集成本；（3）拍照购结果增强，商品图片上传至阿里云 OSS 实现外网可访问，新增商品链接提取能力。此外优化了 TikTok 采集的字段解析准确性，清理了 Git 仓库中的敏感信息。
