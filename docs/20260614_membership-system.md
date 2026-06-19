# 会员系统设计

## 方案概览

| | 免费版 | 基础版 | 专业版 |
|---|---|---|---|
| **价格** | 0 | ¥99/月 | ¥129/月 |
| **每日采集** | 50次 | 500次 | 不限 |
| **拍照购** | ✅ 不限 | ✅ 不限 | ✅ 不限 |
| **1688比价** | ✅ | ✅ | ✅ |
| **云手机** | ❌ 需单独购买 ¥100/月/台 | ❌ 需单独购买 ¥100/月/台 | ❌ 需单独购买 ¥100/月/台 |
| **报表导出** | ✅ | ✅ | ✅ |
| **利润计算** | ✅ 基础+批量 | ✅ 基础+批量 | ✅ 基础+批量 |
| **数据看板** | ✅ | ✅ | ✅ |
| **积分充值** | ✅ 按量付费 | ✅ 按量付费 | ✅ 按量付费 |

### 核心差异

会员价值聚焦在**每日采集次数**：

- 免费版：50次/天，够体验核心流程
- 基础版：500次/天，覆盖中小卖家日常选品
- 专业版：不限，重度用户/团队

### 云手机计费

云手机与会员解耦，所有用户均需单独购买：

- 价格：¥100/月/台
- 每用户上限：5台

---

## 数据模型

### User 表新增字段

```python
membership_tier = Column(Enum("free", "basic", "pro"), nullable=False, default="free")
membership_expires_at = Column(DateTime, nullable=True)
```

### 新增 CloudPhoneSubscription 表

```python
class CloudPhoneSubscription(Base):
    __tablename__ = "cloud_phone_subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    device_id = Column(Integer, nullable=True, comment='绑定的云手机设备ID，允许先购买后绑定')
    order_id = Column(Integer, nullable=True, comment='关联的支付订单ID')
    status = Column(Enum("active", "expired"), nullable=False, default="active")
    started_at = Column(DateTime, server_default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=False, comment='到期时间')
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
```

> `device_id` 设为 nullable，支持用户先购买云手机额度，后续再绑定具体设备。

### PaymentOrder 表新增字段

```python
order_type = Column(
    Enum("points", "membership", "cloud_phone"),
    nullable=False,
    default="points",
    comment='订单类型：积分充值 / 会员购买 / 云手机购买'
)
```

> 复用现有 `PaymentOrder` 表，通过 `order_type` 区分三种订单类型，避免新建订单表。

---

## 配额常量

```python
TIER_LIMITS = {
    "free":  {"daily_collect": 50},
    "basic": {"daily_collect": 500},
    "pro":   {"daily_collect": 999999},
}

CLOUD_PHONE_PRICE = 100  # 元/月/台
CLOUD_PHONE_MAX = 5      # 每用户最多5台

# 每日配额按北京时间（UTC+8）0点重置
QUOTA_TIMEZONE = "Asia/Shanghai"
```

---

## 改动范围

### 后端

| 模块 | 改动内容 |
|---|---|
| **Model** | User 加 `membership_tier` + `membership_expires_at`；`PaymentOrder` 加 `order_type`；新增 `CloudPhoneSubscription` 表 |
| **QuotaManager** | `daily_limit` 从硬编码 10000 改为按 `membership_tier` 读取 `TIER_LIMITS`；配额重置时区改为北京时间 |
| **PointsManager** | `get_user_phone_limit` 改为按 `CloudPhoneSubscription` 活跃订阅数限制 |
| **Payment API** | 新增会员购买接口（购买/续费 basic/pro）；新增云手机购买接口 |
| **Membership API** | 新增查询当前会员状态、套餐信息接口 |
| **定时任务** | 会员到期自动降级为 free；云手机到期自动解绑 |

### 前端

| 页面 | 改动内容 |
|---|---|
| **会员页面** | 新增，展示三档套餐 + 云手机购买 |
| **个人中心** | 展示当前会员状态、到期时间 |
| **采集/拍照购** | 配额不足时引导升级会员 |

---

## 实施步骤

1. **User 表加字段 + 配额梯度** — 改动最小，立刻能区分用户
2. **会员购买支付接口** — 复用现有支付宝支付流程
3. **前端会员页面** — 套餐展示 + 购买
4. **云手机订阅表 + 购买接口** — 独立于会员
5. **到期降级定时任务** — 会员 + 云手机到期处理
