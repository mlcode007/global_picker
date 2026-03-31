-- ============================================================
-- Global Picker 用户认证模块迁移脚本
-- 执行日期：2026-03-25
-- 功能：升级 users 表、新增 sms_verification 表、products 表加 user_id
-- ============================================================

USE `global_picker`;

-- ------------------------------------------------------------
-- 1. 升级 users 表：手机号注册 + 公司信息 + 业务属性
-- ------------------------------------------------------------
ALTER TABLE `users`
  ADD COLUMN `phone` VARCHAR(20) DEFAULT NULL COMMENT '手机号（登录凭证）' AFTER `username`,
  ADD COLUMN `company_name` VARCHAR(128) NOT NULL DEFAULT '' COMMENT '公司名称' AFTER `display_name`,
  ADD COLUMN `contact_name` VARCHAR(64) NOT NULL DEFAULT '' COMMENT '联系人姓名' AFTER `company_name`,
  ADD COLUMN `business_type` ENUM('cross_border','wholesale','retail','other') NOT NULL DEFAULT 'cross_border' COMMENT '业务类型' AFTER `contact_name`,
  ADD COLUMN `target_regions` JSON DEFAULT NULL COMMENT '目标市场地区（如 ["PH","MY","TH"]）' AFTER `business_type`,
  ADD COLUMN `avatar` VARCHAR(512) DEFAULT NULL COMMENT '头像URL' AFTER `target_regions`,
  ADD UNIQUE INDEX `idx_phone` (`phone`);

-- 将 username 改为可空（手机号为主登录方式）
ALTER TABLE `users` MODIFY COLUMN `username` VARCHAR(64) DEFAULT NULL;
ALTER TABLE `users` DROP INDEX `idx_username`;
ALTER TABLE `users` ADD UNIQUE INDEX `idx_username` (`username`);

-- 密码改为可空（支持纯短信登录）
ALTER TABLE `users` MODIFY COLUMN `password` VARCHAR(128) DEFAULT NULL;


-- ------------------------------------------------------------
-- 2. 短信验证码表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `sms_verification` (
  `id`         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT 'ID',
  `phone`      VARCHAR(20)     NOT NULL                COMMENT '手机号',
  `code`       VARCHAR(6)      NOT NULL                COMMENT '验证码',
  `purpose`    ENUM('register','login','reset_password') NOT NULL DEFAULT 'login' COMMENT '用途',
  `is_used`    TINYINT(1)      NOT NULL DEFAULT 0       COMMENT '是否已使用',
  `expired_at` DATETIME        NOT NULL                COMMENT '过期时间',
  `created_at` DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `idx_phone_purpose` (`phone`, `purpose`, `is_used`),
  INDEX `idx_expired_at` (`expired_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='短信验证码';


-- ------------------------------------------------------------
-- 3. products 表新增 user_id 字段（每个用户只能看到自己录入的商品）
-- ------------------------------------------------------------
ALTER TABLE `products`
  ADD COLUMN `user_id` INT UNSIGNED DEFAULT NULL COMMENT '所属用户ID' AFTER `id`,
  ADD INDEX `idx_user_id` (`user_id`);

-- 将 tiktok_url 的唯一索引改为 user_id + tiktok_url 联合唯一
ALTER TABLE `products` DROP INDEX `idx_tiktok_url`;
ALTER TABLE `products` ADD UNIQUE INDEX `idx_user_tiktok_url` (`user_id`, `tiktok_url`(255));
