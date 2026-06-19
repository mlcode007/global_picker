-- 会员系统迁移脚本
-- 执行方式: mysql -h <host> -u <user> -p <db_name> < add_membership_system.sql

-- 1. User 表新增会员字段
ALTER TABLE users
  ADD COLUMN membership_tier ENUM('free', 'basic', 'pro') NOT NULL DEFAULT 'free' COMMENT '会员等级',
  ADD COLUMN membership_expires_at DATETIME DEFAULT NULL COMMENT '会员到期时间';

-- 2. PaymentOrder 表新增订单类型字段
ALTER TABLE payment_orders
  ADD COLUMN order_type ENUM('points', 'membership', 'cloud_phone') NOT NULL DEFAULT 'points' COMMENT '订单类型：积分充值/会员购买/云手机购买' AFTER payment_method;

-- 3. 新建云手机订阅表
CREATE TABLE IF NOT EXISTS cloud_phone_subscriptions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL COMMENT '用户ID',
  device_id INT DEFAULT NULL COMMENT '绑定的云手机设备ID，允许先购买后绑定',
  order_id INT DEFAULT NULL COMMENT '关联的支付订单ID',
  status ENUM('active', 'expired') NOT NULL DEFAULT 'active' COMMENT '订阅状态',
  started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '开始时间',
  expires_at DATETIME NOT NULL COMMENT '到期时间',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_user_id (user_id),
  INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='云手机订阅表';
