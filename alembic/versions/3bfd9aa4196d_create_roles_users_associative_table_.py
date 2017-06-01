"""Create roles_users associative table for User/Role tables

Revision ID: 3bfd9aa4196d
Revises: 35fe207b0590
Create Date: 2017-06-01 15:47:42.453812

"""

# revision identifiers, used by Alembic.
revision = '3bfd9aa4196d'
down_revision = '35fe207b0590'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'roles_users',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column('role_id', sa.Integer, sa.ForeignKey("roles.id", ondelete="CASCADE"))
    )

def downgrade():
    op.drop_table('roles_users')
