"""add_unique_constraint_to_team_name

Revision ID: f16a2694d019
Revises: 7fb6b4390738
Create Date: 2026-05-19 00:09:15.695362

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f16a2694d019'
down_revision: Union[str, Sequence[str], None] = '7fb6b4390738'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index(op.f('ix_teams_name'), table_name='teams')
    op.create_index(op.f('ix_teams_name'), 'teams', ['name'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_teams_name'), table_name='teams')
    op.create_index(op.f('ix_teams_name'), 'teams', ['name'], unique=False)
