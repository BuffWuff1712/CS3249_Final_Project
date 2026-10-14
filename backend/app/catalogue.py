from .models import Product
from .intent import ShoppingIntent
from .agent import CATALOGUE

def search_catalogue(intent: ShoppingIntent) -> list[Product]:
    search_result = []

    for product in CATALOGUE:
        if (product.category == intent.category 
            and product.currency == intent.currency):

            if intent.maximum_price is None or product.price <= intent.maximum_price:
                search_result.append(product)

    return search_result


