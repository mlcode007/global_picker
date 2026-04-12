from sqlalchemy import create_engine, text
from app.config import get_settings

settings = get_settings()

# 创建数据库引擎
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_size=10,
    max_overflow=20,
    echo=True,
)

# 执行 SQL 语句
with engine.connect() as conn:
    # 检查字段是否已经存在
    check_sql = """
    SELECT COLUMN_NAME
    FROM information_schema.COLUMNS
    WHERE TABLE_NAME = 'cloud_phone_pool' AND COLUMN_NAME = 'adb_host_port'
    """
    result = conn.execute(text(check_sql))
    if result.fetchone():
        print("adb_host_port 字段已经存在")
    else:
        # 添加字段
        alter_sql = """
        ALTER TABLE cloud_phone_pool
        ADD COLUMN adb_host_port VARCHAR(64) DEFAULT NULL COMMENT 'ADB连接端口'
        """
        conn.execute(text(alter_sql))
        conn.commit()
        print("adb_host_port 字段添加成功")

print("操作完成")
