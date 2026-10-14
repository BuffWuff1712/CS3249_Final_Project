from app.catalogue import search_catalogue
from app.intent import ShoppingIntent


def test_headphones():
    intent = ShoppingIntent(category='Headphones', maximum_price=100, currency='SGD')

    search_result = search_catalogue(intent)

    assert sorted(product.id for product in search_result) == ['p1', 'p4']

def test_no_matching_search():
    intent = ShoppingIntent(category='Headphones', maximum_price=50, currency='SGD')

    search_result = search_catalogue(intent)

    assert search_result == []

def test_earbuds():
    intent = ShoppingIntent(category='Earbuds', maximum_price=100, currency='SGD')

    search_result = search_catalogue(intent)

    assert [product.id for product in search_result] == ['p3']


def test_no_price_limit():
    intent = ShoppingIntent(category='Headphones', maximum_price=None, currency='SGD')

    search_result = search_catalogue(intent)

    assert sorted(product.id for product in search_result) == ['p1', 'p2', 'p4']


def test_different_currency():
    intent = ShoppingIntent(category='Headphones', maximum_price=100, currency='USD')

    search_result = search_catalogue(intent)

    assert search_result == []
