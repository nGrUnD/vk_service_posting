from sqlalchemy import Boolean, BigInteger, ForeignKey
from src.database import Base
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

class CategoryOrm(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    clip_list_id: Mapped[int] = mapped_column(ForeignKey("clip_list.id"), nullable=True)
    name: Mapped[str]
    description: Mapped[str]
    repost_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    daily_limit: Mapped[int]
    hourly_limit: Mapped[int]
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
