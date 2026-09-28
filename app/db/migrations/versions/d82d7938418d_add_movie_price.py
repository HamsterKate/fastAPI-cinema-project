"""add movie price

Revision ID: d82d7938418d
Revises: 191967e25547
Create Date: 2026-09-27 11:04:17.551122

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d82d7938418d"
down_revision: Union[str, Sequence[str], None] = "191967e25547"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "movies",
        sa.Column(
            "price",
            sa.Numeric(precision=6, scale=2),
            nullable=True,
        ),
    )

    op.execute("""
        UPDATE movies
        SET price = LEAST(
            9.99::numeric,
            4.99::numeric
            + CASE
                WHEN EXTRACT(YEAR FROM CURRENT_DATE)
                    - EXTRACT(YEAR FROM movies.date) <= 2
                    THEN 2.00::numeric
                WHEN EXTRACT(YEAR FROM CURRENT_DATE)
                    - EXTRACT(YEAR FROM movies.date) <= 5
                    THEN 1.00::numeric
                ELSE 0.00::numeric
            END
            + CASE
                WHEN movies.revenue >= 500000000
                    THEN 2.00::numeric
                WHEN movies.revenue >= 100000000
                    THEN 1.00::numeric
                ELSE 0.00::numeric
            END
            + CASE
                WHEN movies.score >= 8
                    THEN 1.00::numeric
                ELSE 0.00::numeric
            END
        )
        """)

    op.alter_column(
        "movies",
        "price",
        nullable=False,
    )
    op.create_check_constraint(
        "price_non_negative",
        "movies",
        "price >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "price_non_negative",
        "movies",
        type_="check",
    )
    op.drop_column("movies", "price")
