"""add_last_used_at_to_tags

Revision ID: d842a75ff59e
Revises: ce8000af5443
Create Date: 2024-03-24 03:14:44.144537

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd842a75ff59e'
down_revision = 'ce8000af5443'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add last_used_at column, initially allowing NULL
    op.add_column('tags', sa.Column('last_used_at', sa.DateTime(), nullable=True))
    
    # Create index for performance
    op.create_index('ix_tags_last_used_at', 'tags', ['last_used_at'])
    
    # Update existing rows to set last_used_at = created_at
    op.execute("""
        UPDATE tags 
        SET last_used_at = created_at 
        WHERE last_used_at IS NULL
    """)
    
    # Now make the column non-nullable
    op.alter_column('tags', 'last_used_at',
                    existing_type=sa.DateTime(),
                    nullable=False)


def downgrade() -> None:
    # Drop the index first
    op.drop_index('ix_tags_last_used_at', table_name='tags')
    
    # Then drop the column
    op.drop_column('tags', 'last_used_at') 