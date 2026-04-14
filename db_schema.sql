-- ============================================================
-- Global Picker 数据库表结构
-- 数据库：global_picker（阿里云 RDS MySQL）
-- 创建日期：2026-03-16
-- ============================================================

CREATE DATABASE IF NOT EXISTS `global_picker`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `global_picker`;

-- ------------------------------------------------------------
-- 1. 抓取任务表
--    记录所有提交的 TikTok 商品链接抓取任务，供 Celery Worker 消费
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `crawl_tasks` (
  `id`           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '任务ID',
  `url`          VARCHAR(1024)   NOT NULL                COMMENT 'TikTok 商品原始链接',
  `status`       ENUM('pending','running','done','failed') NOT NULL DEFAULT 'pending' COMMENT '任务状态',
  `retry_count`  TINYINT UNSIGNED NOT NULL DEFAULT 0     COMMENT '已重试次数',
  `error_msg`    TEXT                                    COMMENT '失败时的错误信息',
  `status_detail` VARCHAR(512)                          NULL COMMENT 'running 时进度提示（如验证码）',
  `created_at`   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `idx_status` (`status`),
  INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='抓取任务队列';


-- ------------------------------------------------------------
-- 2. TikTok 商品主表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `products` (
  `id`              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '商品ID',
  `crawl_task_id`   BIGINT UNSIGNED                         COMMENT '关联抓取任务',
  `tiktok_url`      VARCHAR(1024)   NOT NULL                COMMENT 'TikTok 商品链接',
  `tiktok_product_id` VARCHAR(64)                           COMMENT 'TikTok 商品ID（从链接解析）',
  `title`           VARCHAR(512)    NOT NULL DEFAULT ''     COMMENT '商品标题',
  `description`     TEXT                                    COMMENT '商品描述',
  `price`           DECIMAL(12, 2)  NOT NULL DEFAULT 0.00   COMMENT 'TikTok 售价（原始货币）',
  `currency`        VARCHAR(8)      NOT NULL DEFAULT 'PHP'  COMMENT '价格货币单位',
  `price_cny`       DECIMAL(12, 2)           DEFAULT NULL   COMMENT '折算人民币售价',
  `sales_volume`    INT UNSIGNED    NOT NULL DEFAULT 0      COMMENT '销量',
  `rating`          DECIMAL(3, 2)            DEFAULT NULL   COMMENT '商品评分（0.00~5.00）',
  `review_count`    INT UNSIGNED    NOT NULL DEFAULT 0      COMMENT '评价数量',
  `stock_status`    TINYINT(1)      NOT NULL DEFAULT 1      COMMENT '库存状态：1在售 0下架',
  `region`          VARCHAR(16)     NOT NULL DEFAULT 'PH'   COMMENT '销售区域（PH/MY/TH等）',
  `shop_name`       VARCHAR(256)             DEFAULT NULL   COMMENT 'TikTok 店铺名',
  `shop_id`         VARCHAR(64)              DEFAULT NULL   COMMENT 'TikTok 店铺ID',
  `main_image_url`  VARCHAR(1024)            DEFAULT NULL   COMMENT '主图链接',
  `image_urls`      JSON                                    COMMENT '所有图片链接（JSON数组）',
  `category`        VARCHAR(128)             DEFAULT NULL   COMMENT '商品类目',
  `status`          ENUM('pending','selected','abandoned') NOT NULL DEFAULT 'pending' COMMENT '选品状态：待定/已选/放弃',
  `remark`          VARCHAR(512)             DEFAULT NULL   COMMENT '人工备注',
  `is_deleted`      TINYINT(1)      NOT NULL DEFAULT 0      COMMENT '软删除标志',
  `created_at`      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `idx_tiktok_url` (`tiktok_url`(255)),
  INDEX `idx_status` (`status`),
  INDEX `idx_region` (`region`),
  INDEX `idx_sales_volume` (`sales_volume`),
  INDEX `idx_price_cny` (`price_cny`),
  INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='TikTok 商品主表';


-- ------------------------------------------------------------
-- 3. 拼多多匹配结果表
--    一条 TikTok 商品可对应多条拼多多匹配结果（候选列表）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `pdd_matches` (
  `id`                BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '匹配记录ID',
  `product_id`        BIGINT UNSIGNED NOT NULL                COMMENT '关联 products.id',
  `pdd_product_id`    VARCHAR(64)              DEFAULT NULL   COMMENT '拼多多商品ID',
  `pdd_title`         VARCHAR(512)    NOT NULL DEFAULT ''     COMMENT '拼多多商品标题',
  `pdd_price`         DECIMAL(12, 2)  NOT NULL DEFAULT 0.00   COMMENT '拼多多售价（人民币）',
  `pdd_original_price` DECIMAL(12, 2)          DEFAULT NULL   COMMENT '拼多多划线价',
  `pdd_sales_volume`  INT UNSIGNED             DEFAULT NULL   COMMENT '拼多多销量',
  `pdd_shop_name`     VARCHAR(256)             DEFAULT NULL   COMMENT '拼多多店铺名',
  `pdd_shop_id`       VARCHAR(64)              DEFAULT NULL   COMMENT '拼多多店铺ID',
  `pdd_image_url`     VARCHAR(1024)            DEFAULT NULL   COMMENT '拼多多商品主图',
  `pdd_product_url`   VARCHAR(1024)            DEFAULT NULL   COMMENT '拼多多商品链接',
  `match_source`      ENUM('image_search','keyword_search','manual') NOT NULL DEFAULT 'image_search' COMMENT '匹配来源',
  `match_confidence`  DECIMAL(5, 4)            DEFAULT NULL   COMMENT '匹配置信度 0~1',
  `is_confirmed`      TINYINT(1)      NOT NULL DEFAULT 0      COMMENT '是否已人工确认',
  `is_primary`        TINYINT(1)      NOT NULL DEFAULT 0      COMMENT '是否为主参照商品（用于利润计算）',
  `created_at`        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `idx_product_id` (`product_id`),
  INDEX `idx_is_confirmed` (`is_confirmed`),
  INDEX `idx_is_primary` (`product_id`, `is_primary`),
  CONSTRAINT `fk_pdd_product` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='拼多多商品匹配结果';


-- ------------------------------------------------------------
-- 4. 利润计算记录表
--    每次重新计算都插入新记录，保留历史
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `profit_records` (
  `id`                BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '记录ID',
  `product_id`        BIGINT UNSIGNED NOT NULL                COMMENT '关联 products.id',
  `pdd_match_id`      BIGINT UNSIGNED          DEFAULT NULL   COMMENT '关联 pdd_matches.id',
  `tiktok_price_cny`  DECIMAL(12, 2)  NOT NULL               COMMENT 'TikTok 折算人民币售价',
  `pdd_price_cny`     DECIMAL(12, 2)  NOT NULL               COMMENT '拼多多采购价（人民币）',
  `logistics_cost`    DECIMAL(12, 2)  NOT NULL DEFAULT 0.00   COMMENT '物流成本（人民币）',
  `platform_fee_rate` DECIMAL(5, 4)   NOT NULL DEFAULT 0.0000 COMMENT 'TikTok 平台佣金率',
  `platform_fee`      DECIMAL(12, 2)  NOT NULL DEFAULT 0.00   COMMENT '平台佣金金额',
  `other_cost`        DECIMAL(12, 2)  NOT NULL DEFAULT 0.00   COMMENT '其他杂费',
  `profit`            DECIMAL(12, 2)  NOT NULL               COMMENT '利润 = 售价 - 采购 - 物流 - 佣金 - 其他',
  `profit_rate`       DECIMAL(7, 4)   NOT NULL               COMMENT '利润率 = 利润 / 售价',
  `exchange_rate`     DECIMAL(10, 4)            DEFAULT NULL  COMMENT '汇率（如 PHP→CNY）',
  `note`              VARCHAR(512)             DEFAULT NULL   COMMENT '计算备注',
  `created_at`        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `idx_product_id` (`product_id`),
  INDEX `idx_profit_rate` (`profit_rate`),
  CONSTRAINT `fk_profit_product` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='利润计算历史记录';


-- ------------------------------------------------------------
-- 5. 用户表
--    支持多人协作使用系统
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `users` (
  `id`          INT UNSIGNED  NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `username`    VARCHAR(64)   NOT NULL                COMMENT '登录用户名',
  `password`    VARCHAR(128)  NOT NULL                COMMENT '密码（bcrypt）',
  `display_name` VARCHAR(64)  NOT NULL DEFAULT ''     COMMENT '显示名称',
  `role`        ENUM('admin','editor','viewer') NOT NULL DEFAULT 'editor' COMMENT '角色权限',
  `is_active`   TINYINT(1)   NOT NULL DEFAULT 1       COMMENT '是否启用',
  `last_login`  DATETIME              DEFAULT NULL     COMMENT '最后登录时间',
  `created_at`  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `idx_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='系统用户';


-- ------------------------------------------------------------
-- 6. 操作日志表
--    记录关键操作，用于审计与问题追踪
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `operation_logs` (
  `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '日志ID',
  `user_id`     INT UNSIGNED             DEFAULT NULL   COMMENT '操作用户ID',
  `action`      VARCHAR(64)     NOT NULL               COMMENT '操作类型（如 add_product, update_status, export）',
  `target_type` VARCHAR(64)              DEFAULT NULL   COMMENT '操作对象类型（product/task等）',
  `target_id`   BIGINT UNSIGNED          DEFAULT NULL   COMMENT '操作对象ID',
  `detail`      JSON                                    COMMENT '操作详情（变更前后值等）',
  `ip`          VARCHAR(64)              DEFAULT NULL   COMMENT '客户端 IP',
  `created_at`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `idx_user_id` (`user_id`),
  INDEX `idx_action` (`action`),
  INDEX `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='操作审计日志';


-- ------------------------------------------------------------
-- 7. 汇率配置表
--    维护各货币对人民币汇率，定期更新
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `exchange_rates` (
  `id`           INT UNSIGNED  NOT NULL AUTO_INCREMENT COMMENT 'ID',
  `currency`     VARCHAR(8)    NOT NULL                COMMENT '货币代码（如 PHP、MYR、THB）',
  `rate_to_cny`  DECIMAL(10, 6) NOT NULL               COMMENT '兑换人民币汇率（1单位外币=?人民币）',
  `updated_at`   DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `idx_currency` (`currency`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='汇率配置';

-- 初始化常用汇率
INSERT INTO `exchange_rates` (`currency`, `rate_to_cny`) VALUES
  ('PHP', 0.1260),
  ('MYR', 1.5600),
  ('THB', 0.1980),
  ('SGD', 5.3500),
  ('IDR', 0.0004),
  ('VND', 0.0003)
ON DUPLICATE KEY UPDATE `rate_to_cny` = VALUES(`rate_to_cny`);


-- ------------------------------------------------------------
-- 8. 系统配置表
--    存储可动态调整的全局参数（如默认佣金率、每页条数等）
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `system_configs` (
  `id`          INT UNSIGNED  NOT NULL AUTO_INCREMENT,
  `config_key`  VARCHAR(64)   NOT NULL                COMMENT '配置键',
  `config_value` VARCHAR(512) NOT NULL                COMMENT '配置值',
  `description` VARCHAR(256)           DEFAULT NULL   COMMENT '说明',
  `updated_at`  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `idx_config_key` (`config_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='全局系统配置';

-- 初始化默认配置
INSERT INTO `system_configs` (`config_key`, `config_value`, `description`) VALUES
  ('default_platform_fee_rate', '0.05',   'TikTok 默认平台佣金率（5%）'),
  ('default_logistics_cost',    '15.00',  '默认物流成本（人民币）'),
  ('pdd_cache_ttl_minutes',     '30',     '拼多多价格缓存时长（分钟）'),
  ('crawl_max_retry',           '3',      '抓取任务最大重试次数'),
  ('page_size_default',         '20',     '列表默认每页条数')
ON DUPLICATE KEY UPDATE `config_value` = VALUES(`config_value`);


-- ============================================================
-- 9. 用户独立采集配置表
--    每个用户独立的 TikTok 采集配置（Cookie 和代理）
-- ============================================================
CREATE TABLE IF NOT EXISTS `user_crawl_configs` (
  `id`             INT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '配置ID',
  `user_id`        INT UNSIGNED NOT NULL                COMMENT '关联 users.id',
  `tiktok_cookies` TEXT              DEFAULT NULL        COMMENT 'TikTok Cookie JSON 字符串',
  `tiktok_proxy`   VARCHAR(256)      DEFAULT NULL        COMMENT 'TikTok 代理地址 (http://user:pass@host:port)',
  `created_at`     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `idx_user_id` (`user_id`),
  CONSTRAINT `fk_user_config_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户独立采集配置';
