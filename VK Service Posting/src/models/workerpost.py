from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Float,
    TIMESTAMP,
    ForeignKey,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column, relationship,
)
from src.database import Base
from src.models.vk_account import VKAccountOrm
from src.models.vk_group import VKGroupOrm
from src.models.category import CategoryOrm


class WorkerPostOrm(Base):
    __tablename__ = "workerpost"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    vk_group_id: Mapped[int] = mapped_column(ForeignKey("vk_group.id"), nullable=False)
    vk_account_id: Mapped[int] = mapped_column(ForeignKey("vk_account.id"), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)

    is_active: Mapped[bool]
    banner_video_path: Mapped[str | None] = mapped_column(nullable=True)
    banner_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    banner_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    banner_width: Mapped[float | None] = mapped_column(Float, nullable=True)
    banner_height: Mapped[float | None] = mapped_column(Float, nullable=True)


    last_post_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

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

    vk_group = relationship("VKGroupOrm", backref="worker_posts")
    vk_account = relationship("VKAccountOrm", backref="worker_posts")
    category = relationship("CategoryOrm", backref="worker_posts")