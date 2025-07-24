"""add_weaviate_id_to_logs

Revision ID: a1e63fe98111
Revises: remove_embedding_fields
Create Date: 2025-07-24 02:12:05.953385

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1e63fe98111'
down_revision = 'remove_embedding_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add weaviate_id column
    op.add_column('logs', sa.Column('weaviate_id', sa.String(), nullable=True))
    
    # Create unique constraint on weaviate_id
    op.create_unique_constraint('uq_logs_weaviate_id', 'logs', ['weaviate_id'])
    
    # Migrate existing data - copy current id to weaviate_id
    op.execute("""
        UPDATE logs 
        SET weaviate_id = CAST(id AS VARCHAR)
        WHERE weaviate_id IS NULL
    """)


def downgrade() -> None:
    # Remove unique constraint
    op.drop_constraint('uq_logs_weaviate_id', 'logs')
    
    # Remove weaviate_id column
    op.drop_column('logs', 'weaviate_id') 