"""Pagination iterator over GET/QUERY list endpoints.

The SDK exposes list operations as iterators that lazily walk every page
until the server returns an empty ``next`` cursor. The iterator is built
on QUERY because QUERY supports complex filters in the body and avoids
URL-length limits.
"""
from __future__ import annotations

from typing import Any, Callable, Generic, Iterator, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class PaginatedIterator(Generic[T]):
    """Lazy iterator over a paginated list endpoint.

    The iterator does not eagerly fetch any pages — calling ``iter()`` or
    ``list()`` triggers the first request. ``materialize()`` is a
    convenience that returns a fully-realised list.
    """

    def __init__(
        self,
        fetch_page: Callable[[str | None], dict[str, Any]],
        items_key: str,
        item_cls: type[T],
    ):
        self._fetch_page = fetch_page
        self._items_key = items_key
        self._item_cls = item_cls

    def __iter__(self) -> Iterator[T]:
        cursor: str | None = None
        while True:
            page = self._fetch_page(cursor)
            for raw in page.get(self._items_key, []):
                yield self._item_cls.model_validate(raw)
            cursor = page.get("next") or ""
            if not cursor:
                return

    def materialize(self) -> list[T]:
        return list(self)
