import gzip
import json
from scripts.sample_amazon import attach_reviews, iter_items, main, sample


def write_jsonl(path, rows, gz=False):
    text = "\n".join(json.dumps(r) for r in rows) + "\n"
    if gz:
        with gzip.open(path, "wt", encoding="utf-8") as f:
            f.write(text)
    else:
        path.write_text(text, encoding="utf-8")
    return path


META = [
    {"parent_asin": "A1", "title": "Wireless Noise Cancelling Headphones", "price": 99.0},
    {"parent_asin": "A2", "title": "Noise Cancelling Headphones Pro", "price": None},
    {"parent_asin": "A3", "title": "Wired Headphones", "price": 20.0},
    {"parent_asin": "A4", "title": "Earbuds with noise reduction", "price": 30.0},
]


def test_filter_requires_all_keywords_and_price(tmp_path):
    meta = write_jsonl(tmp_path / "meta.jsonl", META)
    assert [r["parent_asin"] for r in iter_items(meta, ["noise", "headphones"])] == ["A1"]


def test_filter_reads_gzip(tmp_path):
    meta = write_jsonl(tmp_path / "meta.jsonl.gz", META, gz=True)
    assert [r["parent_asin"] for r in iter_items(meta, ["headphones"])] == ["A1", "A3"]


def test_sample_is_deterministic():
    items = [{"parent_asin": str(i)} for i in range(50)]
    assert sample(items, 5, 3249) == sample(items, 5, 3249)
    assert len(sample(items, 99, 1)) == 50


def test_reviews_drop_user_fields(tmp_path):
    reviews = write_jsonl(
        tmp_path / "reviews.jsonl",
        [
            {"parent_asin": "A1", "rating": 5.0, "title": "Great", "text": "Love it", "user_id": "U9", "timestamp": 1},
            {"parent_asin": "A1", "rating": 3.0, "title": "Ok", "text": "Fine", "user_id": "U8"},
            {"parent_asin": "B7", "rating": 1.0, "title": "Bad", "text": "No", "user_id": "U7"},
        ],
    )
    out = attach_reviews([{"parent_asin": "A1"}], reviews, 1)
    assert out[0]["reviews"] == [{"rating": 5, "title": "Great", "text": "Love it"}]


def test_cli_writes_selected_fields(tmp_path):
    meta = write_jsonl(
        tmp_path / "meta.jsonl",
        [dict(META[0], store="RealBrand", features=["f"], description=["d"], details={}, average_rating=4.5, rating_number=10, images=["x"])],
    )
    reviews = write_jsonl(tmp_path / "reviews.jsonl", [])
    out = tmp_path / "out.json"
    main(["--meta", str(meta), "--reviews", str(reviews), "--keywords", "headphones", "--n", "5", "--seed", "1", "--out", str(out)])
    [row] = json.loads(out.read_text())
    assert set(row) == {
        "parent_asin", "title", "store", "price", "average_rating",
        "rating_number", "features", "description", "details", "reviews",
    }
