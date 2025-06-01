from datetime import datetime

from sqlalchemy import (
    BigInteger,
    TIMESTAMP,
    ForeignKey,
    String,
    Boolean, func
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column, relationship,
)
from src.database import Base

class VKClipOrm(Base):
    __tablename__ = "vk_clip"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    clip_list_id: Mapped[int] = mapped_column(ForeignKey("clip_list.id"), nullable=True)
    vk_group_id: Mapped[int] = mapped_column(ForeignKey("vk_group.id"), nullable=True)

    vk_id: Mapped[int]
    files: Mapped[str]
    views: Mapped[int]
    date: Mapped[datetime]
    frames_file: Mapped[str]


    parse_status: Mapped[str]
    task_id: Mapped[str]

    #clip_list = relationship("src.models.clip_list.ClipListOrm", back_populates="clips", lazy="selectin")

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

