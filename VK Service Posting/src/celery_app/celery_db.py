from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from your_project.settings import settings

engine = create_async_engine(
    settings.DB_URL,
    pool_size=5,          # Можно меньше, чем в FastAPI
    max_overflow=2,
    pool_timeout=30,
    pool_recycle=1800
)

AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)