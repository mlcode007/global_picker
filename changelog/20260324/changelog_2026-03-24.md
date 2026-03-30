# 修改日报 — 2026-03-24

## 一、拍照购任务中断恢复机制

**问题**：服务重启后，正在执行的拍照购任务会卡在中间状态（dispatching/running/collecting 等），设备也被锁定为 busy，导致后续任务无法执行。

**改动文件**：
- `backend/app/main.py` — 新增 `_startup_recover()` 启动恢复函数，在 lifespan 中自动恢复中断任务并重新调度执行
- `backend/app/services/photo_search_service.py` — 新增 `recover_interrupted_tasks()` 方法，将所有中间状态任务重置为 queued，释放卡住的设备

## 二、设备离线自动恢复

**问题**：云手机设备偶尔断连后被标记为 offline/error，需要手动干预才能恢复，影响拍照购任务的自动执行。

**改动文件**：
- `backend/app/workers/pdd_photo/device_manager.py` — 重构 `acquire_device()` 逻辑：无空闲设备时自动尝试恢复 offline/error 设备（ADB 重连 + 重试）；心跳检测中发现设备恢复连接时自动置为 idle

## 三、拍照购结果图片裁剪与回传

**问题**：拍照购搜索结果只有文字信息（标题、价格），缺少商品主图，前端无法直观展示比价结果。

**改动文件**：
- `backend/app/workers/pdd_photo/result_parser.py` — 新增 `image_bounds` 字段和 `_assign_image_bounds()` 方法，从无障碍 XML 中收集大尺寸 ImageView 的坐标，匹配到对应候选商品
- `backend/app/workers/pdd_photo/worker.py` — 新增 `_crop_candidate_images()` 函数，从结果页截图中按 bounds 裁剪每个商品主图，保存为 artifact 并生成 HTTP 可访问路径
- `backend/app/main.py` — 挂载 `/artifacts` 静态文件服务，前端可直接访问截图
- `frontend/vite.config.js` — 开发代理新增 `/artifacts` 路径转发

## 四、PDD 比价记录图片补充

**问题**：已存在的 PDD 比价记录可能缺少商品图片，重新执行拍照购时应补充更新。

**改动文件**：
- `backend/app/services/photo_search_service.py` — `save_candidates_to_matches()` 中新增逻辑：已存在的匹配记录若缺少图片则补充更新
- `backend/app/services/pdd_service.py` — 比价记录排序改为按创建时间降序（替代 match_confidence）

## 五、清理历史诊断文档

**问题**：diagnosis 目录下的历史诊断文档已过时，占用仓库空间。

**改动文件**：
- `diagnosis/` — 删除 5 个历史诊断文档（changelog_crawl_pipeline、changelog_dashboard、changelog_playwright_upgrade、crawl_pipeline_diagnosis、tiktok_crawl_interaction_analysis）

## 六、新增 .gitignore

**问题**：项目缺少 .gitignore 文件，敏感文件和临时文件可能被误提交。

**改动文件**：
- `.gitignore` — 新增 41 行规则，覆盖 Python 缓存、Node 依赖、环境变量、IDE 配置、数据临时文件等

## 涉及文件汇总

| 文件 | 改动点 |
|------|--------|
| `backend/app/main.py` | 启动恢复 + 静态文件服务 |
| `backend/app/services/photo_search_service.py` | 任务恢复 + 图片补充更新 |
| `backend/app/services/pdd_service.py` | 比价排序调整 |
| `backend/app/workers/pdd_photo/device_manager.py` | 设备离线自动恢复 |
| `backend/app/workers/pdd_photo/result_parser.py` | 商品主图坐标提取 |
| `backend/app/workers/pdd_photo/worker.py` | 截图裁剪商品主图 |
| `frontend/vite.config.js` | 代理 /artifacts 路径 |
| `.gitignore` | 新增忽略规则 |
| `diagnosis/` | 删除 5 个过时文档 |

---

## 总结

本次改动重点解决了拍照购系统的稳定性和可用性问题。新增服务重启自动恢复机制，确保中断的任务和锁定的设备能自动恢复执行；实现设备离线自动重连，减少人工干预；完成拍照购结果商品主图的自动裁剪与回传，让前端能直观展示比价结果图片。同时清理了过时文档，新增了 .gitignore 保护敏感文件。
