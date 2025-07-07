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
from src.models.vk_account_cred import VKAccountCredOrm
from src.database import Base

class VKAccountOrm(Base):
    __tablename__ = "vk_account"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    vk_account_id: Mapped[int]
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    account_type: Mapped[str] # backup main poster

    vk_cred_id: Mapped[int] = mapped_column(ForeignKey("vk_account_cred.id"), nullable=True)
    proxy_id: Mapped[int] = mapped_column(ForeignKey("proxy.id"), nullable=True)

    encrypted_curl : Mapped[str] = mapped_column(String(10000), nullable=False)
    vk_account_url : Mapped[str]
    avatar_url: Mapped[str]
    name: Mapped[str]
    second_name: Mapped[str]
    groups_count: Mapped[int]
    flood_control: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    parse_status: Mapped[str]
    task_id: Mapped[str]

    vk_cred = relationship("VKAccountCredOrm", backref="vk_account", lazy="joined")

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

