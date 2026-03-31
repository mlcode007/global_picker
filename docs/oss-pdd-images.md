# 拼多多拍照购图片 → 阿里云 OSS

## 流程说明

1. Worker 从结果页截图裁剪商品主图，通过 `oss_service.upload_image_bytes` 上传到 Bucket（默认 `global-picker-pdd-image`）。
2. 返回的 **HTTPS 公网 URL** 写入 `pdd_matches.pdd_image_url`。
3. 前端商品详情页用 `<a-image :src="pdd_image_url" />` 直接展示。

## 环境变量（`backend/.env`）

| 变量 | 说明 |
|------|------|
| `OSS_ACCESS_KEY_ID` / `OSS_ACCESS_KEY_SECRET` | RAM 用户密钥，建议仅授予该 Bucket 的读写权限 |
| `OSS_BUCKET_NAME` | 如 `global-picker-pdd-image` |
| `OSS_ENDPOINT` | 地域 Endpoint，华北2北京：`https://oss-cn-beijing.aliyuncs.com` |
| `OSS_CDN_DOMAIN` | 可选，绑定 CDN/自定义域名时填完整域名（无尾斜杠） |

## 控制台必配

### 1. Bucket 读权限

前端 `<img>` 需要匿名可读，任选其一：

- **公共读**：Bucket → 权限管理 → 读写权限 → **公共读**（或按对象 ACL）
- 或保持私有，由后端生成**签名 URL**（当前代码未实现，需扩展）

### 2. 跨域 CORS（否则部分浏览器下可能异常）

Bucket → **数据安全** → **跨域设置** → 创建规则，示例：

- **来源**：`*` 或你的前端域名（如 `http://localhost:5173`）
- **方法**：`GET`, `HEAD`
- **允许 Headers**：`*`
- **暴露 Headers**：`ETag`（可选）

### 3. 内联预览（非强制下载）

上传时已设置 `Content-Disposition: inline`。若旧对象仍是下载行为，可在控制台对该对象 **设置元数据** 为 `Content-Disposition: inline`，或重新跑一次拍照购覆盖上传。

## 数据库同步

- 新任务：`save_candidates_to_matches` 会写入/更新 `pdd_image_url`（含覆盖旧的 `/artifacts` 本地路径）。
- **历史数据**：若 OSS 已有文件但库里无链接，可调用：

```http
POST /api/v1/pdd/photo-search/tasks/{task_id}/sync-images
```

任务需存在 `raw_result_json.candidates[].image_url`（与任务完成时保存的一致）。

商品详情页在拍照购成功条上提供 **「同步图片到列表」** 按钮，等价于上述接口。

## 拼多多商品链接（goods_id）

无障碍 XML **不含**商品 URL。开启 `PDD_EXTRACT_PRODUCT_LINKS=true`（默认）时，Worker 在结果页依次**点击**每个候选卡片，进入详情后从 `dumpsys activity activities` 中解析 `goods_id`，写入：

- `pdd_matches.pdd_product_id`
- `pdd_matches.pdd_product_url`（`https://mobile.yangkeduo.com/goods.html?goods_id=...`）

若解析失败（机型/P 版本差异），链接为空；可重试任务或稍后扩展 logcat 规则。

## 依赖

```bash
pip install -r backend/requirements.txt
# 含 Pillow、oss2
```
