from datetime import datetime
from sqlalchemy import (
    BigInteger,
    TIMESTAMP,
    String
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from src.database import Base


class UserOrm(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email : Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    hashed_password : Mapped[str] = mapped_column(String(200), nullable=False)

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