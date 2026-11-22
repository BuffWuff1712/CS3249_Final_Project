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
        "enough", "life", "level", "feature", "features",
        # Generic second halves of hyphenated features ("christmas-themed", "retro-style").
        "theme", "themed", "style", "styled", "inspired", "look", "looking", "type"}

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
             *product.attributes, *(f"{k} {v}" for k, v in product.specifications.items()),
             "sizes " + ", ".join(product.sizes) if product.sizes else ""]
    return " ".join(x for x in parts if x).casefold()


def met(feature, text):
    """True when the listing text shows this feature's concept or most of its own words."""
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
    # Hyphenated words compare by their parts: "christmas-themed" is about "christmas".
    parts = [x for w in tokens for x in w.split("-") if len(x) >= 3 and x not in STOP]
    stems = [stem(w) for w in parts]
    if not stems:
        return False
    listing = words(text)
    found = sum(any(w.startswith(s) for w in listing) for s in stems)
    return found * 2 >= len(stems)


# --- Size, brand and seller rules. Each returns True (matches), False (clearly does not) or None
# (cannot tell from structured fields; free-text needs then go to the model check).

YEARS = {"y", "yr", "yrs", "year", "years", "t", "jaar", "jahre", "j", "ans", "age", "ages", "yo"}
MONTHS = {"m", "mo", "mos", "month", "months", "maand", "maanden", "monate", "mois"}
LETTERS = {"xxs": "xxs", "xs": "xs", "s": "s", "m": "m", "l": "l", "xl": "xl", "xxl": "xxl", "xxxl": "xxxl",
           "2xl": "xxl", "3xl": "xxxl", "extra small": "xs", "small": "s", "medium": "m", "large": "l",
           "extra large": "xl"}
RANGE = re.compile(r"(\d+(?:\.\d+)?)\s*([a-z]*)\s*(?:-|/|to)\s*(\d+(?:\.\d+)?)\s*([a-z]*)|(\d+(?:\.\d+)?)\s*([a-z]*)")


def size_text(text):
    return re.sub(r"\s+", " ", text.casefold().replace("–", "-").replace("—", "-")).strip()


def parse_size(text):
    """('years', lo, hi) for ages (months converted), ('letter', code) for S/M/L, ('number', n) or None."""
    t = size_text(text)
    hint = "years" if re.search(r"\b(age|ages|years?|jaar|jahre|yrs?)\b", t) else "months" if re.search(r"\bmonths?\b", t) else None
    for m in RANGE.finditer(t):
        if m.group(1):
            lo, hi, units = float(m.group(1)), float(m.group(3)), {m.group(2), m.group(4)} - {""}
        else:
            lo = hi = float(m.group(5))
            units = {m.group(6)} - {""}
        if units & YEARS or (not units and hint == "years"):
            return ("years", lo, hi)
        if units & MONTHS or (not units and hint == "months"):
            return ("years", lo / 12, hi / 12)
        if units == {"cm"}:
            continue
        if not units and hint is None and m.group(5):
            return ("number", lo)
    letters = re.sub(r"\(.*?\)", " ", t).strip()
    if letters in LETTERS:
        return ("letter", LETTERS[letters])
    inner = re.findall(r"\(([a-z0-9]+)\)", t)
    if inner and inner[0] in LETTERS:
        return ("letter", LETTERS[inner[0]])
    return None


def size_rule(need, sizes):
    """Does any listed size satisfy the requested one? Age ranges match when they overlap."""
    if not sizes:
        return None
    want = parse_size(need)
    verdicts = []
    for size in sizes:
        if size_text(size) == size_text(need):
            return True
        have = parse_size(size)
        if want is None or have is None or want[0] != have[0]:
            verdicts.append(None)
        elif want[0] == "years":
            verdicts.append(have[1] <= want[2] + 1e-9 and want[1] <= have[2] + 1e-9)
        else:
            verdicts.append(want[1] == have[1] if want[0] == "letter" else (True if want[1] == have[1] else None))
    if any(v is True for v in verdicts):
        return True
    return False if verdicts and all(v is False for v in verdicts) else None


def phrase_in(phrase, text):
    phrase = " ".join(words(phrase))
    return bool(phrase) and re.search(r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])", " ".join(words(text))) is not None


def brand_rule(term, product):
    """The brand field decides when present; otherwise the brand named in the title counts."""
    brand = product.brand.strip()
    if brand:
        return phrase_in(term, brand) or phrase_in(brand, term)
    return True if phrase_in(term, product.name) else None


def merchant_rule(term, product):
    """A seller term matches the seller name or the listing's host ("amazon" -> "Amazon US (www.amazon.sg)")."""
    from urllib.parse import urlparse
    host = (urlparse(product.source_url).hostname or "").replace(".", " ")
    return phrase_in(term, product.merchant) or phrase_in(term, host)
