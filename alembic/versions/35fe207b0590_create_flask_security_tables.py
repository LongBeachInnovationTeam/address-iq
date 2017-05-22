"""Create Flask-Security tables

Revision ID: 35fe207b0590
Revises: 3f232866635a
Create Date: 2017-05-22 15:30:23.690426

"""

# revision identifiers, used by Alembic.
revision = '35fe207b0590'
down_revision = '3f232866635a'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(80), unique=True),
        sa.Column('description', sa.String(255))
    )
    op.add_column('users', sa.Column('password', sa.String))
    op.add_column('users', sa.Column('active', sa.Boolean, default=False))
    op.add_column('users', sa.Column('confirmed_at', sa.DateTime(timezone=True)))

def downgrade():
    op.drop_table('roles')
    op.drop_column('users', 'password')
    op.drop_column('users', 'active')
    op.drop_column('users', 'confirmed_at')
