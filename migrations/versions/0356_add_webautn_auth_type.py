"""

Revision ID: 0356_add_webautn_auth_type
Revises: 0355_add_webauthn_table
Create Date: 2021-05-13 12:42:45.190269

"""
from alembic import op

revision = '0356_add_webautn_auth_type'
down_revision = '0355_add_webauthn_table'


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.execute("INSERT INTO auth_type VALUES ('webauthn_auth')")

    op.drop_constraint('ck_users_mobile_or_email_auth', 'users', type_=None, schema=None)
    op.create_check_constraint(
        'ck_user_has_mobile_or_other_auth',
        'users',
        "auth_type in ('email_auth', 'webauthn_auth') or mobile_number is not null"
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.execute("UPDATE users SET auth_type = 'sms_auth' WHERE auth_type = 'webauthn_auth'")
    op.execute("UPDATE invited_users SET auth_type = 'sms_auth' WHERE auth_type = 'webauthn_auth'")

    op.drop_constraint('ck_user_has_mobile_or_other_auth', 'users', type_=None, schema=None)
    op.create_check_constraint(
        'ck_users_mobile_or_email_auth',
        'users',
        "auth_type = 'email_auth' or mobile_number is not null"
    )

    op.execute("DELETE FROM auth_type WHERE name = 'webauthn_auth'")
    # ### end Alembic commands ###
