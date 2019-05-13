"""Add appealable option to reasons

Revision ID: aeb1852855b4
Revises: 838a6ad16cf4
Create Date: 2019-02-27 19:21:58.871057

"""

# revision identifiers, used by Alembic.
revision = "aeb1852855b4"
down_revision = "838a6ad16cf4"

import sqlalchemy as sa
from alembic import op
from sqlalchemy import engine_from_config
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import reflection


def _table_has_column(table, column):
    config = op.get_context().config
    engine = engine_from_config(
        config.get_section(config.config_ini_section), prefix='sqlalchemy.')
    insp = reflection.Inspector.from_engine(engine)
    has_column = False
    for col in insp.get_columns(table):
        if column not in col['name']:
            continue
        has_column = True
    return has_column

def _table_exists(table):
    config = op.get_context().config
    engine = engine_from_config(
        config.get_section(config.config_ini_section), prefix='sqlalchemy.')
    insp = reflection.Inspector.from_engine(engine)
    return table in insp.get_table_names()



def upgrade():
    if _table_exists('migration'):
        op.drop_table('migration')
    if _table_exists('user_requests_0806_bkup_20181212'):
        op.drop_table('user_requests_0806_bkup_20181212')
    if _table_exists('note_import'):
        op.drop_table('note_import')
    op.create_foreign_key(None, 'agency_users', 'users', ['user_guid'], ['guid'])
    op.add_column('reasons', sa.Column('has_appeals_language', sa.Boolean(), nullable=True))


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("reasons", "has_appeals_language")
    op.drop_constraint(None, "agency_users", type_="foreignkey")
    op.create_table(
        "note_import",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=True),
        sa.Column(
            "request_id", sa.VARCHAR(length=19), autoincrement=False, nullable=True
        ),
        sa.Column(
            "date_modified", postgresql.TIMESTAMP(), autoincrement=False, nullable=True
        ),
        sa.Column(
            "user_guid", sa.VARCHAR(length=64), autoincrement=False, nullable=True
        ),
        sa.Column(
            "type",
            sa.VARCHAR(length=64),
            server_default=sa.text("'notes'::character varying"),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "content", sa.VARCHAR(length=5000), autoincrement=False, nullable=True
        ),
    )
    op.create_table(
        "user_requests_0806_bkup_20181212",
        sa.Column(
            "user_guid", sa.VARCHAR(length=64), autoincrement=False, nullable=True
        ),
        sa.Column(
            "auth_user_type",
            postgresql.ENUM(
                "Saml2In:NYC Employees",
                "LDAP:NYC Employees",
                "FacebookSSO",
                "MSLiveSSO",
                "YahooSSO",
                "LinkedInSSO",
                "GoogleSSO",
                "EDIRSSO",
                "AnonymousUser",
                name="auth_user_type",
            ),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "request_id", sa.VARCHAR(length=19), autoincrement=False, nullable=True
        ),
        sa.Column(
            "request_user_type",
            postgresql.ENUM("requester", "agency", name="request_user_type"),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("permissions", sa.BIGINT(), autoincrement=False, nullable=True),
        sa.Column("point_of_contact", sa.BOOLEAN(), autoincrement=False, nullable=True),
    )
    op.create_table(
        "migration",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=True),
        sa.Column(
            "request_id", sa.VARCHAR(length=19), autoincrement=False, nullable=True
        ),
        sa.Column(
            "date_modified", postgresql.TIMESTAMP(), autoincrement=False, nullable=True
        ),
        sa.Column(
            "user_guid", sa.VARCHAR(length=64), autoincrement=False, nullable=True
        ),
        sa.Column("type", sa.VARCHAR(length=64), autoincrement=False, nullable=True),
        sa.Column("dtype", sa.VARCHAR(length=64), autoincrement=False, nullable=True),
        sa.Column("reason", sa.VARCHAR(), autoincrement=False, nullable=True),
        sa.Column("date", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    )
    # ### end Alembic commands ###