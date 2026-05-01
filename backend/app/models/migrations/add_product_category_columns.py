"""
添加商品三级类目字段
"""
from sqlalchemy import create_engine, text
from app.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url)

sql = """
ALTER TABLE products
    ADD COLUMN category1_id VARCHAR(64) NULL COMMENT '一级类目ID',
    ADD COLUMN category1_name VARCHAR(128) NULL COMMENT '一级类目名称',
    ADD COLUMN category1_name_en VARCHAR(128) NULL COMMENT '一级类目英文名',
    ADD COLUMN category2_id VARCHAR(64) NULL COMMENT '二级类目ID',
    ADD COLUMN category2_name VARCHAR(128) NULL COMMENT '二级类目名称',
    ADD COLUMN category2_name_en VARCHAR(128) NULL COMMENT '二级类目英文名',
    ADD COLUMN category3_id VARCHAR(64) NULL COMMENT '三级类目ID',
    ADD COLUMN category3_name VARCHAR(128) NULL COMMENT '三级类目名称',
    ADD COLUMN category3_name_en VARCHAR(128) NULL COMMENT '三级类目英文名';
"""

with engine.connect() as conn:
    conn.execute(text(sql))
    conn.commit()

print("Migration done: category columns added to products table")
