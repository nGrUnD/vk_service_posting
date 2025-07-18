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
    mapped_column
)
from src.database import Base

class VKAccountOrm(Base):
    __tablename__ = "vk_account"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    vk_account_id: Mapped[int]
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    account_type: Mapped[str] # backup main poster

    proxy_id: Mapped[int] = mapped_column(ForeignKey("proxy.id"), nullable=True)

    encrypted_curl : Mapped[str] = mapped_column(String(10000), nullable=True)
    login : Mapped[str] = mapped_column(String(200), unique=True, nullable=True)
    encrypted_password : Mapped[str] = mapped_column(String(200), nullable=True)

    vk_account_url : Mapped[str]
    avatar_url: Mapped[str]
    name: Mapped[str]
    second_name: Mapped[str]
    groups_count: Mapped[int]
    flood_control: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
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

