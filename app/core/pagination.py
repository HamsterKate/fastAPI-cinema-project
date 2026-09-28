from collections.abc import Mapping
from urllib.parse import urlencode


def build_pagination_links(
    path: str,
    page: int,
    per_page: int,
    total_items: int,
    query_params: Mapping[str, str] | None = None,
) -> tuple[str | None, str | None, int]:
    total_pages = (total_items + per_page - 1) // per_page

    def page_link(target_page: int) -> str:
        params: dict[str, int | str] = {
            "page": target_page,
            "per_page": per_page,
        }
        params.update(query_params or {})
        return f"{path}?{urlencode(params)}"

    prev_page = page_link(page - 1) if page > 1 else None
    next_page = page_link(page + 1) if page < total_pages else None
    return prev_page, next_page, total_pages
