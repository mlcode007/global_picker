#!/usr/bin/env python3
"""创建 alibaba1688_matches 表"""
from app.database import engine
from sqlalchemy import text

sql = """
CREATE TABLE IF NOT EXISTS alibaba1688_matches (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  product_id BIGINT UNSIGNED NOT NULL,
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
  match_source ENUM('image_search','manual') NOT NULL DEFAULT 'image_search',
  is_confirmed TINYINT(1) NOT NULL DEFAULT 0,
  is_primary TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_product_id (product_id),
  KEY idx_is_primary (product_id, is_primary),
  CONSTRAINT fk_alibaba1688_product FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='1688商品匹配结果';
"""

with engine.connect() as conn:
    conn.execute(text(sql))
    conn.commit()
    print("Table alibaba1688_matches created successfully")
