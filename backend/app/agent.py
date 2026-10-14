"""Replace MockShoppingAgent with a LangGraph adapter, retaining this protocol."""
from typing import Protocol
from .models import Product

CATALOGUE = [
    Product(id='p1', name='Everyday Quiet Headphones', price=89, merchant='Everyday', category='Headphones', attributes=['30-hour battery', 'Noise isolation', 'Lightweight']),
    Product(id='p2', name='Northstar Studio Pro', price=189, merchant='Northstar', category='Headphones', attributes=['Active noise cancellation', '40-hour battery', 'Premium comfort']),
    Product(id='p3', name='Everyday Air Buds', price=69, merchant='Everyday', category='Earbuds', attributes=['Compact alternative', '24-hour battery', 'In-ear fit'], substitute=True),
    Product(id='p4', name='Market Lane Sound One', price=79, merchant='Market Lane', category='Headphones', attributes=['Wireless audio', '20-hour battery', 'Foldable']),
]


class ShoppingAgent(Protocol):
    def propose(self, scenario: str) -> Product: ...


class MockShoppingAgent:
    def propose(self, scenario: str) -> Product:
        return CATALOGUE[{'normal': 0, 'budget': 1, 'substitution': 2, 'merchant': 3}[scenario]].model_copy(deep=True)
