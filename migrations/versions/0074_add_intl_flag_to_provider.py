"""empty message

Revision ID: 0074_add_intl_flag_to_provider
Revises: 0073_add_international_sms_flag
Create Date: 2017-04-25 09:44:13.194164

"""

# revision identifiers, used by Alembic.
revision = '0074_add_intl_flag_to_provider'
down_revision = '0073_add_international_sms_flag'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('provider_details', sa.Column('supports_international', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('provider_details_history', sa.Column('supports_international', sa.Boolean(), nullable=False, server_default=sa.false()))

    op.execute("UPDATE provider_details SET supports_international=True WHERE identifier='mmg'")
    op.execute("UPDATE provider_details_history SET supports_international=True WHERE identifier='mmg'")


def downgrade():
    op.drop_column('provider_details_history', 'supports_international')
    op.drop_column('provider_details', 'supports_international')
