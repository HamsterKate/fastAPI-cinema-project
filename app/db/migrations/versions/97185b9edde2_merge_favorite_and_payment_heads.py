"""merge favorite and payment heads

Revision ID: 97185b9edde2
Revises: d48412ae475a, dc0f59b0bef5
Create Date: 2026-09-27 17:20:41.203509

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '97185b9edde2'
down_revision: Union[str, Sequence[str], None] = ('d48412ae475a', 'dc0f59b0bef5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
