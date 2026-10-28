"""Build a Browser Use replay fixture from the study dataset (offline helper).

Evidence comes from app.runtime.local_evidence, the same mapping the AI risk
review uses for local products, so replayed and local listings carry identical
evidence. Ground truth under data/research/ is never read, so replayed
listings cannot leak labels into the runtime. Boolean risk flags are never
converted: they are not page text.
"""

import argparse
import json
from pathlib import Path
from app.runtime.local_evidence import local_evidence
from app.runtime.schemas import Merchant, Product

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "data/products/catalogue.json"
MERCHANTS = ROOT / "data/merchants/merchants.json"
OUTPUT = ROOT / "data/replay/study_listings.json"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def listing(p, m):
    product, merchant = Product.model_validate(p), Merchant.model_validate(m)
    return {
        "category": p["category"],
        "listing": {
            "name": p["name"],
            "url": f"{m['website']}/products/{p['id']}",
            "brand": p["brand"],
            "price": p["price"],
            "currency": p["currency"],
            "attributes": p["attributes"],
            "sizes": p.get("sizes", []),
            "description": p["description"],
            "in_stock": p.get("stock", True),
            "evidence": local_evidence(product, merchant).model_dump(exclude_defaults=True),
        },
    }


def build(prefixes=("study-",), catalogue=CATALOGUE, merchants=MERCHANTS):
    by_id = {m["id"]: m for m in load(merchants)}
    rows = [
        listing(p, by_id[p["merchant_id"]])
        for p in load(catalogue)
        if p["id"].startswith(tuple(prefixes))
    ]
    return {
        "version": 1,
        "source": "Study dataset products and merchants; shopper-visible fields only",
        "listings": rows,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--only",
        default="study-",
        help="Comma-separated product ID prefixes to include (default: study-)",
    )
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    prefixes = tuple(x.strip() for x in args.only.split(",") if x.strip())
    data = build(prefixes)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"Wrote {len(data['listings'])} listings to {args.output}")


if __name__ == "__main__":
    main()
