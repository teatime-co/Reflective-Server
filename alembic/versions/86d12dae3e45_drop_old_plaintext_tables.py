"""drop_old_plaintext_tables

Revision ID: 86d12dae3e45
Revises: 450c5575b021
Create Date: 2025-11-09 23:50:47.281161

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '86d12dae3e45'
down_revision = '450c5575b021'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop junction tables first (have foreign keys)
    op.drop_table('tag_log')
    op.drop_table('log_theme')

    # Drop tables with foreign keys to logs
    op.drop_table('query_results')
    op.drop_table('entry_revisions')
    op.drop_table('linguistic_metrics')

    # Drop main tables
    op.drop_table('queries')
    op.drop_table('logs')
    op.drop_table('themes')
    op.drop_table('user_insights')
    op.drop_table('prompts')
    op.drop_table('writing_sessions')


def downgrade() -> None:
    # NOTE: Downgrade not implemented - this is a destructive migration
    # Old tables are removed as part of fresh start architecture
    pass 