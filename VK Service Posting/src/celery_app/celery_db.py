from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from src.config import settings

engine = create_async_engine(
    settings.DB_URL,
    pool_size=5,          # Можно меньше, чем в FastAPI
    max_overflow=2,
    pool_timeout=30,
    pool_recycle=1800
)

AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)