"""fix_is_active_on_users_and_teams

Revision ID: 7fb6b4390738
Revises: 1e20803a61b8
Create Date: 2026-05-18 17:05:24.741366

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7fb6b4390738'
down_revision: Union[str, Sequence[str], None] = '1e20803a61b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE users SET is_active = true WHERE is_active IS NULL")
    op.execute("UPDATE teams SET is_active = true WHERE is_active IS NULL")

    op.alter_column('users', 'is_active',
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text('true')
    )
    op.alter_column('teams', 'is_active',
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text('true')
    )


def downgrade() -> None:
    op.alter_column('users', 'is_active',
        existing_type=sa.Boolean(),
        nullable=True,
        server_default=None
    )
    op.alter_column('teams', 'is_active',
        existing_type=sa.Boolean(),
        nullable=True,
        server_default=None
    )
