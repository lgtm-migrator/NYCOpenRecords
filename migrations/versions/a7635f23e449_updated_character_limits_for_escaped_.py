"""Updated Character Limits for Escaped Values in Requests and Users Tables

Revision ID: a7635f23e449
Revises: a9d6b5037034
Create Date: 2022-01-04 21:18:31.060303

"""

# revision identifiers, used by Alembic.
revision = 'a7635f23e449'
down_revision = 'a9d6b5037034'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('requests', 'description',
               existing_type=sa.VARCHAR(length=5000),
               type_=sa.String(length=10240),
               existing_nullable=True)
    op.alter_column('requests', 'title',
               existing_type=sa.VARCHAR(length=90),
               type_=sa.String(length=256),
               existing_nullable=True)
    op.alter_column('users', 'first_name',
               existing_type=sa.VARCHAR(length=32),
               type_=sa.String(length=128),
               existing_nullable=False)
    op.alter_column('users', 'last_name',
               existing_type=sa.VARCHAR(length=64),
               type_=sa.String(length=128),
               existing_nullable=False)
    op.alter_column('users', 'organization',
               existing_type=sa.VARCHAR(length=128),
               type_=sa.String(length=256),
               existing_nullable=True)
    op.alter_column('users', 'title',
               existing_type=sa.VARCHAR(length=64),
               type_=sa.String(length=256),
               existing_nullable=True)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('users', 'title',
               existing_type=sa.String(length=256),
               type_=sa.VARCHAR(length=64),
               existing_nullable=True)
    op.alter_column('users', 'organization',
               existing_type=sa.String(length=256),
               type_=sa.VARCHAR(length=128),
               existing_nullable=True)
    op.alter_column('users', 'last_name',
               existing_type=sa.String(length=128),
               type_=sa.VARCHAR(length=64),
               existing_nullable=False)
    op.alter_column('users', 'first_name',
               existing_type=sa.String(length=128),
               type_=sa.VARCHAR(length=32),
               existing_nullable=False)
    op.alter_column('requests', 'title',
               existing_type=sa.String(length=256),
               type_=sa.VARCHAR(length=90),
               existing_nullable=True)
    op.alter_column('requests', 'description',
               existing_type=sa.String(length=10240),
               type_=sa.VARCHAR(length=5000),
               existing_nullable=True)
    # ### end Alembic commands ###