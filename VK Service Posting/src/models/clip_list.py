from datetime import datetime

from sqlalchemy import (
    BigInteger,
    TIMESTAMP,
    ForeignKey,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column, relationship,
)
from src.database import Base
from src.models.vk_clip import VKClipOrm


class ClipListOrm(Base):
    __tablename__ = "clip_list"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    name: Mapped[str]
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)

    parse_status: Mapped[str]
    task_id: Mapped[str]

    clips = relationship("VKClipOrm", backref="clip_list", lazy="selectin")

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

