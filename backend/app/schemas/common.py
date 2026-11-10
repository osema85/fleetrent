from decimal import Decimal
from typing import Annotated, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

T = TypeVar("T")


class InputModel(BaseModel):
    """Base for request bodies: unknown fields are rejected (mass-assignment protection)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class OutputModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int


Name = Annotated[str, StringConstraints(min_length=1, max_length=100)]
ShortText = Annotated[str, StringConstraints(max_length=255)]
LongText = Annotated[str, StringConstraints(max_length=2000)]
Phone = Annotated[str, StringConstraints(pattern=r"^\+?[0-9 ()\-]{6,30}$")]
Money = Annotated[Decimal, Field(ge=0, le=1_000_000, max_digits=10, decimal_places=2)]
PositiveMoney = Annotated[Decimal, Field(gt=0, le=1_000_000, max_digits=10, decimal_places=2)]
Percent = Annotated[int, Field(ge=0, le=100)]
Mileage = Annotated[int, Field(ge=0, le=5_000_000)]
