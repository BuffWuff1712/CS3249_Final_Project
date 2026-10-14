from pydantic import BaseModel, Field
from typing import Literal


class ShoppingIntent(BaseModel):
    category: Literal["Headphones", "Earbuds"]
    maximum_price: float | None = Field(default=None, gt=0)
    currency: Literal["SGD", "USD"]