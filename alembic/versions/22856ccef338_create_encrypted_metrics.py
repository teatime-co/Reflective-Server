"""create_encrypted_metrics

Revision ID: 22856ccef338
Revises: 0a70c8a28957
Create Date: 2025-11-09 18:59:19.924799

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = '22856ccef338'
down_revision = '0a70c8a28957'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'encrypted_metrics',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('metric_type', sa.String(), nullable=False),
        sa.Column('encrypted_value', sa.LargeBinary(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    op.create_index(
        'ix_encrypted_metrics_user_type_time',
        'encrypted_metrics',
        ['user_id', 'metric_type', 'timestamp']
    )


def downgrade() -> None:
    op.drop_index('ix_encrypted_metrics_user_type_time', table_name='encrypted_metrics')
    op.drop_table('encrypted_metrics') 