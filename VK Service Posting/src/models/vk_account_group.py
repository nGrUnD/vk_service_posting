from sqlalchemy import Column, BigInteger, Integer, String, Boolean, TIMESTAMP, ForeignKey, text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
#from src.models.vk_account import VKAccountOrm
#from src.models.vk_group import VKGroupOrm

Base = declarative_base()


class VKAccountGroupOrm(Base):
    __tablename__ = "vk_account_group"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    vk_account_id = Column(BigInteger, ForeignKey("vk_account.id", ondelete="CASCADE"), nullable=False)
    vk_group_id = Column(BigInteger, ForeignKey("vk_group.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False)  # 'main', 'poster'

    created_at = Column(TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False)

    # Relationships
    #vk_account = relationship("VKAccountOrm", back_populates="account_groups")
    #vk_group = relationship("VKGroupOrm", back_populates="account_groups")