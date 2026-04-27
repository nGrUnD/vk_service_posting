"""account_checker_batch.label + vk_account.account_checker_batch_id

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-04-28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "account_checker_batch",
        sa.Column("label", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "vk_account",
        sa.Column("account_checker_batch_id", sa.BigInteger(), nullable=True),
    )
    op.create_foreign_key(
        "fk_vk_account_account_checker_batch",
        "vk_account",
        "account_checker_batch",
        ["account_checker_batch_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_vk_account_account_checker_batch", "vk_account", type_="foreignkey")
    op.drop_column("vk_account", "account_checker_batch_id")
    op.drop_column("account_checker_batch", "label")
