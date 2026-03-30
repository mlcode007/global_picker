# 改动记录 — 2026-03-31

> **日期**：2026-03-31  
> **范围**：短信频率限制 Bug 修复 + 拍照购设备切换 + 系统架构文档 + 改进计划

---

## 一、短信频率限制时区 Bug 修复

**问题**：用户反馈"已经超过 60 秒了为啥还提示 60 秒"。

**根因**：`can_send_sms()` 使用 Python `datetime.now(timezone.utc)` 计算 60 秒窗口，但 MySQL `created_at` 字段使用 `DEFAULT CURRENT_TIMESTAMP`（服务器本地时区 UTC+8）。两个时钟差 8 小时，导致 `created_at >= cutoff` 的比较**永远为真**——Python UTC 时间比 MySQL 本地时间早 8 小时，任何记录都"看起来在 60 秒内"。

**修复**：将时间窗计算下沉到 MySQL 侧，使用 `NOW()` 和 `DATE_SUB()` 在同一时钟下比较。

**改动文件**：
- `backend/app/services/sms_service.py`

```diff
+ from sqlalchemy import func, literal_column

- cutoff = datetime.now(timezone.utc) - timedelta(seconds=settings.SMS_SEND_INTERVAL_SECONDS)
+ sec = int(settings.SMS_SEND_INTERVAL_SECONDS)
+ threshold = func.date_sub(func.now(), literal_column(f"INTERVAL {sec} SECOND"))
  recent = (
      db.query(SmsVerification)
      .filter(
          SmsVerification.phone == phone,
          SmsVerification.purpose == purpose,
-         SmsVerification.created_at >= cutoff,
+         SmsVerification.created_at >= threshold,
      )
      .first()
  )
```

---

## 二、拍照购设备切换：真机 → 阿里云手机

**背景**：拍照购 Worker 从本地真机调试切换到阿里云手机环境。

**改动文件**：
- `backend/app/workers/pdd_photo/worker.py` — 默认设备 serial 更新
- `db_photo_search.sql` — 初始化设备记录更新

### worker.py

```diff
- DEFAULT_DEVICE_SERIAL = "101.37.165.50:100"
+ DEFAULT_DEVICE_SERIAL = "120.55.50.221:10001"
```

### db_photo_search.sql

```diff
  INSERT INTO `device_pool` (`device_id`, `device_name`, `device_type`, `android_version`, `screen_width`, `screen_height`)
- VALUES ('MNYHYHBQOZDQS89H', 'Redmi 21091116AC', 'real_phone', '12', 1080, 2400)
- ON DUPLICATE KEY UPDATE `device_name` = VALUES(`device_name`);
+ VALUES ('120.55.50.221:10001', '阿里云手机', 'cloud_phone', '12', 720, 1280)
+ ON DUPLICATE KEY UPDATE `device_name` = VALUES(`device_name`), `device_type` = VALUES(`device_type`);
```

---

## 三、.gitignore 补充

新增 `.cursor/` 目录到忽略列表，避免 Cursor IDE 的项目配置文件被提交。

```diff
+ .cursor/
```

---

## 四、系统架构文档生成（docs 目录）

为项目汇报生成了三套 drawio 架构图及导出 PNG：

| 文件 | 说明 |
|------|------|
| `docs/01-system-architecture.drawio(.png)` | 系统整体架构图：前端、后端 API、Worker 层、数据库、外部服务 |
| `docs/02-tech-stack.drawio(.png)` | 技术栈全景图：各层使用的框架、库、中间件 |
| `docs/03-business-flow.drawio(.png)` | 业务流程图：商品采集 → 比价 → 利润计算 → 导出的完整数据流 |
| `docs/architecture.drawio` | 初版综合架构图（后拆分为上述三个独立文件） |

---

## 五、系统改进计划

基于全量代码审查，生成了 `docs/improvement-plan.md`，包含 23 项改进建议：

| 优先级 | 数量 | 典型问题 |
|--------|------|----------|
| P0（安全） | 4 项 | IDOR 越权、采集配置越权、SECRET_KEY 默认值、敏感文件 |
| P1（可靠/性能） | 6 项 | 任务恢复不完整、无自动重试、N+1 查询、Redis 闲置 |
| P2（工程化） | 13 项 | 无 Alembic、无测试、无 CI/CD、前端代码规范 |

含 6 周实施路线图和状态跟踪表。

---

## 涉及文件汇总

| 文件 | 改动点 |
|------|--------|
| `backend/app/services/sms_service.py` | 修复短信频率限制时区 Bug，改用 MySQL `NOW()` |
| `backend/app/workers/pdd_photo/worker.py` | 默认设备 serial 切换为阿里云手机 |
| `db_photo_search.sql` | 初始化设备改为阿里云手机 |
| `.gitignore` | 新增 `.cursor/` 忽略 |
| `docs/01-system-architecture.drawio(.png)` | 新增：系统架构图 |
| `docs/02-tech-stack.drawio(.png)` | 新增：技术栈全景图 |
| `docs/03-business-flow.drawio(.png)` | 新增：业务流程图 |
| `docs/architecture.drawio` | 新增：初版综合架构图 |
| `docs/improvement-plan.md` | 新增：23 项系统改进计划 |

---

## 总结

修复了短信验证码频率限制因 Python UTC 与 MySQL 本地时区不一致导致的"永远提示 60 秒"Bug；拍照购设备从本地真机切换到阿里云手机，为远程部署做准备；生成了三套系统架构图和一份 23 项改进计划，为项目汇报和后续迭代提供依据。
