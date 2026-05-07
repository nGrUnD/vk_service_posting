from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, String, TIMESTAMP, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class LiveLogOrm(Base):
    __tablename__ = "live_log_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    logtype: Mapped[str] = mapped_column(String(50), nullable=False)
    log: Mapped[str] = mapped_column(String(500), nullable=False)
    logdescription: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
