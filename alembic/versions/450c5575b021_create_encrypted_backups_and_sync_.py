"""create_encrypted_backups_and_sync_conflicts

Revision ID: 450c5575b021
Revises: 22856ccef338
Create Date: 2025-11-09 20:15:08.810811

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = '450c5575b021'
down_revision = '22856ccef338'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'encrypted_backups',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('encrypted_content', sa.LargeBinary(), nullable=False),
        sa.Column('content_iv', sa.String(), nullable=False),
        sa.Column('content_tag', sa.String(), nullable=True),
        sa.Column('encrypted_embedding', sa.LargeBinary(), nullable=True),
        sa.Column('embedding_iv', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('device_id', sa.String(), nullable=False),
    )

    op.create_index(
        'ix_encrypted_backups_user_updated',
        'encrypted_backups',
        ['user_id', 'updated_at']
    )
    op.create_index(
        'ix_encrypted_backups_device',
        'encrypted_backups',
        ['device_id']
    )

    op.create_table(
        'sync_conflicts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('log_id', sa.String(), nullable=False),
        sa.Column('local_encrypted_content', sa.LargeBinary(), nullable=False),
        sa.Column('local_iv', sa.String(), nullable=False),
        sa.Column('local_updated_at', sa.DateTime(), nullable=False),
        sa.Column('local_device_id', sa.String(), nullable=False),
        sa.Column('remote_encrypted_content', sa.LargeBinary(), nullable=False),
        sa.Column('remote_iv', sa.String(), nullable=False),
        sa.Column('remote_updated_at', sa.DateTime(), nullable=False),
        sa.Column('remote_device_id', sa.String(), nullable=False),
        sa.Column('detected_at', sa.DateTime(), nullable=False),
        sa.Column('resolved', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
    )

    op.create_index(
        'ix_sync_conflicts_user_unresolved',
        'sync_conflicts',
        ['user_id', 'resolved']
    )
    op.create_index(
        'ix_sync_conflicts_log_id',
        'sync_conflicts',
        ['log_id']
    )


def downgrade() -> None:
    op.drop_index('ix_sync_conflicts_log_id', table_name='sync_conflicts')
    op.drop_index('ix_sync_conflicts_user_unresolved', table_name='sync_conflicts')
    op.drop_table('sync_conflicts')

    op.drop_index('ix_encrypted_backups_device', table_name='encrypted_backups')
    op.drop_index('ix_encrypted_backups_user_updated', table_name='encrypted_backups')
    op.drop_table('encrypted_backups') 