# 拼多多拍照购业务实现方案

> 文档日期：2026-03-17
>
> 适用前提：已有云手机、真机与本地测试机，设备均可通过 `ADB` 连接；目标是在现有 `Global Picker` 系统中接入“TikTok 商品图 -> 拼多多 App 拍照购 -> 返回候选同款 -> 人工确认/设主参照”的自动化流程。

---

## 一、目标定义

本方案的目标不是“直接调用拼多多官方图片搜索 API”，而是通过 **ADB 驱动拼多多 App 的拍照购能力**，完成以下闭环：

1. 从系统商品库中获取 TikTok 商品主图或辅图。
2. 将图片下发到 Android 设备。
3. 自动打开拼多多 App 并进入“拍照购 / 识图搜同款”入口。
4. 自动选择本地图片发起搜索。
5. 采集搜索结果页中的候选商品信息。
6. 回传后端，写入 `pdd_matches`，作为自动匹配结果。
7. 前端展示候选项，由人工确认、删除、设为主参照。

核心定位应当是：

- **自动推荐**，不是 100% 全自动决策。
- **设备自动化采集**，不是走官方开放平台。
- **结果回流业务系统**，不是单独做一套离线脚本。

---

## 二、整体架构

建议采用“业务系统 + 调度层 + 设备执行层 + 结果解析层”的四层结构。

```text
前端详情页
  -> 后端 API
  -> 任务队列
  -> ADB 调度器
  -> Android 设备执行器
  -> 拼多多 App 拍照购
  -> 结果采集/解析
  -> 回写 MySQL
  -> 前端展示与人工确认
```

### 1. 业务系统层

- 负责发起“自动拍照购”任务。
- 维护任务状态、超时、重试、结果入库。
- 与现有商品详情页、匹配列表、利润计算保持一致。

### 2. 调度层

- 管理设备池：云手机、真机、离线设备。
- 负责任务分配、设备加锁、超时回收。
- 控制同一设备同一时刻仅执行一个拍照购任务。

### 3. 设备执行层

- 使用 `ADB`、`uiautomator dump`、`input tap`、`input swipe`、`am start`、截图、OCR 等方式驱动拼多多 App。
- 执行“启动 -> 进入拍照购 -> 选图 -> 搜索 -> 等待结果 -> 采集页面”。

### 4. 结果解析层

- 从 XML UI 树、截图 OCR、剪贴板、跳转详情页等多个通道提取商品信息。
- 结构化出 `pdd_product_id`、标题、价格、店铺、销量、主图、链接、置信度。

---

## 三、推荐实现模式

从工程稳定性角度，建议优先采用以下模式。

### 模式 A：ADB + UIAutomator + OCR

这是最稳妥的首选方案。

- ADB 负责拉起 App、点击、滑动、文件下发。
- `uiautomator dump` 负责读取当前页面节点树。
- OCR 负责补足节点树拿不到的价格、销量、角标等视觉信息。

优点：

- 不依赖 App 内部接口逆向。
- 易于快速打通 PoC。
- 适合设备异构、版本变化情况下迭代。

缺点：

- 对页面结构变化较敏感。
- 结果提取准确率需要多轮打磨。

### 模式 B：ADB + 辅助服务 / 无障碍服务

适合后期提升稳定性。

- 在测试机安装自定义辅助服务 APK。
- 由辅助服务更可靠地读取节点、触发相册选择、上传图片、监听页面变化。

优点：

- 比纯 shell 点击更稳定。
- 可减少坐标点击依赖。

缺点：

- 需要维护 Android 端组件。
- 云手机环境可能存在权限差异。

### 模式 C：ADB + 抓包/逆向配合

可作为增强方案，但不建议作为第一阶段核心路径。

- 通过 ADB 驱动真实页面流程。
- 同时抓包分析搜索结果接口，若能确认稳定字段，则解析可更高效。

优点：

- 结果结构化更容易。
- 可降低 OCR 成本。

缺点：

- 维护成本高。
- App 升级后协议可能变化。

结论：

- **第一阶段**：模式 A。
- **第二阶段**：A + B 混合。
- **第三阶段**：若已掌握稳定接口，再局部接入模式 C 做解析增强。

---

## 四、业务流程设计

## 4.1 任务触发

触发方式建议有两种：

1. 商品详情页点击“自动拍照购”。
2. 批量任务：对待定商品批量发起自动匹配。

后端接口建议：

```http
POST /api/v1/pdd/photo-search/tasks
Content-Type: application/json

{
  "product_id": 123,
  "images": [
    "https://.../main.jpg",
    "https://.../detail-1.jpg"
  ],
  "max_candidates": 10
}
```

返回：

```json
{
  "task_id": "pdd_photo_20260317_xxx",
  "status": "queued"
}
```

## 4.2 后端准备图片

后端拿到任务后执行：

1. 下载 TikTok 商品主图到临时目录。
2. 做统一预处理：
   - 去白边
   - 缩放到合适尺寸
   - 保留原图与压缩图
3. 为设备准备固定落地图，如：
   - `/sdcard/DCIM/Camera/pdd_search_<task_id>.jpg`
   - `/sdcard/Pictures/pdd_search_<task_id>.jpg`

建议每个任务保留：

- 原图
- 压缩图
- 截图日志
- UI XML
- OCR 结果
- 结构化候选结果

## 4.3 调度设备

调度器从设备池挑选一个空闲设备：

- 设备在线
- 电量/云机状态正常
- 拼多多 App 已安装
- 未被其他任务占用

设备表建议维护：

| 字段 | 说明 |
|------|------|
| `device_id` | ADB serial |
| `device_type` | `cloud_phone` / `real_phone` |
| `status` | `idle` / `busy` / `offline` / `error` |
| `app_version` | 拼多多版本 |
| `last_heartbeat` | 最后心跳 |
| `current_task_id` | 当前任务 |
| `capabilities` | 是否支持 OCR、辅助服务、root 等 |

## 4.4 设备执行状态机

建议将拍照购流程做成显式状态机，便于重试和问题定位。

```text
INIT
-> PUSH_IMAGE
-> START_APP
-> ENTER_HOME
-> OPEN_CAMERA_SEARCH
-> OPEN_GALLERY
-> SELECT_IMAGE
-> SUBMIT_SEARCH
-> WAIT_RESULT
-> COLLECT_RESULT
-> PARSE_RESULT
-> SAVE_RESULT
-> FINISH
```

异常状态：

```text
APP_NOT_FOUND
NO_CAMERA_ENTRY
GALLERY_OPEN_FAILED
IMAGE_SELECT_FAILED
SEARCH_TIMEOUT
RESULT_PARSE_FAILED
DEVICE_DISCONNECTED
```

---

## 五、ADB 执行链路设计

以下是推荐的实际执行步骤。

## 5.1 设备预热

执行前先做设备标准化：

1. `adb -s <serial> shell wm size` 检查分辨率。
2. `adb -s <serial> shell settings put system screen_off_timeout 1800000`
3. 唤醒并解锁屏幕。
4. 回到桌面，清理前台弹窗。
5. 检查拼多多是否已登录到可用账号。

说明：

- 不建议每次 cold start 全量重启 App，可先 warm start。
- 连续失败达到阈值再清理 App 进程或切换设备。

## 5.2 下发图片

推荐两种方法：

### 方法 1：ADB push 到相册目录

```bash
adb -s <serial> push local.jpg /sdcard/DCIM/Camera/pdd_search_xxx.jpg
adb -s <serial> shell am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE -d file:///sdcard/DCIM/Camera/pdd_search_xxx.jpg
```

适合绝大多数场景。

### 方法 2：设备侧 HTTP 下载

如果设备与后端网络互通，也可让设备打开中转下载地址后保存。

适合大批量时减少本地 ADB 传输阻塞，但实现更复杂。

## 5.3 启动拼多多

推荐优先通过 `monkey` 或 `am start` 拉起：

```bash
adb -s <serial> shell monkey -p com.xunmeng.pinduoduo -c android.intent.category.LAUNCHER 1
```

启动后做两件事：

1. 等待首页稳定。
2. `uiautomator dump` 拉 UI 树，确认当前处于首页或可识别页面。

## 5.4 进入拍照购入口

入口识别建议按优先级执行：

1. 首页搜索框右侧相机图标。
2. 搜索页中的拍照/相册识图入口。
3. 通过首页搜索框先进入搜索页，再找相机入口。

入口定位策略：

- 优先用 XML 节点的 `text`、`content-desc`、`resource-id`。
- 找不到时，退化到模板图匹配或固定区域 OCR。
- 最后才使用分辨率映射坐标点击。

建议维护一个入口策略表：

| app_version | page_signature | action |
|-------------|----------------|--------|
| 版本 A | 首页搜索栏带相机 icon | 点击 icon |
| 版本 B | 首页无相机 icon | 先点搜索框，再点拍照购 |
| 版本 C | 弹窗遮挡 | 先关闭弹窗 |

## 5.5 打开相册并选择图片

典型流程：

1. 点击相机/识图入口。
2. 若弹出权限框，点击允许。
3. 切换到“相册/从相册选择”。
4. 选择最新下发的图片。

这里要特别处理：

- Android 权限授权弹窗
- 相册应用差异
- 云手机 ROM 定制相册
- 首次打开系统选择器时的“最近项目/图片/文件管理器”差异

建议做一个“选择器适配层”，对不同设备品牌/ROM 维护策略。

## 5.6 提交搜索并等待结果页

识别“结果已加载”的判断条件：

- 页面上出现商品卡片列表
- 出现价格文本，如 `¥`
- 出现“相似商品”“同款”“为你推荐”等关键词
- 页面截图中可见多个卡片区域

等待策略建议：

- 最长等待 15 秒
- 每 1 秒检查一次 UI 树或截图
- 超时则截图、导出 XML、记录错误码

---

## 六、结果采集设计

拍照购结果页通常很难一次性拿到完整字段，因此建议做“分层采集”。

## 6.1 第一层：列表页直接提取

目标字段：

- 标题
- 价格
- 销量
- 店铺名
- 缩略图

实现方式：

- 从 `uiautomator dump` 中读取节点文本
- 对截图进行 OCR，补足价格和销量
- 对卡片区域做版式切分，建立一条卡片一个对象

## 6.2 第二层：进入详情页补字段

对 Top N 候选做二次点击进入详情页，提取：

- `pdd_product_id`
- 商品详情页标题
- 更准确价格
- 店铺名
- 详情页主图

`pdd_product_id` 获取方式建议按优先级：

1. 详情页分享链接中的商品 ID
2. 页面 URL / schema 中的 goods_id
3. 页面文案或剪贴板数据中的商品 ID
4. 若拿不到，则保存为 null，仅保留标题和价格

说明：

- 列表页信息提取快，但字段不完整。
- 详情页补采更慢，因此只对前 3 到 5 个候选执行。

## 6.3 第三层：图片与文本联合打分

建议给每个候选计算一个 `match_confidence`：

- 图像相似度：TikTok 图与候选图做感知哈希或 CLIP 相似度
- 标题词相似度：分词后做 Jaccard / cosine
- 价格相近度：价格区间差异惩罚
- 品类一致性：是否同品类

示例：

```text
match_confidence =
  0.45 * image_similarity +
  0.30 * title_similarity +
  0.15 * price_similarity +
  0.10 * category_similarity
```

这样即使拍照购返回多个近似结果，也能在系统里自动排序。

---

## 七、结果回写业务系统

结果应回写到现有 `pdd_matches` 表。

建议映射关系如下：

| 业务字段 | 来源 |
|----------|------|
| `product_id` | 当前 TikTok 商品 |
| `pdd_product_id` | 详情页商品 ID |
| `pdd_title` | 结果页或详情页标题 |
| `pdd_price` | 结果页或详情页价格 |
| `pdd_sales_volume` | 结果页销量 |
| `pdd_shop_name` | 结果页或详情页店铺 |
| `pdd_image_url` | 候选商品图 |
| `pdd_product_url` | 分享链接或拼装链接 |
| `match_source` | 固定为 `image_search` |
| `match_confidence` | 综合打分 |
| `is_confirmed` | 初始为 `0` |
| `is_primary` | 初始为 `0` |

去重建议：

- 同一 `product_id + pdd_product_id` 只保留一条。
- 若无 `pdd_product_id`，则退化为 `product_id + 标题 + 价格` 近似去重。

---

## 八、数据库与任务表建议

除现有 `pdd_matches` 外，建议增加任务表与设备表。

## 8.1 拍照购任务表

建议表：`pdd_photo_search_tasks`

核心字段：

- `id`
- `product_id`
- `task_status`
- `device_id`
- `source_image_url`
- `local_image_path`
- `attempt_count`
- `error_code`
- `error_message`
- `started_at`
- `finished_at`
- `raw_result_json`
- `created_at`
- `updated_at`

## 8.2 设备池表

建议表：`device_pool`

核心字段：

- `device_id`
- `device_name`
- `platform`
- `status`
- `app_version`
- `android_version`
- `last_seen_at`
- `current_task_id`

## 8.3 执行日志表

建议表：`device_action_logs`

记录：

- 每一步动作
- 截图路径
- XML 路径
- OCR 路径
- 耗时
- 是否成功

这对于页面改版后的问题定位非常关键。

---

## 九、后端接口设计建议

## 9.1 创建任务

```http
POST /api/v1/pdd/photo-search/tasks
```

用途：

- 创建拍照购任务
- 返回 `task_id`

## 9.2 查询任务

```http
GET /api/v1/pdd/photo-search/tasks/{task_id}
```

返回：

- 当前状态
- 使用设备
- 错误信息
- 结果摘要

## 9.3 获取商品拍照购结果

```http
GET /api/v1/pdd/photo-search/products/{product_id}/matches
```

可直接复用现有 `pdd_matches` 查询接口，前端无需理解设备自动化细节。

## 9.4 重试任务

```http
POST /api/v1/pdd/photo-search/tasks/{task_id}/retry
```

用于：

- 手动重试
- 切换设备重试
- 使用第二张商品图重试

---

## 十、设备执行器模块拆分建议

建议把设备侧逻辑拆成以下模块，避免后期脚本堆成一团。

### 1. `device_manager`

负责：

- 枚举设备
- 心跳检测
- 锁设备
- 释放设备
- 设备异常下线

### 2. `adb_client`

负责：

- shell 执行
- push/pull
- 截图
- XML dump
- 点击、滑动、输入

### 3. `page_detector`

负责判断当前在哪一页：

- 桌面
- 拼多多首页
- 搜索页
- 相册选择页
- 结果页
- 商品详情页
- 弹窗页

### 4. `pdd_photo_flow`

负责完整状态机：

- 启动应用
- 进拍照购
- 选图
- 等结果
- 采结果

### 5. `result_parser`

负责：

- XML 解析
- OCR 解析
- 卡片切分
- 商品字段标准化
- 相似度评分

### 6. `artifact_manager`

负责保存：

- 截图
- XML
- OCR 文本
- 原始 JSON

---

## 十一、关键难点与应对

## 11.1 页面结构经常变化

应对：

- 页面识别不要只依赖坐标。
- 使用“多策略定位”：
  - XML 节点
  - 文字 OCR
  - 图标模板匹配
  - 坐标兜底

## 11.2 设备 ROM 差异导致相册选择器不同

应对：

- 为不同 ROM 建 selector profile。
- 将“选图”步骤独立成适配层，不要写死在主流程里。

## 11.3 列表页文字抽取不完整

应对：

- 列表页只做粗提取。
- Top N 进入详情页补齐字段。

## 11.4 图片搜出来是相似款，不一定是同款

应对：

- 系统侧必须保留人工确认。
- 增加 `match_confidence`。
- 利用标题、价格、图片三维打分做排序。

## 11.5 任务执行慢

应对：

- 单设备串行，多设备并行。
- 同一商品先取主图，失败后再取辅图。
- 列表页提取候选 10 个，但只深挖前 3 个。

---

## 十二、推荐开发顺序

建议按三阶段推进。

### 第一阶段：PoC 打通

目标：

- 单台设备
- 单张图片
- 能稳定完成：
  - push 图片
  - 打开拼多多
  - 进入拍照购
  - 选图
  - 到结果页
  - 采回前 5 条标题 + 价格

成功标准：

- 连续跑 30 次，成功率达到 70% 以上。

### 第二阶段：工程化

目标：

- 接入任务表
- 接入设备池
- 接入前端按钮和任务状态
- 增加截图、XML、OCR 日志
- 对 Top N 进入详情页补字段

成功标准：

- 支持多设备并发
- 支持失败重试
- 支持结果回写 `pdd_matches`

### 第三阶段：质量优化

目标：

- 引入相似度评分
- 多图重试
- 页面模板适配
- OCR 模型优化
- 设备稳定性监控

成功标准：

- 自动结果 Top 3 的人工可用率显著提高
- 平均任务时长控制在可接受范围内

---

## 十三、前端交互建议

商品详情页在“拼多多比价”卡片中新增：

- `自动拍照购`
- `查看任务状态`
- `重试`

前端展示建议：

- 自动结果标记为“自动”
- 展示 `match_confidence`
- 提供“设为主参照”
- 提供“已确认”
- 提供“删除”

交互原则：

- 自动结果默认只是候选，不直接影响利润计算。
- 只有“设为主参照”后才参与主计算逻辑。

---

## 十四、最小可落地版本

如果只追求尽快上线，建议先做最小版本：

1. 后端提供“创建拍照购任务”接口。
2. 单独启动一个 Python worker，负责 ADB 自动化。
3. 只支持一类设备和一个拼多多版本。
4. 只提取：
   - 标题
   - 价格
   - 图片
5. 结果直接写入 `pdd_matches`。
6. 前端只展示结果，不做复杂任务中心。

这样可以最快验证：

- 真实设备链路是否稳定
- 拍照购结果是否足够有业务价值
- 人工确认成本是否可接受

---

## 十五、结论

在你已有 **云手机 + 真机 + ADB** 条件下，最实际的方案不是去找不存在的官方“拼多多图片搜索 API”，而是：

1. 通过后端任务系统发起拍照购任务。
2. 由 ADB 驱动拼多多 App 真实执行“识图搜同款”流程。
3. 用 UIAutomator + OCR + 详情页补采提取候选商品。
4. 将候选结果写入现有 `pdd_matches` 表。
5. 在前端将自动结果作为“推荐候选”，交由人工确认与设主参照。

这是当前工程上最可控、最符合你现有资源条件的落地路径。

后续如果需要，可以继续补一版：

- Python 项目目录结构建议
- 任务表 SQL
- ADB 执行器伪代码
- 拼多多拍照购状态机代码框架
- 前后端接口定义文档

