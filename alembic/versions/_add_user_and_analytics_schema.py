"""add user and analytics schema

Revision ID: add_user_and_analytics
Revises: ce8000af5443
Create Date: 2024-03-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_user_and_analytics'
down_revision = 'ce8000af5443'
branch_labels = None
depends_on = None

def upgrade():
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=True),
        sa.Column('timezone', sa.String(), nullable=False, server_default='UTC'),
        sa.Column('locale', sa.String(), nullable=False, server_default='en-US'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('daily_word_goal', sa.Integer(), nullable=False, server_default='750'),
        sa.Column('writing_reminder_time', sa.String(), nullable=True),
        sa.Column('theme_preferences', postgresql.JSON(), nullable=True),
        sa.Column('ai_features_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_users_email', 'users', ['email'])

    # Create writing_sessions table
    op.create_table(
        'writing_sessions',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('user_id', postgresql.UUID(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('session_type', sa.String(), nullable=True),
        sa.Column('interruption_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('focus_score', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create themes table
    op.create_table(
        'themes',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('confidence_threshold', sa.Float(), nullable=False, server_default='0.7'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Create prompts table
    op.create_table(
        'prompts',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('user_id', postgresql.UUID(), nullable=False),
        sa.Column('prompt_text', sa.String(), nullable=False),
        sa.Column('prompt_type', sa.String(), nullable=True),
        sa.Column('effectiveness_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('generation_context', postgresql.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create user_insights table
    op.create_table(
        'user_insights',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('user_id', postgresql.UUID(), nullable=False),
        sa.Column('insight_type', sa.String(), nullable=False),
        sa.Column('insight_data', postgresql.JSON(), nullable=False),
        sa.Column('date_range_start', sa.DateTime(), nullable=False),
        sa.Column('date_range_end', sa.DateTime(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='new'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create log_theme association table
    op.create_table(
        'log_theme',
        sa.Column('theme_id', postgresql.UUID(), nullable=False),
        sa.Column('log_id', postgresql.UUID(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column('detected_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['log_id'], ['logs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['theme_id'], ['themes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('theme_id', 'log_id'),
        sa.UniqueConstraint('theme_id', 'log_id', name='uq_theme_log')
    )

    # Create linguistic_metrics table
    op.create_table(
        'linguistic_metrics',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('log_id', postgresql.UUID(), nullable=False),
        sa.Column('vocabulary_diversity_score', sa.Float(), nullable=True),
        sa.Column('sentiment_score', sa.Float(), nullable=True),
        sa.Column('complexity_score', sa.Float(), nullable=True),
        sa.Column('readability_level', sa.Float(), nullable=True),
        sa.Column('emotion_scores', postgresql.JSON(), nullable=True),
        sa.Column('writing_style_metrics', postgresql.JSON(), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['log_id'], ['logs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create entry_revisions table
    op.create_table(
        'entry_revisions',
        sa.Column('id', postgresql.UUID(), nullable=False),
        sa.Column('log_id', postgresql.UUID(), nullable=False),
        sa.Column('revision_number', sa.Integer(), nullable=False),
        sa.Column('content_delta', postgresql.JSON(), nullable=False),
        sa.Column('revision_type', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['log_id'], ['logs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Add user_id to logs table
    op.add_column('logs', sa.Column('user_id', postgresql.UUID(), nullable=True))
    op.add_column('logs', sa.Column('session_id', postgresql.UUID(), nullable=True))
    op.add_column('logs', sa.Column('prompt_id', postgresql.UUID(), nullable=True))
    op.add_column('logs', sa.Column('mood_score', sa.Float(), nullable=True))
    op.add_column('logs', sa.Column('completion_status', sa.String(), server_default='draft', nullable=True))
    op.add_column('logs', sa.Column('target_word_count', sa.Integer(), server_default='750', nullable=True))
    op.add_column('logs', sa.Column('writing_duration', sa.Integer(), nullable=True))
    
    # Add foreign key constraints to logs
    op.create_foreign_key('fk_logs_user_id', 'logs', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_logs_session_id', 'logs', 'writing_sessions', ['session_id'], ['id'], ondelete='SET NULL')
    op.create_foreign_key('fk_logs_prompt_id', 'logs', 'prompts', ['prompt_id'], ['id'], ondelete='SET NULL')

    # Add user_id to queries table
    op.add_column('queries', sa.Column('user_id', postgresql.UUID(), nullable=True))
    op.create_foreign_key('fk_queries_user_id', 'queries', 'users', ['user_id'], ['id'], ondelete='CASCADE')

    # Data migration: create default user and assign to existing logs and queries
    op.execute("""
        INSERT INTO users (
            id, email, hashed_password, display_name, created_at, updated_at
        ) VALUES (
            '00000000-0000-0000-0000-000000000000',
            'default@example.com',
            'MIGRATE_ME',
            'Default User',
            NOW(),
            NOW()
        )
    """)
    
    # Assign default user to existing logs and queries
    op.execute("""
        UPDATE logs SET user_id = '00000000-0000-0000-0000-000000000000'
        WHERE user_id IS NULL
    """)
    op.execute("""
        UPDATE queries SET user_id = '00000000-0000-0000-0000-000000000000'
        WHERE user_id IS NULL
    """)

    # Make user_id not nullable after data migration
    op.alter_column('logs', 'user_id', nullable=False)
    op.alter_column('queries', 'user_id', nullable=False)

def downgrade():
    # Remove foreign key constraints first
    op.drop_constraint('fk_logs_user_id', 'logs', type_='foreignkey')
    op.drop_constraint('fk_logs_session_id', 'logs', type_='foreignkey')
    op.drop_constraint('fk_logs_prompt_id', 'logs', type_='foreignkey')
    op.drop_constraint('fk_queries_user_id', 'queries', type_='foreignkey')

    # Drop new columns from existing tables
    op.drop_column('queries', 'user_id')
    op.drop_column('logs', 'user_id')
    op.drop_column('logs', 'session_id')
    op.drop_column('logs', 'prompt_id')
    op.drop_column('logs', 'mood_score')
    op.drop_column('logs', 'completion_status')
    op.drop_column('logs', 'target_word_count')
    op.drop_column('logs', 'writing_duration')

    # Drop new tables in reverse order of creation
    op.drop_table('entry_revisions')
    op.drop_table('linguistic_metrics')
    op.drop_table('log_theme')
    op.drop_table('user_insights')
    op.drop_table('prompts')
    op.drop_table('themes')
    op.drop_table('writing_sessions')
    op.drop_index('ix_users_email', 'users')
    op.drop_table('users') 