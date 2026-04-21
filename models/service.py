"""Bookable service offered by a business."""

from .base import BaseModel

class Service(BaseModel):
    # A single bookable service on a business menu.

    def __init__(
        self,
        id: str,
        business_id: str,
        name: str,
        duration_min: int = 30,
        price: float = 0.0,
        description: str = '',
    ):
        self.id = id
        self.business_id = business_id
        self.name = name
        self.duration_min = int(duration_min or 30)
        self.price = float(price or 0)
        self.description = description or ''

    def validate(self) -> None:
        if not self.name:
            raise ValueError('Service name is required.')
        if self.duration_min < 5 or self.duration_min > 480:
            raise ValueError('Duration must be between 5 and 480 minutes.')
        if self.price < 0:
            raise ValueError('Price cannot be negative.')

    def is_free(self) -> bool:
        return self.price <= 0

    def price_display(self) -> str:
        return 'Free' if self.is_free() else f'${self.price:.0f}'
