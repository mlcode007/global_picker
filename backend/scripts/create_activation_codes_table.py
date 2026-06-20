"""
创建激活码表
用于直播/线下销售场景，管理员生成激活码，用户兑换后自动开通会员
"""
from app.database import engine
from sqlalchemy import text

# 建表 SQL
SQL = """
CREATE TABLE IF NOT EXISTS `activation_codes` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `code` VARCHAR(20) NOT NULL UNIQUE COMMENT '激活码',
    `tier` VARCHAR(20) NOT NULL DEFAULT 'basic' COMMENT '会员等级: basic/pro',
    `duration_months` INT NOT NULL DEFAULT 1 COMMENT '有效期（月）',
    `max_uses` INT NOT NULL DEFAULT 1 COMMENT '最大使用次数',
    `used_count` INT NOT NULL DEFAULT 0 COMMENT '已使用次数',
    `is_active` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '是否启用',
    `remark` VARCHAR(256) DEFAULT NULL COMMENT '备注',
    `created_by` INT DEFAULT NULL COMMENT '创建人',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `expires_at` DATETIME DEFAULT NULL COMMENT '激活码过期时间',
    INDEX `idx_code` (`code`),
    INDEX `idx_is_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='激活码表';
"""

def run():
    with engine.connect() as conn:
        conn.execute(text(SQL))
        conn.commit()
    print("✅ activation_codes 表创建成功")

if __name__ == "__main__":
    run()
