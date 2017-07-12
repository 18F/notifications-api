"""empty message

Revision ID: 0106_change_logo_not_nullable
Revises: 0105_opg_letter_org
Create Date: 2017-07-06 10:14:35.188404

"""

# revision identifiers, used by Alembic.
revision = '0106_change_logo_not_nullable'
down_revision = '0105_opg_letter_org'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.alter_column('organisation', 'logo',
               existing_type=sa.VARCHAR(length=255),
               nullable=False)


def downgrade():
    op.alter_column('organisation', 'logo',
               existing_type=sa.VARCHAR(length=255),
               nullable=True)
