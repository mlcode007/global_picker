from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,       # 连接前检测是否存活
    pool_recycle=3600,        # 每小时回收连接，防止 MySQL gone away
    pool_size=10,
    max_overflow=20,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI 依赖注入：提供数据库 Session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
