"""initial_schema

Revision ID: initial_schema
Revises: 
Create Date: 2024-03-24 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'initial_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create logs table
    op.create_table(
        'logs',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('content', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('word_count', sa.Integer(), nullable=True),
        sa.Column('processing_status', sa.String(), nullable=True),
        sa.Column('embedding', sa.LargeBinary(), nullable=True),
        sa.Column('embedding_version', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create tags table
    op.create_table(
        'tags',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('color', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tags_name', 'tags', ['name'], unique=True)

    # Create queries table
    op.create_table(
        'queries',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('query_text', sa.String(), nullable=False),
        sa.Column('embedding', sa.LargeBinary(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('execution_time', sa.Float(), nullable=True),
        sa.Column('result_count', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create tag_log junction table
    op.create_table(
        'tag_log',
        sa.Column('tag_id', postgresql.UUID(), nullable=False),
        sa.Column('log_id', postgresql.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['log_id'], ['logs.id']),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id']),
        sa.PrimaryKeyConstraint('tag_id', 'log_id'),
        sa.UniqueConstraint('tag_id', 'log_id', name='uq_tag_log')
    )

    # Create query_results table
    op.create_table(
        'query_results',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('relevance_score', sa.Float(), nullable=False),
        sa.Column('snippet_text', sa.String(), nullable=False),
        sa.Column('snippet_start_index', sa.Integer(), nullable=False),
        sa.Column('snippet_end_index', sa.Integer(), nullable=False),
        sa.Column('context_before', sa.String(), nullable=True),
        sa.Column('context_after', sa.String(), nullable=True),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('query_id', postgresql.UUID(), nullable=False),
        sa.Column('log_id', postgresql.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['log_id'], ['logs.id']),
        sa.ForeignKeyConstraint(['query_id'], ['queries.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_query_results_rank', 'query_results', ['rank'])
    op.create_index('ix_query_results_relevance_score', 'query_results', ['relevance_score'])

def downgrade():
    op.drop_table('query_results')
    op.drop_table('tag_log')
    op.drop_table('queries')
    op.drop_table('tags')
    op.drop_table('logs') 