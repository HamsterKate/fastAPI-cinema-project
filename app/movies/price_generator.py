import argparse
import csv
from datetime import date
from decimal import Decimal
from pathlib import Path


BASE_PRICE = Decimal("4.99")
MAX_PRICE = Decimal("9.99")

RECENT_RELEASE_YEARS = 2
MODERN_RELEASE_YEARS = 5

HIGH_REVENUE = Decimal("100000000")
VERY_HIGH_REVENUE = Decimal("500000000")

HIGH_SCORE = Decimal("8.0")


def calculate_price(
    release_date: date,
    score: Decimal,
    revenue: Decimal,
) -> Decimal:
    price = BASE_PRICE
    years_old = max(date.today().year - release_date.year, 0)

    if years_old <= RECENT_RELEASE_YEARS:
        price += Decimal("2.00")
    elif years_old <= MODERN_RELEASE_YEARS:
        price += Decimal("1.00")

    if revenue >= VERY_HIGH_REVENUE:
        price += Decimal("2.00")
    elif revenue >= HIGH_REVENUE:
        price += Decimal("1.00")

    if score >= HIGH_SCORE:
        price += Decimal("1.00")

    return min(price, MAX_PRICE)


def add_prices(path: Path) -> int:
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        fieldnames = list(reader.fieldnames or [])

        if "price" not in fieldnames:
            fieldnames.append("price")

        rows = list(reader)

    for row in rows:
        price = calculate_price(
            release_date=date.fromisoformat(row["date_x"]),
            score=Decimal(row["score"]),
            revenue=Decimal(row["revenue"] or "0"),
        )
        row["price"] = f"{price:.2f}"

    temporary_path = path.with_suffix(".tmp")

    with temporary_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    temporary_path.replace(path)
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()

    total = add_prices(args.path)
    print(f"Added prices to {total} movies.")


if __name__ == "__main__":
    main()
