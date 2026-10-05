# Campus Customs: Yale Merch Storefront + AI Shopping Assistant (HW4)

A React storefront for **Campus Customs (CC)** with a PydanticAI chat assistant. The assistant searches the catalogue (typos OK), checks live stock and prices from the database, updates the product grid from chat, and remembers logged-in shoppers.

- **Frontend:** React 19 + Vite + TypeScript (`frontend/`)
- **Backend:** FastAPI + PydanticAI agent via the Portkey gateway (`backend/`)
- **Data:** SQLite `campus_customs.db` + product photos (a local data pack, **not in git**)

---

## 1. Requirements
- **Python 3.11+** (developed on 3.13)
- **Node.js 20+** and npm (developed on Node 24)
- A **Portkey API key** for the model calls

## 2. Place the data pack
The database and product images are not in this repo. Unzip the course data pack (`data.zip`) **inside the `hw4/` folder**, so the layout is:

```
hw4/
└── data/
    ├── campus_customs.db
    └── products/          # images referenced by the catalogue table (image_file_path)
```
For example, from inside `hw4/`:
```bash
unzip /path/to/data.zip
```
`data/` is git-ignored. On first start the backend also creates `data/products_web/` (cleaned, uniform copies of the photos). This happens automatically in the background and takes a minute or two; the originals are shown until it finishes.

## 3. Configure the API key
```bash
cp .env.example .env
```
Then edit `.env` and set `PORTKEY_API_KEY=...`. `.env` is git-ignored; never commit it.

## 4. Run the backend (FastAPI + agent)
```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd backend
uvicorn main:app --reload --port 8000
```
- API: http://127.0.0.1:8000 · interactive docs: http://127.0.0.1:8000/docs
- `--reload` only watches `.py` files, so restart after editing `backend/prompts/prompt.md`.

## 5. Run the frontend (in a second terminal)
```bash
cd frontend
npm install
npm run dev
```
Open **http://localhost:5173**. Vite forwards `/api` and `/media` to the backend on port 8000, so start the backend first.

## 6. Try it
- **Test account:** `test@campuscustoms.yale.edu` / `password` (from the assignment's seed data). Or use **Create Account**.
- Open **Ask CC** (bottom right) and try:
  - "What hoodies do you have?" (the Products page fills with hoodie cards)
  - On a product page: "Is this in stock in M?" or "Do you have this in pink?"
  - "do u have any quater zips for branferd" (typos are fixed and the fixes are shown)
- The Products page also has a typo-tolerant search box, category filters and sorting.

## 7. Project layout
```
hw4/
├── AI_prompts.md          # every prompt typed into the vibe coder, by problem
├── README.md
├── requirements.txt
├── .env.example           # placeholders only
├── .gitignore             # excludes .env, data/, node_modules/, build output
├── frontend/              # Vite + React + TypeScript storefront
├── backend/
│   ├── main.py            # FastAPI app: run with `uvicorn main:app --reload --port 8000`
│   │                      #   (API routes, accounts/login, product-photo cleanup)
│   ├── agent.py           # the agent: model, prompt, validators, run loop, safety, audit trail
│   ├── tools.py           # the agent's tools (search, details, stock, page, account) + DB/fuzzy helpers
│   ├── models.py          # Pydantic/PydanticAI structured types
│   └── prompts/
│       └── prompt.md      # system prompt: CC voice, tool rules, safety rules
└── output/
    ├── harness.md         # how the system works: models, tools, types, safety, limits, audit (start here)
    ├── design.md          # storefront design decisions (Problem 10)
    ├── usability.md       # 4 usability improvements with before/after measurements (Problem 9)
    ├── app_check.html     # live-site test report; double-click to open (Problem 11)
    ├── app_check_images/  # screenshots linked from app_check.html
    └── audit_trail.json   # append-only agent activity log (JSON Lines; one event per line)
```
The **agent** is exactly four files: `backend/prompts/prompt.md`, `backend/agent.py`, `backend/tools.py` and `backend/models.py`. `backend/main.py` is the web server around it.

## 8. Key specs (details in `output/harness.md`)
| | |
|---|---|
| Model | `gpt-5.6-luna` via Portkey, reasoning effort `none`, parallel tool calls, max 600 output tokens |
| Loop limits | ≤ 8 model calls and ≤ 60 s per chat turn, 2 output retries |
| Result caps | search ≤ 30 results; page grid ≤ 30 cards; chat ≤ 6 cards; 20 history turns replayed; messages ≤ 1000 chars |
| Safety | 10 rules in `prompt.md`. Enforced in code: real prices only, no other people's emails, card/SSN/password messages blocked before the model, tools can't read user accounts |
| Audit | Every turn is appended to `output/audit_trail.json`: time, tool, short args/result, stop reason (sensitive data redacted, never wiped) |
| Passwords | PBKDF2-SHA256 (600k iterations, per-user salt); session tokens stored hashed |

## 9. Troubleshooting
- **`PORTKEY_API_KEY is missing`:** create `hw4/.env` from `.env.example`.
- **Images missing or 404:** check that `hw4/data/products/` exists (step 2). To rebuild the cleaned copies by hand: `cd backend && python main.py --prepare-images`.
- **Chat says "having trouble":** check the backend terminal; the Portkey key or network is the usual cause.
- **Test login fails:** on startup the backend re-hashes only the documented test account (the seed stores it in an older, unverifiable hash format). Restart the backend once after placing the data pack.
