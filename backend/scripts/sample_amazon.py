"""Sample Amazon Reviews 2023 candidates for manual curation (offline helper).

The output is a scratch file for a human to curate; it is never study data
itself. Keep raw dumps and outputs under data/raw/ (git-ignored).
"""

import argparse
import gzip
import json
import random
from pathlib import Path

FIELDS = [
    "parent_asin",
    "title",
    "store",
    "price",
    "average_rating",
    "rating_number",
    "features",
    "description",
    "details",
]


def rows(path):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def iter_items(meta_path, keywords):
    terms = [k.casefold() for k in keywords]
    for row in rows(meta_path):
        title = (row.get("title") or "").casefold()
        if row.get("price") is not None and all(t in title for t in terms):
            yield row


def sample(items, n, seed):
    items = list(items)
    return random.Random(seed).sample(items, min(n, len(items)))


def attach_reviews(items, reviews_path, k):
    wanted = {i["parent_asin"]: [] for i in items}
    for row in rows(reviews_path):
        bucket = wanted.get(row.get("parent_asin"))
        if bucket is not None and len(bucket) < k:
            bucket.append(
                {"rating": int(row["rating"]), "title": row["title"], "text": row["text"]}
            )
    return [dict(i, reviews=wanted[i["parent_asin"]]) for i in items]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--meta", type=Path, required=True)
    parser.add_argument("--reviews", type=Path, required=True)
    parser.add_argument("--keywords", required=True, help="comma-separated, all must match the title")
    parser.add_argument("--n", type=int, default=30)
    parser.add_argument("--seed", type=int, default=3249)
    parser.add_argument("--k", type=int, default=8, help="reviews kept per item")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    picked = sample(iter_items(args.meta, keywords), args.n, args.seed)
    picked = [{f: i.get(f) for f in FIELDS} for i in picked]
    out = attach_reviews(picked, args.reviews, args.k)
    args.out.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{len(out)} candidates -> {args.out}")


if __name__ == "__main__":
    main()
