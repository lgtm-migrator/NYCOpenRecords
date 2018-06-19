"""Increase Length of File TItle to 250 Chars

Revision ID: 60116f094400
Revises: dc926c74551d
Create Date: 2018-06-12 19:38:16.559392

"""

# revision identifiers, used by Alembic.
revision = '60116f094400'
down_revision = 'dc926c74551d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('files', 'title',
               existing_type=sa.VARCHAR(length=140),
               type_=sa.String(length=250),
               existing_nullable=True)
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('files', 'title',
               existing_type=sa.String(length=250),
               type_=sa.VARCHAR(length=140),
               existing_nullable=True)
    ### end Alembic commands ###
