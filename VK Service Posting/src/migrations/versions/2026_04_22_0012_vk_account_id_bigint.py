"""change vk_account.vk_account_id to bigint

Revision ID: 6c1e8a9bb2f4
Revises: 1f4fbb0e0d21
Create Date: 2026-04-22 18:35:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6c1e8a9bb2f4"
down_revision: Union[str, None] = "1f4fbb0e0d21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "vk_account",
        "vk_account_id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
        postgresql_using="vk_account_id::bigint",
    )


def downgrade() -> None:
    op.alter_column(
        "vk_account",
        "vk_account_id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
        postgresql_using="vk_account_id::integer",
    )
