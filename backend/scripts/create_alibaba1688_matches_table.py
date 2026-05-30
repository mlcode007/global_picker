"""
创建 alibaba1688_matches 表
"""
from sqlalchemy import text
from app.database import SessionLocal


def create_table():
    sql = """
    CREATE TABLE IF NOT EXISTS alibaba1688_matches (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        product_id BIGINT NOT NULL,
        offer_id VARCHAR(64) DEFAULT NULL,
        member_id VARCHAR(64) DEFAULT NULL,
        title VARCHAR(512) NOT NULL DEFAULT '',
        main_image VARCHAR(1024) DEFAULT NULL,
        images VARCHAR(2048) DEFAULT NULL,
        last30_days_sales VARCHAR(64) DEFAULT NULL,
        total_sales VARCHAR(64) DEFAULT NULL,
        good_rates DECIMAL(5,2) DEFAULT NULL,
        repurchase_rate VARCHAR(32) DEFAULT NULL,
        tp_year INT DEFAULT NULL,
        free_return_in7d VARCHAR(32) DEFAULT NULL,
        support_waybill VARCHAR(256) DEFAULT NULL,
        price DECIMAL(12,2) NOT NULL DEFAULT 0,
        match_source ENUM('image_search', 'manual') NOT NULL DEFAULT 'image_search',
        is_confirmed TINYINT(1) NOT NULL DEFAULT 0,
        is_primary TINYINT(1) NOT NULL DEFAULT 0,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
        INDEX idx_product_id (product_id),
        INDEX idx_is_primary (is_primary)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    db = SessionLocal()
    try:
        db.execute(text(sql))
        db.commit()
        print("alibaba1688_matches table created successfully")
    except Exception as e:
        db.rollback()
        print(f"Error creating table: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    create_table()
