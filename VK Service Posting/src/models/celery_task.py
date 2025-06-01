from datetime import datetime
from sqlalchemy import (
    BigInteger,
    TIMESTAMP,
    ForeignKey,
    String, func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from src.database import Base

class CeleryTaskOrm(Base):
    __tablename__ = "celery_tasks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    vk_account_id: Mapped[int] = mapped_column(ForeignKey("vk_account.id"), nullable=True)
    clip_list_id: Mapped[int] = mapped_column(ForeignKey("clip_list.id"), nullable=True)

    vk_group_url: Mapped[str] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(200), nullable=True, default="started")  # pending, started, success, failure
    type: Mapped[str] = mapped_column(String(200), nullable=True)  # ["add account", "parse account", "parse source group"]

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
