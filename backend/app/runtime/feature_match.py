"""Tolerant feature matching for live listings.

Shoppers and retailers describe the same feature in different words ("blocks background noise"
vs "active noise cancellation"), so a literal substring test rejects good matches. A feature
counts as met when the listing shows the same concept, or most of the feature's own words.
Catalogue products keep exact matching against their curated attribute vocabulary.
"""
import re

# Each concept: words in the shopper's feature that name it, and listing patterns that show it.
CONCEPTS = [
    (("noise", "quiet", "anc", "silen", "isolat"),
     (r"\bnoise[- ]?(cancel|reduc|isolat|block)", r"\banc\b", r"\benc\b", r"\bisolat", r"\bquiet")),
    (("comfort", "cushion", "soft", "ergonom", "padd"),
     (r"\bcomfort", r"\bcushion", r"\bpadd", r"\bsoft", r"\bergonom", r"memory[- ]foam", r"\bbreathab")),
    (("lightweight", "portab", "compact", "carry", "small", "mini"),
     (r"\blight[- ]?weight", r"\bportab", r"\bcompact", r"\bmini\b", r"\bpocket[- ]?size", r"\bcarry",
      r"\bstrap", r"\bfoldab", r"\d+(\.\d+)?\s?(g|kg|grams?|oz)\b")),
    (("durab", "sturdy", "rugged", "tough", "robust", "heavy-duty"),
     (r"\bdurab", r"\bsturdy", r"\brugged", r"\btough", r"\brobust", r"\breinforc", r"\bripstop",
      r"heavy[- ]duty", r"\babrasion", r"tear[- ]resist", r"\bshock[- ]?proof")),
    (("waterproof", "water", "rain", "splash"),
     (r"\bwater[- ]?(proof|resist|repell)", r"\bip[x\d]\d", r"\bsplash", r"\brain")),
    (("battery", "playtime", "charge"),
     (r"\bbattery", r"\bplay[- ]?time", r"\d+\s?(-\s?)?(hours?|hrs?|h)\b", r"\bmah\b")),
    (("bass", "loud", "volume", "sound", "audio", "output", "perform", "power"),
     (r"\bbass", r"\bloud", r"\d+\s?w\b", r"\bwatts?\b", r"\bstereo", r"\bsound", r"\bdb\b", r"\bdrivers?\b")),
    (("practical", "functional", "versatil", "organi", "storage", "pocket", "compartment"),
     (r"\bpockets?\b", r"\bcompartment", r"\borgani[sz]", r"\bversatil", r"multi[- ]?function", r"\bsleeve", r"\bstorage")),
]

STOP = {"a", "an", "the", "and", "or", "with", "for", "of", "to", "in", "on", "at", "by", "from", "out",
        "good", "great", "nice", "very", "really", "high", "long", "big", "best", "decent", "quality",
        "must", "have", "has", "be", "is", "that", "it", "easy", "easily", "well", "lot", "lots", "strong",
        "enough", "life", "level", "feature", "features"}

SUFFIXES = ("ability", "ation", "ness", "able", "ible", "ing", "ers", "ed", "er", "ly", "es", "s")


def stem(word):
    for suffix in SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


def words(text):
    return re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", text.casefold())


def listing_text(product):
    # Provider-inferred features and selling points summarise the listing; they never confirm a feature.
    parts = [product.name, product.description, product.observed_type, product.type_evidence,
             *product.attributes, *(f"{k} {v}" for k, v in product.specifications.items())]
    return " ".join(x for x in parts if x).casefold()


def met(feature, text):
    """True when the listing text shows this feature's concept or more than half of its own words."""
    feature = feature.casefold().strip()
    if not feature:
        return True
    if feature in text:
        return True
    tokens = [w for w in words(feature) if w not in STOP]
    for triggers, patterns in CONCEPTS:
        # Prefix only: "pickpockets" must not trigger the pockets/storage concept.
        if any(t.startswith(trigger) for t in tokens for trigger in triggers):
            if any(re.search(p, text) for p in patterns):
                return True
    stems = [stem(w) for w in tokens]
    if not stems:
        return False
    listing = words(text)
    found = sum(any(w.startswith(s) for w in listing) for s in stems)
    # A strict majority: one shared word of two ("heating" in "induction heating") is not a match.
    return found * 2 > len(stems)
