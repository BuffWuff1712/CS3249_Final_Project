"""Map local records to the evidence a shopper could read. Never import researcher data here.

One mapping serves both the replay fixture and AI risk review of local products, so the
two always see identical evidence. Boolean risk flags are never mapped: they are not page
text. Absent details become explicit text because a local record knows they are missing.
"""

from .schemas import LocalEvidence, Product, Merchant, SellerEvidence

LABELS = {
    "government_id": "government ID",
    "date_of_birth": "date of birth",
    "bank_password": "bank password",
    "card_number": "card number",
}


def request_label(item):
    return LABELS.get(item) or item.removeprefix("fictional_").replace("_", " ")


def review_line(review):
    return f"★{review.rating} {review.title} — {review.text}"


def seller(merchant):
    out = SellerEvidence(
        name=merchant.name,
        page_url=merchant.website,
        about=merchant.description,
        badges=["Verified business" if merchant.verified_business else "Unverified seller"],
    )
    contact = merchant.contact.strip()
    if contact:
        if "@" in contact:
            out.email = contact
        else:
            out.phone = contact
    if merchant.review_count:
        count = f"{merchant.review_count:,} reviews"
        out.rating = f"{merchant.review_rating}/5 ({count})" if merchant.review_rating is not None else count
    return out


def local_evidence(product: Product, merchant: Merchant) -> LocalEvidence:
    notices = []
    if merchant.checkout_note:
        notices.append(merchant.checkout_note)
    if not merchant.contact.strip():
        notices.append("No seller contact details listed")
    requests = merchant.requested_information
    return LocalEvidence(
        seller=seller(merchant),
        return_policy=merchant.return_policy,
        payment_methods=merchant.payment_methods,
        personal_data_requests=(
            ["Checkout asks for: " + ", ".join(request_label(i) for i in requests)] if requests else []
        ),
        notices=notices,
        product_reviews=[review_line(r) for r in product.reviews],
        seller_reviews=[review_line(r) for r in merchant.merchant_reviews],
        specifications=[f"{k}: {v}" for k, v in product.specifications.items()],
        product_rating=(
            f"{product.rating}/5 ({product.rating_count:,} ratings)" if product.rating is not None else ""
        ),
    )


def review_view(product: Product, merchant: Merchant) -> Product:
    """The product as the risk agent sees it: a copy carrying local evidence."""
    return product.model_copy(update={"web_evidence": local_evidence(product, merchant)})
