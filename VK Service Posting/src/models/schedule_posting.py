from datetime import datetime

from sqlalchemy import (
    BigInteger,
    TIMESTAMP,
    ForeignKey,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column
)
from src.database import Base

class SchedulePostingOrm(Base):
    __tablename__ = "schedule_posting"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    workpost_id: Mapped[int] = mapped_column(ForeignKey("vk_group.id"), nullable=False)
    clip_id: Mapped[int]
    task_id: Mapped[str]
    status: Mapped[str]

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )