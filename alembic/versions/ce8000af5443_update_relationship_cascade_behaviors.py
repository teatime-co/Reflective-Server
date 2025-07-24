"""update_relationship_cascade_behaviors

Revision ID: ce8000af5443
Revises: a1e63fe98111
Create Date: 2025-07-24 02:37:44.144537

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ce8000af5443'
down_revision = 'a1e63fe98111'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # First drop all existing foreign key constraints
    # QueryResult constraints
    op.drop_constraint('query_results_query_id_fkey', 'query_results', type_='foreignkey')
    op.drop_constraint('query_results_log_id_fkey', 'query_results', type_='foreignkey')
    
    # TagLog constraints
    op.drop_constraint('tag_log_tag_id_fkey', 'tag_log', type_='foreignkey')
    op.drop_constraint('tag_log_log_id_fkey', 'tag_log', type_='foreignkey')
    
    # Recreate all foreign key constraints with appropriate delete behaviors
    
    # 1. QueryResult relationships
    # When Query is deleted, delete its QueryResults (CASCADE)
    op.create_foreign_key(
        'query_results_query_id_fkey', 'query_results', 'queries',
        ['query_id'], ['id'], ondelete='CASCADE'
    )
    # When Log is deleted, prevent if it has QueryResults (NO ACTION)
    op.create_foreign_key(
        'query_results_log_id_fkey', 'query_results', 'logs',
        ['log_id'], ['id'], ondelete='NO ACTION'
    )
    
    # 2. TagLog relationships
    # When Tag is deleted, only delete the junction table entries (CASCADE)
    op.create_foreign_key(
        'tag_log_tag_id_fkey', 'tag_log', 'tags',
        ['tag_id'], ['id'], ondelete='CASCADE'
    )
    # When Log is deleted, only delete the junction table entries (CASCADE)
    op.create_foreign_key(
        'tag_log_log_id_fkey', 'tag_log', 'logs',
        ['log_id'], ['id'], ondelete='CASCADE'
    )


def downgrade() -> None:
    # Drop all constraints
    op.drop_constraint('query_results_query_id_fkey', 'query_results', type_='foreignkey')
    op.drop_constraint('query_results_log_id_fkey', 'query_results', type_='foreignkey')
    op.drop_constraint('tag_log_tag_id_fkey', 'tag_log', type_='foreignkey')
    op.drop_constraint('tag_log_log_id_fkey', 'tag_log', type_='foreignkey')
    
    # Recreate all with default behavior (NO ACTION)
    op.create_foreign_key(
        'query_results_query_id_fkey', 'query_results', 'queries',
        ['query_id'], ['id']
    )
    op.create_foreign_key(
        'query_results_log_id_fkey', 'query_results', 'logs',
        ['log_id'], ['id']
    )
    op.create_foreign_key(
        'tag_log_tag_id_fkey', 'tag_log', 'tags',
        ['tag_id'], ['id']
    )
    op.create_foreign_key(
        'tag_log_log_id_fkey', 'tag_log', 'logs',
        ['log_id'], ['id']
    ) 