from pydantic import BaseModel
from typing import Generic, TypeVar

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    data: T | None = None
    message: str = "success"


# NOTE: PaginatedResponse is defined for future use in list endpoints.
class PaginatedResponse(BaseModel, Generic[T]):
    code: int = 0
    data: dict | None = None
    message: str = "success"
