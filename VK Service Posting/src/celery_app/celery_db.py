from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import settings

engine = create_engine(
    settings.DB_URL.replace('+asyncpg', ''),  # Убираем async
    pool_pre_ping=True
)

SyncSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)