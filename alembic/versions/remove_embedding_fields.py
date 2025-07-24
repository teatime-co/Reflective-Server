"""Remove embedding fields from Log model

Revision ID: remove_embedding_fields
Revises: # will be filled by alembic
Create Date: 2024-03-24 01:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'remove_embedding_fields'
down_revision = None  # will be filled by alembic
branch_labels = None
depends_on = None

def upgrade():
    # Remove embedding and embedding_version columns from logs table
    op.drop_column('logs', 'embedding')
    op.drop_column('logs', 'embedding_version')

def downgrade():
    # Add back embedding and embedding_version columns if needed to rollback
    op.add_column('logs', sa.Column('embedding', sa.LargeBinary(), nullable=True))
    op.add_column('logs', sa.Column('embedding_version', sa.String(), nullable=True)) 