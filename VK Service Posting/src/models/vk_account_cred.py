from datetime import datetime
from sqlalchemy import (
    BigInteger,
    TIMESTAMP,
    ForeignKey,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from src.database import Base

class VKAccountCredOrm(Base):
    __tablename__ = "vk_account_cred"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    login : Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    encrypted_password : Mapped[str] = mapped_column(String(200), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default="NOW()",
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default="NOW()",
        onupdate="NOW()",
    )