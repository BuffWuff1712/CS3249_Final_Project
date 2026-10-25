"""Build a Browser Use replay fixture from the study dataset (offline helper).

Only fields a shopper could read on a product, seller or policy page are
converted. Ground truth under data/research/ is never read, so replayed
listings cannot leak labels into the runtime. Product and merchant reviews,
specifications and the fixture's boolean risk flags are left out: reviews are
outside the risk review's scope, and flags are not page text.
"""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "data/products/catalogue.json"
MERCHANTS = ROOT / "data/merchants/merchants.json"
OUTPUT = ROOT / "data/replay/study_listings.json"


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def seller(m):
    out = {"name": m["name"], "page_url": m["website"], "about": m["description"]}
    contact = m.get("contact", "").strip()
    if contact:
        out["email" if "@" in contact else "phone"] = contact
    if m.get("verified_business"):
        out["badges"] = ["Verified business"]
    if m.get("review_count"):
        count = f"{m['review_count']:,} reviews"
        rating = m.get("review_rating")
        out["rating"] = f"{rating}/5 ({count})" if rating is not None else count
    return out


def evidence(m):
    # Text is copied as-is; deciding which risk it signals is the review agent's job.
    out = {
        "seller": seller(m),
        "return_policy": m.get("return_policy", ""),
        "payment_methods": m.get("payment_methods", []),
    }
    if m.get("checkout_note"):
        out["notices"] = [m["checkout_note"]]
    return out


def listing(p, m):
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
            "evidence": evidence(m),
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
