# 云手机平台设计方案

> 生成日期：2026-04-10  
> 作者：AI Assistant

---

## 一、设计目标

### 核心需求
1. **每个用户独立分配一台云手机** - 用户独享资源，互不干扰
2. **云手机资源不足时的应对策略** - 弹性扩容 + 等待队列

### 设计原则
- **资源池化**：统一管理所有云手机资源
- **动态分配**：根据用户需求动态分配和回收
- **自动扩容**：资源不足时自动创建新云手机
- **状态管理**：完整的生命周期管理

---

## 二、数据库设计

### 1. 云手机池表 (`cloud_phone_pool`)

```sql
CREATE TABLE IF NOT EXISTS `cloud_phone_pool` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `phone_id` VARCHAR(64) NOT NULL UNIQUE COMMENT '云手机ID',
  `phone_name` VARCHAR(128) DEFAULT NULL COMMENT '云手机名称',
  `status` ENUM('available', 'binding', 'bound', 'offline', 'maintenance') 
    NOT NULL DEFAULT 'available',
  `region` VARCHAR(32) NOT NULL DEFAULT 'cn-jsha-cloudphone-3',
  `instance_type` VARCHAR(64) DEFAULT NULL COMMENT '实例类型',
  `spec` JSON DEFAULT NULL COMMENT '规格信息（CPU、内存、存储）',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `idx_phone_id` (`phone_id`),
  INDEX `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='云手机池';
```

### 2. 用户云手机绑定表 (`user_cloud_phone`)

```sql
CREATE TABLE IF NOT EXISTS `user_cloud_phone` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` INT UNSIGNED NOT NULL,
  `phone_id` VARCHAR(64) NOT NULL,
  `bind_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `unbind_at` DATETIME DEFAULT NULL COMMENT '解绑时间（软删除）',
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `idx_user_id` (`user_id`),
  UNIQUE INDEX `idx_phone_id` (`phone_id`),
  CONSTRAINT `fk_user_phone_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_user_phone_phone` FOREIGN KEY (`phone_id`) REFERENCES `cloud_phone_pool` (`phone_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户云手机绑定关系';
```

---

## 三、核心功能模块

### 1. 云手机池管理

**功能：**
- ✅ 添加云手机到资源池
- ✅ 从资源池移除云手机
- ✅ 更新云手机状态
- ✅ 查询资源池统计信息

**状态流转：**
```
available → binding → bound → offline/available
                          ↓
                      maintenance
```

### 2. 用户绑定管理

**功能：**
- ✅ 为用户分配云手机
- ✅ 解绑用户的云手机
- ✅ 查询用户的云手机
- ✅ 查询云手机的使用用户

**绑定策略：**
- 一个用户只能绑定一台云手机
- 支持软删除（保留历史记录）
- 支持强制解绑

### 3. 资源分配策略

**核心方法：** `acquire_phone_for_user(user_id)`

**分配流程：**
1. 检查用户是否已有云手机（优先复用）
2. 从资源池获取空闲云手机
3. 如果资源池为空，触发自动扩容
4. 如果扩容失败，返回资源紧张提示

**伪代码：**
```python
def acquire_phone_for_user(user_id):
    # 1. 检查用户是否已有云手机
    existing = get_user_phone(user_id)
    if existing and is_available(existing.phone_id):
        return bind_to_user(user_id, existing.phone_id)
    
    # 2. 从资源池分配
    phone = try_acquire_from_pool()
    if phone:
        return bind_to_user(user_id, phone.phone_id)
    
    # 3. 自动扩容
    if should_auto_scale():
        new_phones = auto_scale()
        if new_phones:
            return bind_to_user(user_id, new_phones[0].phone_id)
    
    # 4. 资源不足
    return None
```

### 4. 自动扩容机制

**触发条件：**
```python
# 阈值配置
MIN_AVAILABLE_POOL = 3          # 最小可用池数量
AUTO_SCALE_THRESHOLD = 0.3      # 自动扩容触发阈值（30%）
MAX_AUTO_SCALE = 10             # 最大自动扩容数量
```

**扩容逻辑：**
```python
def _should_auto_scale(self) -> bool:
    total = get_total_phones()
    available = get_available_count()
    available_rate = available / total
    return available_rate < AUTO_SCALE_THRESHOLD or total == 0

def _auto_scale(self, count=1):
    for i in range(count):
        response = create_cloud_phone(instance_type="ci.g5.large")
        add_to_pool(response['Id'])
```

---

## 四、云手机不够的解决方案

### 方案一：资源池 + 动态扩容（已实现）

**优点：**
- ✅ 自动化程度高
- ✅ 用户体验好
- ✅ 资源利用率高

**缺点：**
- ❌ 需要云手机服务商支持快速创建
- ❌ 可能产生额外成本

**适用场景：**
- 云手机服务商支持快速创建（5分钟内）
- 预算充足
- 用户量波动较大

---

### 方案二：等待队列 + 优先级

**适用场景：**
- 云手机创建速度慢（>10分钟）
- 预算有限
- 用户可以接受等待

**实现思路：**
```python
class CloudPhoneQueue:
    def __init__(self):
        self.waiting_users = []  # 等待队列
        self.user_priority = {}  # 用户优先级
    
    def request_phone(self, user_id):
        phone = get_available_phone()
        if phone:
            return bind_to_user(user_id, phone)
        
        # 加入等待队列
        self.waiting_users.append(user_id)
        notify_user(user_id, "云手机资源紧张，您在队列中第{}位".format(
            len(self.waiting_users)
        ))
        return None
    
    def on_phone_release(self, phone_id):
        # 云手机释放时，分配给等待队列的第一个用户
        if self.waiting_users:
            user_id = self.waiting_users.pop(0)
            bind_to_user(user_id, phone_id)
            notify_user(user_id, "云手机已就绪")
```

**优先级策略：**
```python
USER_PRIORITY = {
    'premium': 1,   # 高级用户 - 优先分配
    'standard': 2,  # 普通用户
    'free': 3       # 免费用户 - 最后分配
}
```

---

### 方案三：用户优先级 + 资源抢占

**适用场景：**
- 付费用户需要 guaranteed 资源
- 免费用户可以接受等待

**实现思路：**
```python
def acquire_phone_with_priority(user_id):
    user_level = get_user_level(user_id)
    
    # 1. 优先分配给高级用户
    if user_level == 'premium':
        # 跳过等待，直接创建新云手机
        phone = create_and_bind(user_id)
        return phone
    
    # 2. 普通用户和免费用户排队
    return wait_in_queue(user_id)
```

---

### 方案四：混合模式（推荐）

**策略：**
1. 保持 3-5 台云手机在资源池中（available 状态）
2. 用户请求时，优先从池中分配
3. 池中不足时，自动扩容 + 加入等待队列
4. 高级用户可以抢占普通用户的云手机（通知普通用户等待）

**优点：**
- ✅ 普通用户快速响应
- ✅ 高级用户 guaranteed 资源
- ✅ 资源利用率最大化

---

## 五、API 设计

### 1. 获取云手机池统计

```http
GET /api/v1/cloud-phone/pool/stats
```

**响应：**
```json
{
  "code": 0,
  "data": {
    "total": 10,
    "available": 3,
    "bound": 5,
    "offline": 2,
    "available_rate": 0.3
  }
}
```

### 2. 为用户分配云手机

```http
POST /api/v1/cloud-phone/acquire
```

**响应：**
```json
{
  "code": 0,
  "msg": "云手机分配成功",
  "data": {
    "phone_id": "cp-bn15bs1p5aglj39w",
    "bind_at": "2026-04-10T10:00:00"
  }
}
```

### 3. 获取用户的云手机

```http
GET /api/v1/cloud-phone/my-phone
```

**响应：**
```json
{
  "code": 0,
  "data": {
    "phone_id": "cp-bn15bs1p5aglj39w",
    "bind_at": "2026-04-10T10:00:00",
    "is_active": true
  }
}
```

### 4. 手动扩容

```http
POST /api/v1/cloud-phone/pool/scale?count=3
```

**响应：**
```json
{
  "code": 0,
  "msg": "成功扩容 3 台云手机",
  "data": ["cp-xxx1", "cp-xxx2", "cp-xxx3"]
}
```

---

## 六、实施路线图

### 第一阶段：基础功能（1-2天）
- [ ] 创建数据库表
- [ ] 实现云手机池管理
- [ ] 实现用户绑定管理
- [ ] 实现基本的分配和回收

### 第二阶段：自动扩容（1天）
- [ ] 集成 chinac API 创建云手机
- [ ] 实现自动扩容逻辑
- [ ] 配置阈值和策略

### 第三阶段：等待队列（可选，1天）
- [ ] 实现等待队列
- [ ] 实现优先级策略
- [ ] 实现通知机制

### 第四阶段：监控和运维（1天）
- [ ] 健康检查
- [ ] 离线恢复
- [ ] 统计和告警

---

## 七、关键配置

### 环境变量
```env
# 云手机配置
CLOUD_PHONE_MIN_POOL=3
CLOUD_PHONE_MAX_SCALE=10
CLOUD_PHONE_SCALE_THRESHOLD=0.3

# Chinac API（已有）
CHINAC_ACCESS_KEY_ID=your_access_key
CHINAC_ACCESS_KEY_SECRET=your_access_secret
```

### 阈值配置（代码中）
```python
class CloudPhoneManager:
    MIN_AVAILABLE_POOL = 3
    MAX_AUTO_SCALE = 10
    AUTO_SCALE_THRESHOLD = 0.3
```

---

## 八、优势分析

### 1. 用户隔离
- 每个用户独享云手机，互不干扰
- 避免资源竞争和冲突

### 2. 弹性伸缩
- 资源不足时自动扩容
- 支持手动扩容

### 3. 状态管理
- 完整的生命周期管理
- 支持离线恢复

### 4. 扩展性强
- 支持多种分配策略
- 支持优先级和排队

---

## 九、后续优化方向

### 1. 智能调度
- 根据用户使用习惯预分配
- 识别低峰期批量释放资源

### 2. 成本优化
- 不同规格的云手机池
- 按需分配不同规格

### 3. 多地域支持
- 跨地域资源池
- 就近分配

### 4. 监控告警
- 资源使用率告警
- 离线告警

---

## 十、总结

**推荐方案：** 混合模式（资源池 + 自动扩容 + 等待队列）

**核心优势：**
1. ✅ 每个用户独立云手机
2. ✅ 资源不足时自动扩容
3. ✅ 支持等待队列和优先级
4. ✅ 完整的状态管理和监控

**下一步：**
1. 创建数据库表
2. 实现基础功能
3. 集成 chinac API
4. 测试和优化
