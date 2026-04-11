-- 云手机平台数据库迁移脚本
-- 生成日期：2026-04-10
-- 说明：为现有数据库添加云手机池和用户绑定表

USE `global_picker`;

-- ============================================================
-- 10. 云手机池表
--    管理所有云手机资源
-- ============================================================
CREATE TABLE IF NOT EXISTS `cloud_phone_pool` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `phone_id` VARCHAR(64) NOT NULL COMMENT '云手机ID（chinac返回的Id）',
  `phone_name` VARCHAR(128) DEFAULT NULL COMMENT '云手机名称',
  `status` ENUM('available', 'binding', 'bound', 'offline', 'maintenance') 
    NOT NULL DEFAULT 'available' COMMENT '状态: available-可用, binding-绑定中, bound-已绑定, offline-离线, maintenance-维护中',
  `created_by` INT UNSIGNED DEFAULT NULL COMMENT '创建用户ID',
  `region` VARCHAR(32) NOT NULL DEFAULT 'cn-jsha-cloudphone-3' COMMENT '地域',
  `instance_type` VARCHAR(64) DEFAULT NULL COMMENT '实例类型',
  `spec` JSON DEFAULT NULL COMMENT '规格信息（CPU、内存、存储等）',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `idx_phone_id` (`phone_id`),
  INDEX `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='云手机池';

-- ============================================================
-- 11. 用户云手机绑定表
--    记录用户与云手机的绑定关系
-- ============================================================
CREATE TABLE IF NOT EXISTS `user_cloud_phone` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `user_id` INT UNSIGNED NOT NULL COMMENT '用户ID',
  `phone_id` VARCHAR(64) NOT NULL COMMENT '云手机ID',
  `bind_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '绑定时间',
  `unbind_at` DATETIME DEFAULT NULL COMMENT '解绑时间（软删除）',
  `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否激活',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `idx_user_id` (`user_id`),
  UNIQUE INDEX `idx_phone_id` (`phone_id`),
  CONSTRAINT `fk_user_phone_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_user_phone_phone` FOREIGN KEY (`phone_id`) REFERENCES `cloud_phone_pool` (`phone_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户云手机绑定关系';

-- ============================================================
-- 初始化示例数据（可选）
-- ============================================================
-- 插入初始云手机资源（需要替换为实际的云手机ID）
-- INSERT INTO `cloud_phone_pool` (`phone_id`, `phone_name`, `status`, `instance_type`) VALUES
--   ('cp-bn15bs1p5aglj39w', '云手机-001', 'available', 'ci.g5.large'),
--   ('cp-bn15bs1p5aglj39x', '云手机-002', 'available', 'ci.g5.large'),
--   ('cp-bn15bs1p5aglj39y', '云手机-003', 'available', 'ci.g5.large');
