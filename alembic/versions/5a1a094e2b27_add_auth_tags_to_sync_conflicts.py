"""add_auth_tags_to_sync_conflicts

Revision ID: 5a1a094e2b27
Revises: 86d12dae3e45
Create Date: 2025-11-11 14:34:53.561973

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5a1a094e2b27'
down_revision = '86d12dae3e45'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('sync_conflicts', sa.Column('local_tag', sa.String(), nullable=True))
    op.add_column('sync_conflicts', sa.Column('remote_tag', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('sync_conflicts', 'remote_tag')
    op.drop_column('sync_conflicts', 'local_tag') 