"""add workerpost banner fields

Revision ID: 1f4fbb0e0d21
Revises: 8311f40181d9
Create Date: 2026-04-20 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1f4fbb0e0d21"
down_revision: Union[str, None] = "8311f40181d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("workerpost", sa.Column("banner_video_path", sa.String(), nullable=True))
    op.add_column("workerpost", sa.Column("banner_x", sa.Float(), nullable=True))
    op.add_column("workerpost", sa.Column("banner_y", sa.Float(), nullable=True))
    op.add_column("workerpost", sa.Column("banner_width", sa.Float(), nullable=True))
    op.add_column("workerpost", sa.Column("banner_height", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("workerpost", "banner_height")
    op.drop_column("workerpost", "banner_width")
    op.drop_column("workerpost", "banner_y")
    op.drop_column("workerpost", "banner_x")
    op.drop_column("workerpost", "banner_video_path")
