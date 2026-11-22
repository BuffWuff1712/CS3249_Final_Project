import pytest
import json
from pathlib import Path
from app.runtime.shopify_catalog import product_title, normalize


@pytest.mark.parametrize('variant,expected', [
    ('Running Shoe', 'Running Shoe'),
    (' running   SHOE ', 'Running Shoe'),
    (None, 'Running Shoe'),
    ('', 'Running Shoe'),
    ('Default Title', 'Running Shoe'),
    ('US 7 / Black', 'Running Shoe · US 7 / Black'),
    ('Running Shoe · US 7', 'Running Shoe · US 7'),
    ('Running Shoe - Blue', 'Running Shoe · Blue'),
    ('Running Shoe Pro', 'Running Shoe · Running Shoe Pro'),
])
def test_variant_title(variant, expected):
    assert product_title('Running Shoe', variant) == expected


def test_normalized_record_does_not_repeat_title():
    row = json.loads((Path(__file__).parent / 'fixtures/shopify_live_shape.json').read_text(encoding='utf-8'))
    original = json.dumps(row, sort_keys=True)
    products = normalize(row)
    assert products
    assert products[0][0].name == row['title']
    assert json.dumps(row, sort_keys=True) == original
