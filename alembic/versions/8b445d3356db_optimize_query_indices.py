"""optimize_query_indices

Revision ID: 8b445d3356db
Revises: remove_embedding_fields
Create Date: 2024-03-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '8b445d3356db'
down_revision = 'remove_embedding_fields'
branch_labels = None
depends_on = None


def upgrade():
    # Add indices for better query performance
    op.create_index('ix_queries_query_text', 'queries', ['query_text'])
    op.create_index('ix_queries_created_at', 'queries', ['created_at'])
    op.create_index('ix_logs_weaviate_id', 'logs', ['weaviate_id'])
    
    # Add constraints
    op.create_check_constraint(
        'ck_queries_query_text_not_empty',
        'queries',
        sa.text("query_text != ''")
    )
    op.create_check_constraint(
        'ck_queries_result_count_non_negative',
        'queries',
        sa.text('result_count >= 0')
    )
    op.create_check_constraint(
        'ck_queries_execution_time_non_negative',
        'queries',
        sa.text('execution_time >= 0')
    )
    op.create_check_constraint(
        'ck_query_results_relevance_score_range',
        'query_results',
        sa.text('relevance_score >= 0 AND relevance_score <= 1')
    )
    op.create_check_constraint(
        'ck_query_results_snippet_indices',
        'query_results',
        sa.text('snippet_end_index >= snippet_start_index')
    )


def downgrade():
    # Remove constraints
    op.drop_constraint('ck_query_results_snippet_indices', 'query_results')
    op.drop_constraint('ck_query_results_relevance_score_range', 'query_results')
    op.drop_constraint('ck_queries_execution_time_non_negative', 'queries')
    op.drop_constraint('ck_queries_result_count_non_negative', 'queries')
    op.drop_constraint('ck_queries_query_text_not_empty', 'queries')
    
    # Remove indices
    op.drop_index('ix_logs_weaviate_id')
    op.drop_index('ix_queries_created_at')
    op.drop_index('ix_queries_query_text') 