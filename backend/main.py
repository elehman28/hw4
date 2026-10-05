"""Campus Customs API — catalogue, auth, and the shop chatbot agent.

Run from the backend/ folder:
    uvicorn main:app --reload --port 8000

Sections: accounts/login (auth), product-image cleanup, then the API routes.
"""

import hashlib
import hmac
import json
import logging
import re
import secrets
import sqlite3
import sys
import threading
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from PIL import Image, ImageChops, ImageDraw, ImageFilter
from pydantic import BaseModel
from pydantic_ai.exceptions import ModelHTTPError

from agent import CHAT_MODEL, MAX_HISTORY_TURNS, SENSITIVE_REPLY, audit_write, check_input, new_run_id, run_chat
from models import (
    AgentReply, ChatHistoryItem, ChatRequest, ChatResponse, ChatTurn, CustomerProfile, PageContext, PageInfo,
    ProductCard, SearchResults,
)
from tools import (
    DATA_DIR, ShopDeps, _search, get_db, image_url, inventory_for, product_cards, product_details_by_id,
    product_from_row, stock_totals,
)


# ============================================================================
# Accounts, login and sessions
# Account creation, login, and sessions for Campus Customs.
#
# Passwords are never stored or returned in plain text. We store a salted
# PBKDF2-SHA256 hash; session tokens are random and only their SHA-256 digest
# is kept in the database.
# ============================================================================

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])

PBKDF2_ITERATIONS = 600_000  # OWASP 2023 recommendation for PBKDF2-SHA256
# The seed data uses the older 3-part format "pbkdf2_sha256$salt$hash", which
# doesn't record its iteration count.
LEGACY_PBKDF2_ITERATIONS = 100_000
SESSION_DAYS = 7
MIN_PASSWORD_LEN = 8
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ---------- password hashing ----------

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    parts = stored.split("$")
    if len(parts) == 4 and parts[0] == "pbkdf2_sha256":
        _, iterations, salt, expected = parts
        iterations = int(iterations)
    elif len(parts) == 3 and parts[0] == "pbkdf2_sha256":
        _, salt, expected = parts
        iterations = LEGACY_PBKDF2_ITERATIONS
    else:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations)
    return hmac.compare_digest(digest.hex(), expected)


# ---------- sessions ----------

def ensure_sessions_table() -> None:
    with get_db() as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )"""
        )


TEST_USER_EMAIL = "test@campuscustoms.yale.edu"
TEST_USER_PASSWORD = "password"  # the assignment's published test credential, not a real secret


def ensure_test_user() -> None:
    """The seed DB stores the test account in an older hash format ("pbkdf2_sha256$salt$hash")
    that doesn't record its iteration count, so it can't be verified. Re-hash ONLY that
    documented test account in the current format so `test@campuscustoms.yale.edu / password`
    works on a fresh data pack. Real accounts are never touched."""
    with get_db() as conn:
        row = conn.execute("SELECT id, password_hash FROM users WHERE email = ?", (TEST_USER_EMAIL,)).fetchone()
        if row and len(row["password_hash"].split("$")) == 3:
            conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(TEST_USER_PASSWORD), row["id"]))


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(conn: sqlite3.Connection, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
    conn.execute(
        "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
        (_token_hash(token), user_id, expires.isoformat()),
    )
    return token


def _bearer(authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def public_user(row: sqlite3.Row) -> dict:
    # Only safe fields — password_hash never leaves the backend.
    return {
        "id": row["id"],
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "email": row["email"],
    }


def current_user(authorization: str | None) -> dict | None:
    token = _bearer(authorization)
    if not token:
        return None
    with get_db() as conn:
        row = conn.execute(
            """SELECT u.id, u.first_name, u.last_name, u.email, s.expires_at
               FROM sessions s JOIN users u ON u.id = s.user_id
               WHERE s.token_hash = ?""",
            (_token_hash(token),),
        ).fetchone()
    if row is None or datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
        return None
    return public_user(row)


# ---------- endpoints ----------

class SignupRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    confirm_password: str


class LoginRequest(BaseModel):
    email: str
    password: str


@auth_router.post("/signup", status_code=201)
def signup(req: SignupRequest):
    first, last = req.first_name.strip(), req.last_name.strip()
    email = req.email.strip().lower()
    if not first or not last:
        raise HTTPException(400, "First and last name are required.")
    if not EMAIL_RE.match(email):
        raise HTTPException(400, "Please enter a valid email address.")
    if len(req.password) < MIN_PASSWORD_LEN:
        raise HTTPException(400, f"Password must be at least {MIN_PASSWORD_LEN} characters.")
    if req.password != req.confirm_password:
        raise HTTPException(400, "Passwords do not match.")

    with get_db() as conn:
        exists = conn.execute(
            "SELECT 1 FROM users WHERE lower(email) = ?", (email,)
        ).fetchone()
        if exists:
            raise HTTPException(409, "An account with that email already exists.")
        cur = conn.execute(
            """INSERT INTO users (name, email, password_hash, first_name, last_name)
               VALUES (?, ?, ?, ?, ?)""",
            (f"{first} {last}", email, hash_password(req.password), first, last),
        )
        user_id = cur.lastrowid
        token = create_session(conn, user_id)
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return {"token": token, "user": public_user(row)}


@auth_router.post("/login")
def login(req: LoginRequest):
    email = req.email.strip().lower()
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE lower(email) = ?", (email,)
        ).fetchone()
        # Same message for unknown email and wrong password, so attackers
        # can't probe which emails have accounts.
        if row is None or not verify_password(req.password, row["password_hash"]):
            raise HTTPException(401, "Incorrect email or password.")
        token = create_session(conn, row["id"])
    return {"token": token, "user": public_user(row)}


@auth_router.get("/me")
def me(authorization: str | None = Header(default=None)):
    user = current_user(authorization)
    if user is None:
        raise HTTPException(401, "Not logged in.")
    return {"user": user}


@auth_router.post("/logout")
def logout(authorization: str | None = Header(default=None)):
    token = _bearer(authorization)
    if token:
        with get_db() as conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))
    return {"ok": True}


# ============================================================================
# Product photo cleanup (runs automatically once; see prepare_images_if_needed)
# One-time image prep for the storefront: uniform, clean product photos.
#
# The catalogue photos mix white backgrounds with black letterbox bars and different
# sizes, which makes the product grid look patchy. This writes cleaned copies to
# data/products_web/ (originals in data/products/ are untouched):
#   1. trim rows/columns that are entirely near-black (letterboxing, not garments:
#      a garment column always has white background above/below it)
#   2. whiten any remaining black *background* (flood fill from the border, so only black
#      connected to the edge changes; navy/black garments in the middle are kept)
#   3. trim the remaining white margin
#   4. center on a white 4:5 canvas (800x1000) with even padding
#
# Runs automatically on startup if needed, or manually:  python main.py --prepare-images
# The /media route serves data/products_web/ first, then the originals.
# ============================================================================

SRC, OUT = DATA_DIR / "products", DATA_DIR / "products_web"
CANVAS = (800, 1000)
PAD = 0.07          # fraction of canvas left as white space around the garment
BAR_MAX = 28        # a column/row is a bar only if *every* pixel is darker than this
BG_FILL_THRESH = 22  # flood-fill tolerance: near-pure black only (dark navy/heather stays)
MIN_GARMENT = 0.18   # if whitening leaves less non-white than this, the garment itself was black


def trim_bars(im: Image.Image) -> Image.Image:
    gray = im.convert("L")
    w, h = gray.size
    px = gray.load()

    def col_is_bar(x): return max(px[x, y] for y in range(h)) < BAR_MAX
    def row_is_bar(y): return max(px[x, y] for x in range(w)) < BAR_MAX

    left = 0
    while left < w // 2 and col_is_bar(left):
        left += 1
    right = w
    while right > left + 1 and col_is_bar(right - 1):
        right -= 1
    top = 0
    while top < h // 2 and row_is_bar(top):
        top += 1
    bottom = h
    while bottom > top + 1 and row_is_bar(bottom - 1):
        bottom -= 1
    return im.crop((left, top, right, bottom))


def whiten_black_background(im: Image.Image) -> Image.Image:
    """Flood-fill near-black regions touching the border with white."""
    im = im.copy()
    w, h = im.size
    px = im.load()
    step = max(1, min(w, h) // 60)
    seeds = [(x, 0) for x in range(0, w, step)] + [(x, h - 1) for x in range(0, w, step)]
    seeds += [(0, y) for y in range(0, h, step)] + [(w - 1, y) for y in range(0, h, step)]
    before = im.copy()
    for x, y in seeds:
        if max(px[x, y]) < BG_FILL_THRESH:
            ImageDraw.floodfill(im, (x, y), (255, 255, 255), thresh=BG_FILL_THRESH)
    return remove_halo(before, im)


def remove_halo(before: Image.Image, after: Image.Image, radius: int = 7) -> Image.Image:
    """JPEG edges leave a dark, colorless fringe where the black background met the garment.
    Whiten pixels that are near the filled background AND dark AND gray (not navy/colored)."""
    filled = ImageChops.difference(before, after).convert("L").point(lambda v: 255 if v > 0 else 0)
    near_bg = filled.filter(ImageFilter.MaxFilter(radius))
    out = after.copy()
    o, near = out.load(), near_bg.load()
    w, h = out.size
    for y in range(h):
        for x in range(w):
            if near[x, y]:
                r, g, b = o[x, y]
                if max(r, g, b) < 120 and max(r, g, b) - min(r, g, b) < 22:
                    o[x, y] = (255, 255, 255)
    return out


def non_white_fraction(im: Image.Image) -> float:
    g = im.convert("L").resize((100, 125))
    return sum(1 for v in g.tobytes() if v < 235) / (100 * 125)


def trim_white(im: Image.Image) -> Image.Image:
    bg = Image.new("RGB", im.size, (255, 255, 255))
    diff = ImageChops.difference(im, bg).convert("L").point(lambda v: 255 if v > 18 else 0)
    box = diff.getbbox()
    return im.crop(box) if box else im


def to_canvas(im: Image.Image, bg=(255, 255, 255)) -> Image.Image:
    cw, ch = CANVAS
    max_w, max_h = cw * (1 - 2 * PAD), ch * (1 - 2 * PAD)
    scale = min(max_w / im.width, max_h / im.height)
    im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    canvas = Image.new("RGB", CANVAS, bg)
    canvas.paste(im, ((cw - im.width) // 2, (ch - im.height) // 2))
    return canvas


def prepare_images() -> None:
    OUT.mkdir(exist_ok=True)
    files = sorted(SRC.glob("*.jpg"))
    kept: list[str] = []
    for f in files:
        im = trim_bars(Image.open(f).convert("RGB"))
        white = whiten_black_background(im)
        if non_white_fraction(white) >= MIN_GARMENT or non_white_fraction(im) < 0.5:
            out = to_canvas(trim_white(white))
        else:
            # Black garment on a black background: can't separate them safely, so present
            # it full-bleed on a black tile instead of erasing the garment.
            kept.append(f.name)
            out = to_canvas(im, bg=(0, 0, 0))
        out.save(OUT / f.name, quality=86, optimize=True, progressive=True)
    print(f"wrote {len(files)} images to {OUT}; kept on black: {kept}")


_prepare_lock = threading.Lock()


def prepare_images_if_needed() -> None:
    """Generate data/products_web/ if it's missing or incomplete (e.g. right after placing the data pack)."""
    if not SRC.is_dir():
        return
    with _prepare_lock:
        have = {f.name for f in OUT.glob("*.jpg")} if OUT.is_dir() else set()
        if all(f.name in have for f in SRC.glob("*.jpg")):
            return
        logging.getLogger("campus_customs").warning("preparing cleaned product photos in %s ...", OUT)
        prepare_images()




# ============================================================================
# API
# ============================================================================

log = logging.getLogger("campus_customs")

AGENT_ERROR = "Sorry, the Campus Customs assistant is having trouble right now. Please try again."
MAX_PAGE_RESULTS = 30    # cards in the page grid for a catalogue search
MAX_CHAT_CARDS = 6       # mini cards in the chat widget for specific answers
CHAT_PREVIEW_CARDS = 3   # mini cards in the chat widget when the full results are on the page

BLOCKED_REPLY = (
    "Sorry, I can't help with that. I can only help with Campus Customs products, "
    "sizes, and stock. What Yale gear are you looking for?"
)

app = FastAPI(title="Campus Customs API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
ensure_sessions_table()
ensure_test_user()

# Clean product photos once in the background (a minute or two); originals are served meanwhile.
threading.Thread(target=prepare_images_if_needed, daemon=True).start()

_MEDIA_NAME = re.compile(r"^[a-z0-9][a-z0-9\-]*\.jpg$")


@app.get("/media/{filename}")
def media(filename: str):
    """Product photos only. data/ itself (database, password hashes) is never web-served.
    Strict file-name check, so no path traversal."""
    if not _MEDIA_NAME.match(filename):
        raise HTTPException(status_code=404, detail="Not found")
    for folder in (OUT, SRC):  # cleaned copy first, then the original
        path = folder / filename
        if path.is_file():
            return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=86400"})
    raise HTTPException(status_code=404, detail="Not found")

HISTORY_DISPLAY_LIMIT = 100  # saved messages redrawn in the widget when a shopper returns


def ensure_chat_schema() -> None:
    """chat_messages ships with the seed DB; add the page_path column and a per-user index."""
    with get_db() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(chat_messages)")}
        if "page_path" not in cols:
            conn.execute("ALTER TABLE chat_messages ADD COLUMN page_path TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_user ON chat_messages (user_id, id)")


ensure_chat_schema()


@app.get("/api/health")
def health():
    return {"ok": True, "model": CHAT_MODEL}


@app.get("/api/products")
def list_products():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM catalogue ORDER BY name").fetchall()
        totals = stock_totals(conn)
    return [{**product_from_row(r), "total_stock": totals.get(r["product_id"], 0)} for r in rows]


@app.get("/api/products/{product_id}")
def get_product(product_id: str):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Product not found")
        inventory = [i.model_dump() for i in inventory_for(conn, product_id)]
    return {
        **product_from_row(row),
        "inventory": inventory,
        "total_stock": sum(i["quantity"] for i in inventory),
    }


# ---------- site search (same fuzzy search the agent uses) ----------

def search_note(search) -> str | None:
    if search.corrections:
        fixes = ", ".join(search.corrections)
        return f"Showing results for “{search.interpreted_as}” (we fixed: {fixes})"
    return None


@app.get("/api/search", response_model=SearchResults)
def site_search(q: str = Query(min_length=1, max_length=200), limit: int = Query(30, ge=1, le=30)):
    with get_db() as conn:
        search = _search(conn, q, max_price=None, in_stock_only=False, limit=limit)
    cards = product_cards([m.product_id for m in search.matches], limit=limit)
    title = f"Results for “{search.interpreted_as or q}”" if cards else f"No matches for “{q}”"
    return SearchResults(title=title, query=q, products=cards, note=search_note(search))


# ---------- chat: memory + context ----------

def load_user_history(user_id: int, limit: int = MAX_HISTORY_TURNS) -> list[ChatTurn]:
    """The shopper's most recent saved turns, oldest first (replayed to the model)."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT role, content FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [ChatTurn(role=r["role"], content=r["content"]) for r in reversed(rows)]


def save_turn(user_id: int, message: str, response: ChatResponse, page_path: str) -> None:
    shown = response.search_results.products if response.search_results else response.products
    products_json = json.dumps([p.model_dump() for p in shown]) if shown else None
    with get_db() as conn:
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, page_path) VALUES (?, 'user', ?, ?)",
            (user_id, message, page_path),
        )
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json, page_path)"
            " VALUES (?, 'assistant', ?, ?, ?)",
            (user_id, response.reply, products_json, page_path),
        )


def build_customer(user: dict) -> CustomerProfile:
    """Safe customer fields for the agent; built from the session, never from the request body."""
    with get_db() as conn:
        created = conn.execute("SELECT created_at FROM users WHERE id = ?", (user["id"],)).fetchone()
        count = conn.execute("SELECT COUNT(*) FROM chat_messages WHERE user_id = ?", (user["id"],)).fetchone()
    return CustomerProfile(
        user_id=user["id"],
        first_name=user["first_name"] or "",
        last_name=user["last_name"] or "",
        email=user["email"],
        member_since=(created[0] or "")[:10],
        past_messages=count[0],
    )


PAGE_NAMES = {"/": "home", "/products": "products", "/about": "about", "/login": "login",
              "/create-account": "create_account"}


def resolve_page(ctx: PageContext) -> PageInfo:
    """Turn the browser's page context into what the agent sees, checking ids against the DB."""
    path = ctx.path.split("?")[0].rstrip("/") or "/"
    if path.startswith("/products/"):
        product = product_details_by_id(ctx.product_id or path.removeprefix("/products/"))
        if product is not None:
            return PageInfo(path=path, page="product_detail", viewed_product=product)
        return PageInfo(path=path, page="other")
    if path == "/products" and ctx.search_title:
        return PageInfo(path=path, page="search_results", search_title=ctx.search_title)
    return PageInfo(path=path, page=PAGE_NAMES.get(path, "other"))


def build_response(message: str, reply: str, out: AgentReply, deps: ShopDeps) -> ChatResponse:
    """Turn the agent's answer into DB-built cards and decide where they render.

    search   -> the latest search_products result from this run (recorded in deps) becomes the
                page grid (up to 30); if the model did list product_ids, those win (its own ranking).
    specific -> chat mini cards only (up to 6)
    """
    if out.result_type == "search":
        last = next((s for s in reversed(deps.searches) if s.matches), None)
        ids = out.product_ids or ([m.product_id for m in last.matches] if last else [])
        cards = product_cards(ids, limit=MAX_PAGE_RESULTS)
        if cards:
            return ChatResponse(
                reply=reply,
                products=cards[:CHAT_PREVIEW_CARDS],
                search_results=SearchResults(
                    title=out.results_title or "Search results",
                    query=message,
                    products=cards,
                    note=search_note(last) if last and not out.product_ids else None,
                ),
            )
    return ChatResponse(reply=reply, products=product_cards(out.product_ids, limit=MAX_CHAT_CARDS))


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, authorization: str | None = Header(default=None)):
    user = current_user(authorization)
    # Logged-in shoppers: history comes from the DB (and new turns are saved).
    # Guests: the browser sends its recent turns; nothing is stored.
    history = load_user_history(user["id"]) if user else req.history
    deps = ShopDeps(
        customer=build_customer(user) if user else None,
        page=resolve_page(req.page),
    )

    # Safety rule enforced in code: card numbers / SSNs / shared passwords never reach the model,
    # the chat history, or the audit trail.
    run_id = new_run_id()
    sensitive = check_input(req.message)
    if sensitive:
        audit_write("run_start", run_id, user=f"user:{user['id']}" if user else "guest",
                    page=deps.page.path, model=CHAT_MODEL, message="[withheld: sensitive data]")
        audit_write("run_end", run_id, stop_reason="blocked_sensitive_input", kind=sensitive)
        return ChatResponse(reply=SENSITIVE_REPLY)

    try:
        out = await run_chat(req.message, history, deps, run_id)
    except ModelHTTPError as e:
        if "content_filter" not in str(e.body):
            log.exception("agent run failed")
            raise HTTPException(status_code=502, detail=AGENT_ERROR)
        # The provider's safety filter blocked the message (e.g. a jailbreak attempt).
        # Answer politely instead of erroring, and don't save it to history.
        log.warning("message blocked by provider content filter")
        return ChatResponse(reply=BLOCKED_REPLY)
    except Exception:
        log.exception("agent run failed")
        raise HTTPException(status_code=502, detail=AGENT_ERROR)

    # Cards are built from the DB, so prices and stock shown are always real.
    # The widget shows plain text, so drop stray markdown bold markers.
    reply = out.reply.replace("**", "")
    response = build_response(req.message, reply, out, deps)
    if user:
        save_turn(user["id"], req.message, response, deps.page.path)
    return response


@app.get("/api/chat/history", response_model=list[ChatHistoryItem])
def chat_history(authorization: str | None = Header(default=None)):
    """Everything the widget needs to redraw a returning shopper's conversation."""
    user = current_user(authorization)
    if user is None:
        raise HTTPException(status_code=401, detail="Not logged in.")
    with get_db() as conn:
        rows = conn.execute(
            "SELECT role, content, products_json, created_at FROM chat_messages"
            " WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user["id"], HISTORY_DISPLAY_LIMIT),
        ).fetchall()
    items = []
    for r in reversed(rows):
        products = []
        if r["products_json"]:
            try:  # older rows (seed data) used a slightly different card shape; skip what doesn't fit
                for raw in json.loads(r["products_json"])[:CHAT_PREVIEW_CARDS]:
                    # Rebuild from the file name so old rows (seed "/media/products/x.jpg",
                    # pre-versioning "/media/x.jpg") point at the current cleaned image.
                    fname = raw.get("image_url", "").split("?")[0].rsplit("/", 1)[-1]
                    raw["image_url"] = image_url(f"products/{fname}")
                    raw.setdefault("summary", "")
                    raw.setdefault("sizes_in_stock", [i["size"] for i in raw.get("inventory", []) if i["quantity"] > 0])
                    products.append(ProductCard.model_validate(raw))
            except Exception:
                products = []
        items.append(ChatHistoryItem(role=r["role"], content=r["content"], products=products,
                                     created_at=r["created_at"]))
    return items


if __name__ == "__main__":
    # `python main.py --prepare-images` regenerates data/products_web/ from data/products/.
    if "--prepare-images" in sys.argv:
        prepare_images()
