from pydantic import BaseModel
from typing import TypeVar, Generic

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Wrapper for all list endpoints providing pagination metadata."""
    items: list[T]
    total: int
    limit: int
    offset: int
    has_more: bool
