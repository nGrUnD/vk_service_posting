from datetime import datetime
from sqlalchemy import (
    BigInteger,
    TIMESTAMP,
    String, ForeignKey,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)
from src.database import Base

class ProxyOrm(Base):
    __tablename__ = "proxy"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)

    http: Mapped[str] = mapped_column(String(200), nullable=False)

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