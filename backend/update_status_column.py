from sqlalchemy import create_engine, MetaData, Table, Column, String
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取数据库连接信息
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '3306')
DB_NAME = os.getenv('DB_NAME', 'global_picker')

# 创建数据库引擎
engine = create_engine(f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}')

# 创建元数据对象
metadata = MetaData()

# 定义表结构
cloud_phone_pool = Table('cloud_phone_pool', metadata, autoload_with=engine)

# 检查并修改 status 列长度
with engine.connect() as conn:
    # 执行 ALTER TABLE 语句
    conn.execute("ALTER TABLE cloud_phone_pool MODIFY COLUMN status VARCHAR(20) NOT NULL DEFAULT 'available'")
    conn.commit()
    print("Updated cloud_phone_pool.status column length to VARCHAR(20)")
