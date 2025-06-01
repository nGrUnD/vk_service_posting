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
    mapped_column,
)

from src.database import Base

class VKGroupOrm(Base):
    __tablename__ = "vk_group"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    vk_group_id: Mapped[int]
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    vk_admin_main_id: Mapped[int] = mapped_column(ForeignKey("vk_account.id"), nullable=True)
    vk_admin_poster_id: Mapped[int] = mapped_column(ForeignKey("vk_account.id"), nullable=True)

    vk_group_type : Mapped[str] # source | poster | main
    vk_group_url : Mapped[str]
    avatar_url: Mapped[str]
    name: Mapped[str]
    clips_count: Mapped[int]
    parse_status: Mapped[str]
    task_id: Mapped[str]

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

