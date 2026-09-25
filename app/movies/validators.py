import re


def normalize_genre_name(value: str) -> str:
    name = " ".join(value.split())
    name = re.sub(r"\s*-\s*", "-", name)

    parts = re.split(r"([ -])", name)
    return "".join(
        part if part in {" ", "-"} else part.capitalize()
        for part in parts
    )


def normalize_country_code(value: str) -> str:
    return value.strip().upper()


def is_valid_country_code(value: str) -> bool:
    return len(value) in {2, 3} and value.isascii() and value.isalpha()
