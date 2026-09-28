from app.core.pagination import build_pagination_links


def test_build_pagination_links_preserves_filters() -> None:
    prev_page, next_page, total_pages = build_pagination_links(
        path="/api/v2/movies",
        page=2,
        per_page=5,
        total_items=12,
        query_params={
            "country": "UA",
            "genre": "Drama",
        },
    )

    assert prev_page == ("/api/v2/movies?page=1&per_page=5&country=UA&genre=Drama")
    assert next_page == ("/api/v2/movies?page=3&per_page=5&country=UA&genre=Drama")
    assert total_pages == 3


def test_build_pagination_links_for_empty_result() -> None:
    prev_page, next_page, total_pages = build_pagination_links(
        path="/api/v2/movies",
        page=1,
        per_page=10,
        total_items=0,
    )

    assert prev_page is None
    assert next_page is None
    assert total_pages == 0
