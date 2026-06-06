"""
数据库迁移脚本：为 pdd_matches 和 alibaba1688_matches 表添加 match_score 字段

执行方式：
    python backend/scripts/add_match_score_column.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from app.database import SessionLocal, engine


def add_match_score_column():
    """为匹配表添加 match_score 字段"""
    conn = engine.connect()

    # pdd_matches 表：match_score 放在 match_confidence 之后
    try:
        check_sql = text(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() "
            "AND TABLE_NAME = 'pdd_matches' "
            "AND COLUMN_NAME = 'match_score'"
        )
        result = conn.execute(check_sql)
        exists = result.scalar()

        if exists == 0:
            alter_sql = text(
                "ALTER TABLE pdd_matches "
                "ADD COLUMN match_score DECIMAL(5,4) NULL "
                "COMMENT '图片相似度分数(0~1)' AFTER match_confidence"
            )
            conn.execute(alter_sql)
            print("Added match_score column to pdd_matches")
        else:
            print("match_score column already exists in pdd_matches")
    except Exception as e:
        print(f"Error processing pdd_matches: {e}")

    # alibaba1688_matches 表：没有 match_confidence 字段，直接添加到最后
    try:
        check_sql = text(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() "
            "AND TABLE_NAME = 'alibaba1688_matches' "
            "AND COLUMN_NAME = 'match_score'"
        )
        result = conn.execute(check_sql)
        exists = result.scalar()

        if exists == 0:
            alter_sql = text(
                "ALTER TABLE alibaba1688_matches "
                "ADD COLUMN match_score DECIMAL(5,4) NULL "
                "COMMENT '图片相似度分数(0~1)'"
            )
            conn.execute(alter_sql)
            print("Added match_score column to alibaba1688_matches")
        else:
            print("match_score column already exists in alibaba1688_matches")
    except Exception as e:
        print(f"Error processing alibaba1688_matches: {e}")

    conn.close()
    print("Migration completed!")


if __name__ == "__main__":
    add_match_score_column()
