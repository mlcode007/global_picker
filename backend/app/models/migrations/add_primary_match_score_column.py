"""
添加商品主参照图片相似度字段
"""
from sqlalchemy import create_engine, text
from app.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url)

sql = """
ALTER TABLE products
    ADD COLUMN primary_match_score DECIMAL(5, 4) NULL COMMENT '主参照商品图片相似度(拼多多或1688)';
"""

with engine.connect() as conn:
    conn.execute(text(sql))
    conn.commit()

print("Migration done: primary_match_score column added to products table")
