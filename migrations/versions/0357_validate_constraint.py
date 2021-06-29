"""

Revision ID: 0357_validate_constraint
Revises: 0356_add_webautn_auth_type
Create Date: 2021-05-13 14:15:25.259991

"""
from alembic import op

revision = '0357_validate_constraint'
down_revision = '0356_add_webautn_auth_type'


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.execute('ALTER TABLE users VALIDATE CONSTRAINT "ck_user_has_mobile_or_other_auth"')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###