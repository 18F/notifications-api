"""

Revision ID: 0313_email_access_validated_at
Revises: 0312_populate_returned_letters
Create Date: 2020-01-28 18:03:22.237386

"""
from alembic import op
import sqlalchemy as sa


revision = '0313_email_access_validated_at'
down_revision = '0312_populate_returned_letters'


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('email_access_validated_at', sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'email_access_validated_at')
    # ### end Alembic commands ###
