"""merge user analytics and previous heads

Revision ID: 35b68fd1ada1
Revises: add_user_and_analytics, f1c6a2b5561e
Create Date: 2025-08-04 14:33:32.805869

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '35b68fd1ada1'
down_revision = ('add_user_and_analytics', 'f1c6a2b5561e')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass 