"""Tools the Campus Customs agent can call, plus catalogue helpers shared with main.py.

Every fact a tool returns (description, price, per-size quantity) is read from
campus_customs.db at call time, so the agent always sees live data. Catalogue
tools read only the catalogue and inventory tables. Who is chatting and which
page they're on arrive through ShopDeps (built by main.py per request), so no
tool can query users, password hashes, sessions, or anyone else's chat.

Also contains the SQLite connection helper and the fuzzy query parser used by search,
so every agent tool and its helpers live in this one file.
"""

import json
import math
import re
import sqlite3
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass, field
from difflib import SequenceMatcher, get_close_matches
from functools import lru_cache
from pathlib import Path

from pydantic_ai import RunContext

from models import (
    CustomerProfile, PageInfo, ProductCard, ProductDetails, ProductMatch, ProductNotFound, ProductSearch,
    SizeStock, StockCheck, StockStatus,
)


# ============================================================================
# Database connection
# ============================================================================

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "campus_customs.db"


@contextmanager
def get_db():
    """Yield a connection that commits on success and always closes."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# ============================================================================
# Fuzzy query understanding (typos, plurals, compounds, synonyms)
# Fuzzy query understanding for catalogue search (stdlib only: difflib).
#
# Turns a messy shopper query ("do u have any hoodys", "quater zip pulover",
# "branferd crewnek") into clean search terms the scorer can match, and records
# each assumption it made ("hoddie → hoodie") so the agent and the page can say
# "Showing results for …".
#
# Pipeline (normalize_query):
#   1. lowercase + tokenize
#   2. drop filler words ("do", "u", "any", "please" …)
#   3. plural/stem variants: hoodys → hoody, sweatshirts → sweatshirt
#   4. spell-correct unknown words against a vocabulary built from the catalogue
#   5. join split compounds: "crew neck" → crewneck, "quarter zip" → quarter-zip, "t shirt" → t-shirt
#   6. map synonyms: tee → t-shirt, hoody → hoodie, grey → gray
# ============================================================================

STOPWORDS = {
    "a", "an", "and", "the", "for", "with", "of", "in", "on", "to", "do", "does", "you", "u", "ya",
    "have", "has", "got", "any", "anything", "i", "im", "me", "my", "we", "want", "wanna", "looking",
    "look", "show", "see", "some", "something", "is", "are", "it", "that", "this", "there", "what",
    "which", "can", "could", "would", "like", "need", "get", "buy", "sell", "carry", "please", "pls",
    "plz", "thanks", "hi", "hello", "hey", "find", "search", "item", "items", "stuff", "one", "ones",
    "yale", "campus", "customs",  # every product is Yale merch, so these don't discriminate
}

# Applied after spelling correction.
SYNONYMS = {
    "tee": "t-shirt", "tshirt": "t-shirt", "shirt": "t-shirt", "teeshirt": "t-shirt",
    "sweatshirt": "crewneck", "crew": "crewneck", "hoody": "hoodie", "hood": "hoodie",
    "hooded": "hoodie", "grey": "gray", "quarterzip": "quarter-zip", "1/4": "quarter-zip",
    "qtr": "quarter", "pullover": "pullover", "sweater": "crewneck", "jumper": "crewneck",
}

# Split/joined forms shoppers type -> catalogue form. Applied to the corrected token string.
COMPOUNDS = [
    (re.compile(r"\bcrew[\s-]?neck\b"), "crewneck"),
    (re.compile(r"\b(?:quarter|1/4|qtr)[\s-]?zips?\b"), "quarter-zip"),
    (re.compile(r"\bhalf[\s-]?zips?\b"), "quarter-zip"),
    (re.compile(r"\bfull[\s-]?zips?\b"), "full-zip"),
    (re.compile(r"\b(?:t|tee)[\s-]?shirts?\b"), "t-shirt"),
    (re.compile(r"\blong[\s-]?sleeves?\b"), "long-sleeve"),
    (re.compile(r"\bshort[\s-]?sleeves?\b"), "short-sleeve"),
]

# Words the shopper might type that the catalogue spells differently but we still want to recognize.
EXTRA_VOCAB = {"hoodie", "hoody", "tee", "tshirt", "shirt", "sweatshirt", "crew", "neck", "quarter",
               "zip", "pullover", "sweater", "grey", "jumper", "half", "full", "long", "short", "sleeve"}

MIN_CORRECT_LEN = 4  # don't "correct" very short words (too ambiguous: "cap" vs "car")


@dataclass
class ParsedQuery:
    original: str
    terms: list[str]                       # cleaned terms for the scorer
    corrections: list[str] = field(default_factory=list)  # e.g. ["hoddie → hoodie"]

    @property
    def interpreted_as(self) -> str:
        return " ".join(self.terms)


@lru_cache(maxsize=1)
def vocabulary() -> tuple[frozenset[str], Counter]:
    """Every word that appears in the catalogue (names, types, colors, tags, descriptions),
    with frequencies so ties go to the more common (more likely intended) word."""
    counts: Counter = Counter()
    with get_db() as conn:
        for r in conn.execute("SELECT name, garment_type, colors, search_tags, description FROM catalogue"):
            text = " ".join([r[0], r[1], " ".join(json.loads(r[2])), " ".join(json.loads(r[3])), r[4]])
            for w in re.findall(r"[a-z0-9]+", text.lower()):
                if len(w) >= 3:
                    counts[w] += 1
    counts.update({w: 1 for w in EXTRA_VOCAB})
    return frozenset(counts), counts


def _variants(word: str) -> list[str]:
    """The word plus simple plural/stem forms, most specific first."""
    out = [word]
    if word.endswith("ies") and len(word) > 4:
        out += [word[:-3] + "y", word[:-3] + "ie"]
    if word.endswith("es") and len(word) > 4:
        out.append(word[:-2])
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        out.append(word[:-1])
    return out


def _known(word: str, vocab: frozenset[str]) -> bool:
    return word in vocab or word in SYNONYMS or word in STOPWORDS


def correct_word(word: str) -> str:
    """Return the most likely intended catalogue word, or the word unchanged."""
    vocab, counts = vocabulary()
    variants = _variants(word)
    for v in variants:
        if _known(v, vocab):
            return v
    if len(word) < MIN_CORRECT_LEN or word.isdigit():
        return word
    # Longer words tolerate more edits ("huddie" -> hoodie is 2 edits in 6 letters).
    cutoff = 0.75 if len(word) <= 5 else 0.66
    best, best_score = word, 0.0
    for v in variants:
        for cand in get_close_matches(v, vocab, n=5, cutoff=cutoff):
            # similarity first, then how common the word is in the catalogue
            score = SequenceMatcher(None, v, cand).ratio() + min(counts[cand], 50) / 1000
            if score > best_score:
                best, best_score = cand, score
    return best


def normalize_query(text: str) -> ParsedQuery:
    raw_tokens = re.findall(r"[a-z0-9/]+", text.lower())
    corrections: list[str] = []
    fixed: list[str] = []
    for tok in raw_tokens:
        if tok in STOPWORDS or "/" in tok:
            fixed.append(tok)
            continue
        new = correct_word(tok)
        if new != tok and new not in _variants(tok):  # plural stripping isn't worth reporting
            corrections.append(f"{tok} → {new}")
        fixed.append(new)

    joined = " ".join(fixed)
    for pattern, replacement in COMPOUNDS:
        joined = pattern.sub(replacement, joined)

    terms: list[str] = []
    for w in joined.split():
        if w in STOPWORDS:
            continue
        w = SYNONYMS.get(w, w)
        if len(w) > 1 and w not in terms:
            terms.append(w)
    return ParsedQuery(original=text, terms=terms, corrections=corrections)


def best_name_match(ref: str, names: dict[str, str], threshold: float = 0.84, margin: float = 0.04) -> str | None:
    """Fuzzy-match a product name/id with typos to exactly one product_id, or None if unsure.

    names: product_id -> product name. Requires a clear winner so we never silently pick
    the wrong item (then the caller returns ProductNotFound with suggestions instead).
    """
    ref = re.sub(r"[^a-z0-9 ]", " ", ref.lower()).strip()
    scored = []
    for pid, name in names.items():
        n = re.sub(r"[^a-z0-9 ]", " ", name.lower())
        s = max(SequenceMatcher(None, ref, n).ratio(), SequenceMatcher(None, ref, pid.replace("-", " ")).ratio())
        scored.append((s, pid))
    scored.sort(reverse=True)
    if not scored:
        return None
    top = scored[0]
    runner_up = scored[1][0] if len(scored) > 1 else 0.0
    return top[1] if top[0] >= threshold and top[0] - runner_up >= margin else None


# ============================================================================
# Catalogue helpers and agent tools
# ============================================================================

SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"]
SIZE_ALIASES = {
    "EXTRA SMALL": "XS", "X-SMALL": "XS", "SMALL": "S", "MEDIUM": "M", "MED": "M",
    "LARGE": "L", "EXTRA LARGE": "XL", "X-LARGE": "XL", "XXL": "XXL", "2XL": "XXL",
    "XX-LARGE": "XXL", "2X": "XXL",
}
IMAGE_VERSION = "web3"  # bump after changing the image cleanup in main.py
LOW_STOCK_THRESHOLD = 5  # quantities 1-5 are "low_stock" so the agent can say "only a few left"
MAX_SEARCH_RESULTS = 30  # enough for a whole category (e.g. ~27 hoodies)


@dataclass
class ShopDeps:
    """Per-request context handed to every tool and to the dynamic system prompt.

    customer: the logged-in shopper (None = guest). Built server-side from the session token.
    page: where the shopper is on the site, resolved server-side against the DB.
    """

    customer: CustomerProfile | None = None
    page: PageInfo = field(default_factory=lambda: PageInfo(path="/", page="home"))
    # Filled by search_products during the run. For result_type="search", main.py renders the
    # latest search's matches on the page, so the model doesn't have to re-type ~30 product_ids
    # (that echo was the slowest part of a category answer).
    searches: list[ProductSearch] = field(default_factory=list)


# ---------- catalogue helpers (also used by the REST endpoints) ----------

def image_url(image_file_path: str) -> str:
    # image_file_path is relative to data/ ("products/x.jpg"); main.py serves data/products at /media.
    # ?v= busts browser caches whenever the cleaned images change.
    return f"/media/{image_file_path.removeprefix('products/')}?v={IMAGE_VERSION}"


def product_from_row(row: sqlite3.Row) -> dict:
    return {
        "product_id": row["product_id"],
        "name": row["name"],
        "garment_type": row["garment_type"],
        "description": row["description"],
        "colors": json.loads(row["colors"]),
        "search_tags": json.loads(row["search_tags"]),
        "image_url": image_url(row["image_file_path"]),
        "price": row["price"],
    }


def stock_status(quantity: int) -> StockStatus:
    if quantity <= 0:
        return "sold_out"
    return "low_stock" if quantity <= LOW_STOCK_THRESHOLD else "in_stock"


def inventory_for(conn: sqlite3.Connection, product_id: str) -> list[SizeStock]:
    rows = conn.execute(
        "SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)
    ).fetchall()
    inv = [SizeStock(size=r["size"], quantity=r["quantity"], status=stock_status(r["quantity"])) for r in rows]
    inv.sort(key=lambda i: SIZE_ORDER.index(i.size) if i.size in SIZE_ORDER else 99)
    return inv


def stock_totals(conn: sqlite3.Connection) -> dict[str, int]:
    return dict(
        conn.execute("SELECT product_id, SUM(quantity) FROM inventory GROUP BY product_id").fetchall()
    )


def sizes_in_stock_by_product(conn: sqlite3.Connection) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for r in conn.execute("SELECT product_id, size FROM inventory WHERE quantity > 0").fetchall():
        out.setdefault(r["product_id"], []).append(r["size"])
    for sizes in out.values():
        sizes.sort(key=lambda s: SIZE_ORDER.index(s) if s in SIZE_ORDER else 99)
    return out


def card_summary(description: str, max_len: int = 120) -> str:
    first = description.split(". ")[0].rstrip(".") + "."
    return first if len(first) <= max_len else description[: max_len - 1].rstrip() + "…"


def product_cards(product_ids: list[str], limit: int = 6) -> list[ProductCard]:
    """Build cards from the DB for the ids the agent picked; unknown ids are dropped."""
    cards: list[ProductCard] = []
    seen: set[str] = set()
    with get_db() as conn:
        for pid in product_ids:
            if pid in seen or len(cards) >= limit:
                continue
            seen.add(pid)
            row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (pid,)).fetchone()
            if row is None:
                continue
            p = product_from_row(row)
            inv = inventory_for(conn, pid)
            cards.append(
                ProductCard(
                    product_id=pid,
                    name=p["name"],
                    garment_type=p["garment_type"],
                    price=p["price"],
                    image_url=p["image_url"],
                    summary=card_summary(p["description"]),
                    colors=p["colors"],
                    sizes_in_stock=[i.size for i in inv if i.quantity > 0],
                    total_stock=sum(i.quantity for i in inv),
                )
            )
    return cards


def all_prices() -> set[float]:
    with get_db() as conn:
        return {r[0] for r in conn.execute("SELECT DISTINCT price FROM catalogue").fetchall()}


# ---------- search (fuzzy: see "Fuzzy query understanding" above) ----------

def _score(row: sqlite3.Row, terms: list[str]) -> int:
    name = row["name"].lower()
    garment = row["garment_type"].lower()
    colors = row["colors"].lower()
    tags = row["search_tags"].lower()
    desc = row["description"].lower()
    score = 0
    for t in terms:
        if t in name:
            score += 4
        if t in garment:
            score += 4
        if t in colors:
            score += 3
        if t in tags:
            score += 2
        if t in desc:
            score += 1
    return score


def _search(
    conn: sqlite3.Connection, query: str, max_price: float | None, in_stock_only: bool, limit: int = MAX_SEARCH_RESULTS
) -> ProductSearch:
    parsed = normalize_query(query)
    terms = parsed.terms
    rows = conn.execute("SELECT * FROM catalogue").fetchall()
    totals = stock_totals(conn)
    sizes = sizes_in_stock_by_product(conn)

    # Rare words are more specific than common ones: "branford" (2 products) should outrank
    # "crewneck" (30 products) when nothing matches both. Weight each term by IDF.
    df = {t: sum(1 for r in rows if _score(r, [t]) > 0) for t in terms}
    idf = {t: math.log((len(rows) + 1) / (df[t] + 1)) + 1 for t in terms}

    scored = []
    for r in rows:
        if max_price is not None and r["price"] > max_price:
            continue
        stock = totals.get(r["product_id"], 0)
        if in_stock_only and stock == 0:
            continue
        if not terms:
            scored.append((1.0, 0, r, stock))
            continue
        per_term = {t: _score(r, [t]) for t in terms}
        hits = sum(1 for v in per_term.values() if v > 0)
        if hits:
            scored.append((sum(v * idf[t] for t, v in per_term.items()), hits, r, stock))
    # Most terms matched first ("hockey hoodie" -> hockey hoodies before other hoodies),
    # then IDF-weighted score, then name for a stable order.
    scored.sort(key=lambda x: (-x[1], -x[0], x[2]["name"]))

    matches = [
        ProductMatch(
            product_id=r["product_id"],
            name=r["name"],
            garment_type=r["garment_type"],
            price=r["price"],
            colors=json.loads(r["colors"]),
            summary=r["description"][:100],  # short: 30 of these go into the model's context
            total_stock=stock,
            sizes_in_stock=sizes.get(r["product_id"], []),
        )
        for _, _, r, stock in scored[: max(1, min(limit, MAX_SEARCH_RESULTS))]
    ]
    return ProductSearch(
        query=query, interpreted_as=parsed.interpreted_as, corrections=parsed.corrections, matches=matches
    )


def _resolve(conn: sqlite3.Connection, product: str) -> sqlite3.Row | ProductNotFound:
    """Turn a product_id or product name (typos OK) into exactly one catalogue row, or say it can't."""
    ref = product.strip()
    row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (ref.lower(),)).fetchone()
    if row is None:
        row = conn.execute("SELECT * FROM catalogue WHERE lower(name) = ?", (ref.lower(),)).fetchone()
    if row is None:
        # Fuzzy: "Basic Hodie Big Yale" -> basic-hoodie-big-yale, only when one product clearly wins.
        names = dict(conn.execute("SELECT product_id, name FROM catalogue").fetchall())
        pid = best_name_match(ref, names)
        if pid:
            row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (pid,)).fetchone()
    if row is not None:
        return row
    suggestions = _search(conn, ref.replace("-", " "), max_price=None, in_stock_only=False).matches[:5]
    return ProductNotFound(
        query=ref,
        message=(
            f"No product clearly matches '{ref}'. Retry with one of the suggested product_ids, "
            "or ask the shopper which one they mean. Do not guess price or stock."
        ),
        suggestions=suggestions,
    )


def _normalize_size(size: str) -> str | None:
    s = size.strip().upper()
    s = SIZE_ALIASES.get(s, s)
    if s in SIZE_ORDER:
        return s
    # Typos: "meduim" -> MEDIUM -> M, "larg" -> LARGE -> L
    close = get_close_matches(s, list(SIZE_ALIASES), n=1, cutoff=0.75)
    return SIZE_ALIASES[close[0]] if close else None


# ---------- agent tools ----------

def search_products(
    ctx: RunContext[ShopDeps],
    query: str,
    max_price: float | None = None,
    in_stock_only: bool = True,
    limit: int = 20,
) -> ProductSearch:
    """Find products by keywords (garment type, color, sport, residential college, graphic).
    Use this for browsing questions like "what hoodies do you have?"; its results are what
    the website shows as the product grid. For exact per-size stock, follow up with
    get_product_details or check_stock.

    Args:
        query: The shopper's words, typos and all (e.g. "hoddie", "quater zip"); the search
            corrects spelling and reports what it assumed in `corrections`.
        max_price: Optional price ceiling in dollars.
        in_stock_only: If true (default), skip products with zero total stock.
        limit: Max results, 1-30 (default 20). Use 30 for a whole category like "hoodies".
    """
    with get_db() as conn:
        result = _search(conn, query, max_price, in_stock_only, limit)
    if ctx is not None:
        ctx.deps.searches.append(result)
    return result


def get_product_details(ctx: RunContext[ShopDeps], product: str) -> ProductDetails | ProductNotFound:
    """Look up one product's full description, exact price, colors, and stock for every
    size (XS-XXL). Use for "tell me about X", "how much is X", or "what sizes does X come in".

    Args:
        product: The product_id (preferred) or exact product name.
    """
    with get_db() as conn:
        row = _resolve(conn, product)
        if isinstance(row, ProductNotFound):
            return row
        return _details(conn, row)


def _details(conn: sqlite3.Connection, row: sqlite3.Row) -> ProductDetails:
    inv = inventory_for(conn, row["product_id"])
    p = product_from_row(row)
    return ProductDetails(
        product_id=p["product_id"],
        name=p["name"],
        garment_type=p["garment_type"],
        description=p["description"],
        price=p["price"],
        colors=p["colors"],
        inventory=inv,
        sizes_in_stock=[i.size for i in inv if i.quantity > 0],
        sizes_sold_out=[i.size for i in inv if i.quantity <= 0],
        total_stock=sum(i.quantity for i in inv),
    )


def check_stock(ctx: RunContext[ShopDeps], product: str, size: str) -> StockCheck | ProductNotFound | str:
    """Check exactly how many units of one product are in stock in one size. Use for
    "do you have X in medium?" or "how many are left in L?".

    Args:
        product: The product_id (preferred) or exact product name.
        size: XS, S, M, L, XL, or XXL (words like "medium" are accepted).
    """
    norm = _normalize_size(size)
    if norm is None:
        return f"'{size}' is not a size we carry. Sizes are: {', '.join(SIZE_ORDER)}."
    with get_db() as conn:
        row = _resolve(conn, product)
        if isinstance(row, ProductNotFound):
            return row
        inv = inventory_for(conn, row["product_id"])

    this = next((i for i in inv if i.size == norm), None)
    qty = this.quantity if this else 0
    status = stock_status(qty)
    others = [i.size for i in inv if i.quantity > 0 and i.size != norm]
    name = row["name"]
    if status == "sold_out":
        alt = f" Other sizes in stock: {', '.join(others)}." if others else " It is sold out in every size."
        message = f"{name} is SOLD OUT in size {norm} (0 left).{alt}"
    elif status == "low_stock":
        message = f"{name} is in stock in size {norm}, but only {qty} left."
    else:
        message = f"{name} is in stock in size {norm} ({qty} available)."

    return StockCheck(
        product_id=row["product_id"],
        name=name,
        price=row["price"],
        size=norm,
        quantity=qty,
        status=status,
        other_sizes_in_stock=others,
        message=message,
    )


def product_details_by_id(product_id: str) -> ProductDetails | None:
    """Exact-id lookup used to resolve the page the shopper is viewing (no fuzzy matching)."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
        return _details(conn, row) if row else None


def get_my_account(ctx: RunContext[ShopDeps]) -> CustomerProfile | str:
    """Get the logged-in shopper's own account info (name, email, member since).
    Use when they ask "who am I logged in as?" or "what email is on my account?"."""
    if ctx.deps.customer is None:
        return "The shopper is a guest (not logged in). Suggest logging in or creating an account."
    return ctx.deps.customer


def get_current_page(ctx: RunContext[ShopDeps]) -> PageInfo:
    """Get the page the shopper is looking at right now. If they're on a product page,
    `viewed_product` is that product with live price and per-size stock. Use when they
    say "this", "it", or "this one" without naming a product."""
    page = ctx.deps.page
    if page.viewed_product is not None:
        # Refresh so stock is live even if the page context was built a moment ago.
        fresh = product_details_by_id(page.viewed_product.product_id)
        return page.model_copy(update={"viewed_product": fresh})
    return page


SHOP_TOOLS = [search_products, get_product_details, check_stock, get_current_page, get_my_account]
