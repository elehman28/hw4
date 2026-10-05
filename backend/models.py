"""Structured types shared by the API and the PydanticAI agent."""

from typing import Literal

from pydantic import BaseModel, Field


# ---------- catalogue lookups (tool results the agent sees) ----------

StockStatus = Literal["in_stock", "low_stock", "sold_out"]


class SizeStock(BaseModel):
    """Stock for one size. `status` spells out sold-out/low so the model never has to infer it."""

    size: str
    quantity: int = Field(description="Exact units on hand from the inventory table.")
    status: StockStatus


class ProductMatch(BaseModel):
    """Compact search result from search_products: enough to choose, not enough to quote stock."""

    product_id: str
    name: str
    garment_type: str
    price: float
    colors: list[str]
    summary: str = Field(description="First ~100 chars of the description.")
    total_stock: int
    sizes_in_stock: list[str]


class ProductSearch(BaseModel):
    """search_products result: matches plus the assumptions the fuzzy search made."""

    query: str = Field(description="What was searched, as typed.")
    interpreted_as: str = Field(description="Cleaned search terms after spelling/grammar fixes.")
    corrections: list[str] = Field(description='Spelling fixes applied, e.g. ["hoddie → hoodie"]. Empty if none.')
    matches: list[ProductMatch]


class ProductDetails(BaseModel):
    """Full record from get_product_details: everything needed to answer price/description/stock."""

    product_id: str
    name: str
    garment_type: str
    description: str
    price: float = Field(description="Price in US dollars, exactly as stored.")
    colors: list[str]
    inventory: list[SizeStock] = Field(description="Every size XS-XXL, in size order, including sold-out ones.")
    sizes_in_stock: list[str]
    sizes_sold_out: list[str]
    total_stock: int


class StockCheck(BaseModel):
    """Answer to "is <product> available in <size>?" from check_stock."""

    product_id: str
    name: str
    price: float
    size: str
    quantity: int
    status: StockStatus
    other_sizes_in_stock: list[str] = Field(description="Alternatives to offer when this size is sold out.")
    message: str = Field(description="One-sentence factual summary the agent can reuse.")


class ProductNotFound(BaseModel):
    """Returned instead of guessing when a product reference doesn't resolve to one product."""

    query: str
    message: str
    suggestions: list[ProductMatch] = Field(description="Closest catalogue matches to offer or retry with.")


# ---------- product cards (chat widget + page) ----------

class ProductCard(BaseModel):
    """A product as the website renders it: in the chat widget and in the page grid.
    Always built from the database, never from model-written text, so price and stock are exact."""

    product_id: str = Field(description="Links the card to /products/<product_id> (the detail page).")
    name: str
    garment_type: str
    price: float
    image_url: str
    summary: str = Field(description="Short description for the card (first sentence-ish, <= 120 chars).")
    colors: list[str]
    sizes_in_stock: list[str]
    total_stock: int


# ---------- who is chatting and where (agent deps) ----------

class CustomerProfile(BaseModel):
    """The logged-in shopper, as the agent sees them. Deliberately excludes password_hash,
    sessions, and anything about other users."""

    user_id: int
    first_name: str
    last_name: str
    email: str
    member_since: str = Field(description="Account creation date (YYYY-MM-DD).")
    past_messages: int = Field(description="How many saved chat messages this shopper has.")


class PageContext(BaseModel):
    """What the browser sends about the page the shopper is on. Untrusted: product_id is
    re-checked against the DB before the agent sees anything."""

    path: str = Field(default="/", max_length=200)
    product_id: str | None = Field(default=None, max_length=120)
    search_title: str | None = Field(default=None, max_length=120)


class PageInfo(BaseModel):
    """Server-resolved page context the agent sees (from PageContext + the DB)."""

    path: str
    page: Literal["home", "products", "search_results", "product_detail", "about", "login", "create_account", "other"]
    viewed_product: ProductDetails | None = Field(
        default=None, description="The product on screen when page='product_detail' ('this', 'it')."
    )
    search_title: str | None = Field(default=None, description="Heading of chat results on the Products page.")


# ---------- agent output ----------

class AgentReply(BaseModel):
    """The agent's structured output for one chat turn."""

    reply: str = Field(description="Friendly reply to the shopper in Campus Customs voice. Plain text, short.")
    result_type: Literal["search", "specific", "none"] = Field(
        default="none",
        description=(
            "'search' = the shopper asked to browse a type/category of item (e.g. 'what hoodies do you have'); "
            "the matching products are shown on the website page. "
            "'specific' = an answer about one or a few named products (price, size, stock); shown only in chat. "
            "'none' = no products to show."
        ),
    )
    results_title: str | None = Field(
        default=None,
        description="For result_type='search' only: short heading for the page, e.g. 'Hoodies' or 'Gray crewnecks under $60'.",
    )
    product_ids: list[str] = Field(
        default_factory=list,
        description=(
            "product_id values from tool results only, best match first. "
            "For 'search': leave EMPTY - the page shows your latest search_products results automatically. "
            "For 'specific': at most 6."
        ),
    )


# ---------- chat API (the contract the frontend relies on) ----------

class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    # Guests send recent turns from the browser; logged-in users' history comes from the DB.
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)
    page: PageContext = Field(default_factory=PageContext)


class SearchResults(BaseModel):
    """Catalogue search results the website renders as a product grid on the Products page."""

    title: str
    query: str = Field(description="The shopper message that produced these results.")
    products: list[ProductCard]
    note: str | None = Field(default=None, description='e.g. "Showing results for hoodie (you typed hoddie)".')


class ChatResponse(BaseModel):
    reply: str
    products: list[ProductCard] = Field(
        default_factory=list, description="Mini cards shown under the reply inside the chat widget."
    )
    search_results: SearchResults | None = Field(
        default=None, description="Present only for catalogue searches: the page grid updates to show these."
    )


class ChatHistoryItem(BaseModel):
    """One saved message, as the chat widget redraws it when a logged-in shopper returns."""

    role: Literal["user", "assistant"]
    content: str
    products: list[ProductCard] = Field(default_factory=list)
    created_at: str
