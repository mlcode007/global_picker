-- ============================================================
-- Global Picker 拍照购业务表
-- 创建日期：2026-03-17
-- ============================================================

USE `global_picker`;

-- ------------------------------------------------------------
-- 1. 设备池表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `device_pool` (
  `id`              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
  `device_id`       VARCHAR(64)     NOT NULL                COMMENT 'ADB serial',
  `device_name`     VARCHAR(128)             DEFAULT NULL   COMMENT '设备别名',
  `device_type`     ENUM('real_phone','cloud_phone') NOT NULL DEFAULT 'real_phone' COMMENT '设备类型',
  `android_version` VARCHAR(16)              DEFAULT NULL   COMMENT 'Android 版本',
  `screen_width`    INT UNSIGNED             DEFAULT NULL   COMMENT '屏幕宽度',
  `screen_height`   INT UNSIGNED             DEFAULT NULL   COMMENT '屏幕高度',
  `app_package`     VARCHAR(128)    NOT NULL DEFAULT 'com.xunmeng.pinduoduo' COMMENT '拼多多包名',
  `app_version`     VARCHAR(32)              DEFAULT NULL   COMMENT '拼多多版本',
  `status`          ENUM('idle','busy','offline','error') NOT NULL DEFAULT 'idle' COMMENT '设备状态',
  `current_task_id` BIGINT UNSIGNED          DEFAULT NULL   COMMENT '当前执行任务',
  `last_heartbeat`  DATETIME                 DEFAULT NULL   COMMENT '最后心跳时间',
  `error_count`     INT UNSIGNED    NOT NULL DEFAULT 0      COMMENT '连续错误次数',
  `capabilities`    JSON                                    COMMENT '设备能力 {"root":false,"accessibility":false}',
  `created_at`      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `idx_device_id` (`device_id`),
  INDEX `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ADB 设备池';

-- 初始化你的设备
INSERT INTO `device_pool` (`device_id`, `device_name`, `device_type`, `android_version`, `screen_width`, `screen_height`)
VALUES ('120.55.50.221:10001', '阿里云手机', 'cloud_phone', '12', 720, 1280)
ON DUPLICATE KEY UPDATE `device_name` = VALUES(`device_name`), `device_type` = VALUES(`device_type`);


-- ------------------------------------------------------------
-- 2. 拍照购任务表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `photo_search_tasks` (
  `id`                BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `product_id`        BIGINT UNSIGNED NOT NULL                COMMENT '关联 products.id',
  `device_id`         VARCHAR(64)              DEFAULT NULL   COMMENT '执行设备',
  `status`            ENUM('queued','dispatching','running','collecting','parsing','saving','success','failed','retry_waiting','cancelled')
                      NOT NULL DEFAULT 'queued'               COMMENT '任务主状态',
  `step`              VARCHAR(32)              DEFAULT NULL   COMMENT '当前执行子步骤',
  `source_image_url`  VARCHAR(1024)            DEFAULT NULL   COMMENT '搜索用图片 URL',
  `device_image_path` VARCHAR(512)             DEFAULT NULL   COMMENT '设备端图片路径',
  `attempt_count`     TINYINT UNSIGNED NOT NULL DEFAULT 0     COMMENT '已尝试次数',
  `max_attempts`      TINYINT UNSIGNED NOT NULL DEFAULT 3     COMMENT '最大尝试次数',
  `candidates_found`  INT UNSIGNED    NOT NULL DEFAULT 0      COMMENT '找到候选商品数',
  `candidates_saved`  INT UNSIGNED    NOT NULL DEFAULT 0      COMMENT '入库候选商品数',
  `error_code`        VARCHAR(64)              DEFAULT NULL   COMMENT '错误码',
  `error_message`     TEXT                                    COMMENT '错误详情',
  `started_at`        DATETIME                 DEFAULT NULL   COMMENT '开始执行时间',
  `finished_at`       DATETIME                 DEFAULT NULL   COMMENT '完成时间',
  `elapsed_ms`        INT UNSIGNED             DEFAULT NULL   COMMENT '总耗时毫秒',
  `raw_result_json`   JSON                                    COMMENT '原始采集结果',
  `created_at`        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `idx_product_id` (`product_id`),
  INDEX `idx_status` (`status`),
  INDEX `idx_device_id` (`device_id`),
  CONSTRAINT `fk_photo_task_product` FOREIGN KEY (`product_id`) REFERENCES `products` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='拼多多拍照购任务';


-- ------------------------------------------------------------
-- 3. 设备动作日志表
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `device_action_logs` (
  `id`              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `task_id`         BIGINT UNSIGNED NOT NULL                COMMENT '关联 photo_search_tasks.id',
  `device_id`       VARCHAR(64)     NOT NULL                COMMENT 'ADB serial',
  `step`            VARCHAR(32)     NOT NULL                COMMENT '状态机步骤',
  `action`          VARCHAR(128)    NOT NULL                COMMENT '具体动作描述',
  `success`         TINYINT(1)      NOT NULL DEFAULT 1      COMMENT '是否成功',
  `elapsed_ms`      INT UNSIGNED             DEFAULT NULL   COMMENT '动作耗时',
  `screenshot_path` VARCHAR(512)             DEFAULT NULL   COMMENT '截图文件路径',
  `xml_dump_path`   VARCHAR(512)             DEFAULT NULL   COMMENT 'UI XML 文件路径',
  `ocr_text`        TEXT                                    COMMENT 'OCR 识别文本',
  `extra`           JSON                                    COMMENT '补充数据',
  `message`         TEXT                                    COMMENT '日志信息',
  `created_at`      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  INDEX `idx_task_id` (`task_id`),
  INDEX `idx_device_step` (`device_id`, `step`),
  CONSTRAINT `fk_action_log_task` FOREIGN KEY (`task_id`) REFERENCES `photo_search_tasks` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='设备执行动作日志';
