"""seed default user groups

Revision ID: 6403751b866e
Revises: 14b344819461
Create Date: 2026-09-22 18:36:00.975452

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6403751b866e'
down_revision: Union[str, Sequence[str], None] = '14b344819461'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO user_groups (id, name)
            VALUES
                (gen_random_uuid(), 'user'),
                (gen_random_uuid(), 'moderator'),
                (gen_random_uuid(), 'admin')
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM user_groups
            WHERE name IN ('user', 'moderator', 'admin')
            """
        )
    )
