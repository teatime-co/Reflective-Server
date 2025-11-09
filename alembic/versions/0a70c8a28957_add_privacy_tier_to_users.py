"""add_privacy_tier_to_users

Revision ID: 0a70c8a28957
Revises: 0312cb6ab39f
Create Date: 2025-11-09 18:49:29.157956

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0a70c8a28957'
down_revision = '0312cb6ab39f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE privacy_tier_enum AS ENUM ('local_only', 'analytics_sync', 'full_sync');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    op.add_column('users', sa.Column('privacy_tier', sa.Enum('local_only', 'analytics_sync', 'full_sync', name='privacy_tier_enum'), nullable=False, server_default='local_only'))
    op.add_column('users', sa.Column('he_public_key', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('sync_enabled_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'sync_enabled_at')
    op.drop_column('users', 'he_public_key')
    op.drop_column('users', 'privacy_tier')

    op.execute("DROP TYPE privacy_tier_enum") 