from sqlalchemy import Column, BigInteger, Integer, String, Boolean, TIMESTAMP, ForeignKey, text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
#from src.models.vk_account import VKAccountOrm
#from src.models.vk_group import VKGroupOrm
from src.database import Base


class VKAccountGroupOrm(Base):
    __tablename__ = "vk_account_group"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    vk_account_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("vk_account.id", ondelete="CASCADE"), nullable=False)
    vk_group_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("vk_group.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)  # 'main', 'poster', 'backup', 'connect'

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
    # Relationships
    #vk_account = relationship("VKAccountOrm", back_populates="account_groups")
    #vk_group = relationship("VKGroupOrm", back_populates="account_groups")