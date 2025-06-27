from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.config import settings


engine = create_async_engine(
    settings.DB_URL,
    pool_size=20,          # Максимальное количество соединений в пуле
    max_overflow=10,       # Дополнительные соединения сверх pool_size
    pool_timeout=30,       # Таймаут ожидания свободного соединения
    pool_recycle=1800      # Время (сек) для пересоздания соединения
)

async_session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass