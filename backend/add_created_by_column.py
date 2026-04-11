from app.database import engine
from sqlalchemy import text

print('Adding created_by column to cloud_phone_pool table...')

with engine.connect() as conn:
    # 检查 created_by 字段是否已存在
    result = conn.execute(text('DESCRIBE cloud_phone_pool'))
    columns = [row[0] for row in result]
    
    if 'created_by' not in columns:
        # 添加 created_by 字段
        conn.execute(text('ALTER TABLE cloud_phone_pool ADD COLUMN created_by INT NULL COMMENT \'创建用户ID\''))
        conn.commit()
        print('Column added successfully!')
    else:
        print('Column already exists!')
    
    # 检查表结构
    print('Checking table structure...')
    result = conn.execute(text('DESCRIBE cloud_phone_pool'))
    for row in result:
        print(row)