-- 创建用户积分表
CREATE TABLE IF NOT EXISTS `user_points` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL COMMENT '用户ID',
  `points` int(11) NOT NULL DEFAULT '0' COMMENT '当前积分',
  `total_earned` int(11) NOT NULL DEFAULT '0' COMMENT '总获取积分',
  `total_consumed` int(11) NOT NULL DEFAULT '0' COMMENT '总消耗积分',
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 创建积分交易记录表
CREATE TABLE IF NOT EXISTS `points_transaction` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `user_id` int(11) NOT NULL COMMENT '用户ID',
  `type` enum('earn','consume') NOT NULL COMMENT '交易类型',
  `amount` int(11) NOT NULL COMMENT '积分数量',
  `reason` text NOT NULL COMMENT '交易原因',
  `related_id` varchar(128) DEFAULT NULL COMMENT '关联ID',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;