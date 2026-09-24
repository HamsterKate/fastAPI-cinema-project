"""add movie soft delete

Revision ID: 2d531c0004d3
Revises: ee9e20d05ec1
Create Date: 2026-09-24 19:20:45.251699

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2d531c0004d3'
down_revision: Union[str, Sequence[str], None] = 'ee9e20d05ec1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'movies',
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.drop_index('uq_movies_name_lower_date', table_name='movies')
    op.create_index(
        'uq_movies_name_lower_date',
        'movies',
        [sa.literal_column('lower(name)'), 'date'],
        unique=True,
        postgresql_where=sa.text('deleted_at IS NULL'),
    )


def downgrade() -> None:
    op.drop_index('uq_movies_name_lower_date', table_name='movies')
    op.create_index(
        'uq_movies_name_lower_date',
        'movies',
        [sa.literal_column('lower(name)'), 'date'],
        unique=True,
    )
    op.drop_column('movies', 'deleted_at')
