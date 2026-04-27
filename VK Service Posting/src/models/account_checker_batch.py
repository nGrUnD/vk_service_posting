from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Integer,
    String,
    TIMESTAMP,
    ForeignKey,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.database import Base


class AccountCheckerBatchOrm(Base):
    __tablename__ = "account_checker_batch"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)

    total_tasks: Mapped[int] = mapped_column(Integer, nullable=False)
    completed_tasks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # pending -> processing: после постановки в очередь; completed: все таски завершились
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
    )
