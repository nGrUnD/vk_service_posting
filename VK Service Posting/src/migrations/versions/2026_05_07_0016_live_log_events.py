"""live log events

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "live_log_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("logtype", sa.String(length=50), nullable=False),
        sa.Column("log", sa.String(length=500), nullable=False),
        sa.Column("logdescription", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_live_log_events_user_created_at",
        "live_log_events",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_live_log_events_user_logtype_created_at",
        "live_log_events",
        ["user_id", "logtype", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_live_log_events_user_logtype_created_at", table_name="live_log_events")
    op.drop_index("ix_live_log_events_user_created_at", table_name="live_log_events")
    op.drop_table("live_log_events")
