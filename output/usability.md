# Campus Customs — Usability Improvements (Problem 9)

Four improvements, two per layer:

| # | Layer | Improvement | Where it shows up |
|---|---|---|---|
| 1 | Frontend | **Accessible color contrast (WCAG 2.1 AA)** | Every page: colors, form fields, focus rings, disabled button |
| 2 | Backend/agent | **Fuzzy search**: typos and bad grammar still find the right products | Chat assistant + new search box on Products, with a "we fixed: hoddie → hoodie" note |
| 3 | Frontend | **Show/hide password (eye button)** | Log in (1 field), Create Account (2 fields) |
| 4 | Backend/agent | **Faster chatbot replies** (less "thinking") | Every chat message: about 4.2s → 3.3s median |

---

## 1. Frontend: accessible color contrast (WCAG AA)

### The standard
| WCAG 2.1 criterion | Minimum ratio | Applies to |
|---|---|---|
| 1.4.3 Contrast (Minimum) | **4.5 : 1** | Normal text |
| 1.4.3 | **3 : 1** | Large text (≥ 24px, or ≥ 18.66px bold) |
| 1.4.11 Non-text Contrast | **3 : 1** | Boundaries of form inputs and buttons, and focus indicators |
| 2.4.7 Focus Visible | visible | Keyboard focus must be clearly shown |

### Audit before the change
Ratios were computed with the WCAG relative-luminance formula: a script over every color pair in `frontend/src/index.css`, plus an in-browser audit of the rendered pages (see "How it was verified").

| Element | Colors | Ratio | Result |
|---|---|---|---|
| Body text on page background | #1c1f24 on #f7f8fa | 15.55 | Pass |
| Muted text (descriptions, counts, footer) | #5f6672 on #f7f8fa | 5.44 | Pass |
| Links / "From the chat assistant" label | #286dc0 on #eef4fb | **4.70** | Pass, barely (0.2 above the minimum) |
| Links on page background | #286dc0 on #f7f8fa | **4.89** | Pass, barely |
| Browser-default placeholder text | ~#757575 on white | **4.61** | Pass, barely (varies by browser) |
| **Form input borders** (login, create account, chat box) | #e2e5ea on white | **1.26** | **Fail** (1.4.11 needs 3:1) |
| **Disabled "Send" button** (opacity 0.5) | white on #809ab5 | **2.91** | **Fail** |
| **Keyboard focus indicator** | browser default only; nearly invisible on the navy navbar and chat header | — | **Fail** (2.4.7) |

### What I changed (`frontend/src/index.css`)
| Change | Before → After | Why |
|---|---|---|
| `--yale-blue-light` (links, labels, button hover, hero gradient end) | #286dc0 → **#1f5ca8** | Worst case 4.70 → **6.01:1**. Still reads as Yale blue, but no longer sits at the edge of the limit. |
| `--muted` (descriptions, counts, footer, chat sizes) | #5f6672 → **#4b5260** | 5.44 → **7.39:1** on the page background. Small grey text is the hardest to read for low-vision customers. |
| New `--control-border` on all text inputs (login, create account, chat, search) | #e2e5ea → **#767d89** | 1.26 → **4.15:1** (1.4.11). You can now *see where to type*. |
| Disabled Send button | `opacity: .5` → solid **#4b5260** + `cursor: not-allowed` | 2.91 → **7.85:1** for the white text. Disabled still looks disabled, and the label stays readable. |
| Placeholder text | browser default → **`--muted`** | Consistent 7.85:1 in every browser. |
| Navbar links | #dbe6f5 → **#e8eff8** | 9.67 → 10.53:1 on navy. |
| Error red | #b00020 → **#a3001e** | 6.24 → 6.94:1 on the pink error bubble. |
| **New `:focus-visible` ring** | none → 3px **#1f5ca8** (6.66:1) on light surfaces, **#ffd166** (8.46:1) on navy (navbar, chat header, hero, chat launcher) | Keyboard users can always see where they are (2.4.7 / 1.4.11). |

All colors live in CSS variables at the top of `index.css`, each with its contrast ratio in a comment, so future changes are easy to keep compliant.

### Why it helps customers and the business
- **Customers:** shoppers with low vision, color-vision differences, or older eyes (think parents and grandparents buying Yale Mom/Dad/Grandpa gear), or anyone on a phone in bright sun, can read prices, sizes and "Sold out" labels, find the form fields, and navigate by keyboard.
- **Business:** more visitors can complete a purchase, so fewer abandoned carts. It also lowers legal risk, since ADA web-accessibility claims are usually judged against WCAG AA, and it fits a university-affiliated brand where accessibility is expected.

### How it was verified (in the running app)
An in-browser audit script walked every visible text element and computed its WCAG ratio against its real rendered background, including gradients and semi-transparent layers. It covered 8 views: Home, Products, a product page, About, Log in, Create Account, search results, and the open chat panel.

| | Before | After |
|---|---|---|
| Text elements checked | — | **418** |
| Text contrast failures | 0 (but several at 4.6–4.9:1) | **0** |
| Lowest text ratio anywhere | 4.70 | **6.01** |
| Input border ratio | 1.26 (fail) | **3.90–4.15** |
| Focus ring | browser default | **3px solid #1f5ca8** confirmed via computed style on focused input |
| Disabled Send button | white on 50% navy, 2.91 | white on #4b5260, 7.85 (computed `rgb(75, 82, 96)`, opacity 1) |

---

## 2. Backend/agent: fuzzy search (typos and grammar)

### What I added
- **`backend/tools.py (fuzzy section)`** (new; standard library only, `difflib`). It turns a messy query into clean search terms and records every assumption it makes:
  1. **Filler words dropped:** "do", "u", "any", "please", "got", …
  2. **Plurals and stems:** hoodys → hoody, sweatshirts → sweatshirt.
  3. **Spell correction** against a vocabulary built from the catalogue itself (names, garment types, colors, tags, descriptions). Ties go to the more common catalogue word. Short words (< 4 letters) are never "corrected", so "cap" can't become "car".
  4. **Split or joined words:** "crew neck" → crewneck, "quarter zip" / "1/4 zip" → quarter-zip, "t shirt" → t-shirt.
  5. **Synonyms:** tee → t-shirt, hoody → hoodie, grey → gray, sweater → crewneck.
- **Better ranking** (`tools.py → _search`):
  - Products that match *more* of the shopper's words come first.
  - Words are IDF-weighted, so a rare, specific word ("branford", 2 products) beats a common one ("crewneck", 30 products). "branferd crewnek" puts the Branford quarter-zip first instead of 26th.
- **Typo-tolerant product names and sizes:**
  - `check_stock("Basic Hodie Big Yale", "meduim")` resolves to Basic Hoodie Big Yale, size M.
  - Name matching only auto-picks a product when one *clearly* wins. Ambiguous names like "yale mum hoody" (Mom, Dad or Aunt?) return suggestions instead of a confident wrong answer.
- **The assumptions are shown to the customer:**
  - `search_products` now returns `ProductSearch {query, interpreted_as, corrections, matches}`.
  - The prompt tells the agent to say what it searched for ("I read 'quater' as quarter…").
  - The Products page shows a note: *Showing results for "quarter-zip branford" (we fixed: quater → quarter, branferd → branford)*.
- **A new search box on the Products page** (`GET /api/search?q=`) uses the same fuzzy search, so it works without the chat too.

### Why it helps customers and the business
- **Customers:** people type fast on phones. Before, "hoddie", "hoodys", "crewnek" and "branferd" returned **nothing**, and a customer who sees "no results" assumes the shop doesn't carry it. Now they get the right products plus a visible note, so they can correct course if the guess was wrong.
- **Business:** zero-result searches are lost sales. Showing the assumption builds trust ("it understood me"). Making the typo fixing deterministic and in-house (no extra model call) also keeps it fast and free.

### Measured
18 misspelled or ungrammatical queries were run through the search (script: `_search` on each query, checking that the top results are what the shopper meant).

| | Before | After |
|---|---|---|
| Queries returning the right products | **7 / 18** | **18 / 18** |
| Queries returning *nothing* | 7 ("hoddie", "hoodys", "huddie", "do u have any hoodys", "crewnek", "tshrit", "branferd") | 0 |

In the app:
- **Chat:** "do u have any quater zips for branferd" switched the page to "Branford quarter-zips" (11 items, Branford 1/4 Zip first) with the note "we fixed: quater → quarter, branferd → branford". The reply was "Showing quarter-zips (I read 'quater' as quarter and 'branferd' as Branford)… $72" (correct price).
- **Search box:** "branferd crewnek" showed results for "branford crewneck" with both fixes listed.

---

## 3. Frontend: show/hide password (eye button)

### What I added
- **`frontend/src/components/PasswordInput.tsx`** (new): a password field with an eye button inside the right edge. It's used for **Password** on Log in, and **Password** and **Confirm password** on Create Account. Each field toggles independently.
- Clicking the eye switches the field between hidden (`type="password"`) and visible (`type="text"`). The icon changes to a crossed-out eye while the password is visible.
- **Accessible:**
  - It's a real `<button type="button">`, so it doesn't submit the form.
  - It's keyboard-focusable, with the new focus ring.
  - `aria-label` switches between "Show password" and "Hide password", and `aria-pressed` says whether it's on, so screen readers announce it correctly.
  - Icon color is `--muted` (7.85:1).
- **Privacy:**
  - The password is hidden by default.
  - It turns `spellCheck`/`autoCorrect`/`autoCapitalize` off, so a visible password isn't sent to browser spell-check services or auto-capitalized.
  - Nothing is stored. The toggle is purely visual.

### Why it helps customers and the business
- **Customers:** typos in a hidden field are the most common reason logins fail and new accounts get a password the owner doesn't know. Being able to *see* "Bulldog2026!" before submitting avoids "Incorrect email or password" loops. This matters most on phones and for less tech-comfortable family members.
- **Business:** fewer failed logins and password-reset requests, and fewer abandoned sign-ups. More logged-in customers means more saved chat history (Problem 8) and a more personal shopping experience.

### Verified in the app
On `/login`, I typed a test password: the field was `type=password` with label "Show password". After clicking the eye: `type=text`, the password was readable, the label read "Hide password", `aria-pressed=true`, and the icon was the crossed-out eye. Clicking again hid it. On `/create-account`, toggling only Confirm left Password hidden (`["password","text"]`).

---

## 4. Backend/agent: faster chatbot replies (less "thinking")

### What I found
Timing the agent showed that much of the wait was the model **writing tokens nobody reads**:
- **Hidden reasoning tokens:** on "Do you have any navy crewnecks for sailing?", **212 of 328** output tokens were invisible reasoning.
- **Echoing product ids:** for a category search the model re-typed every `product_id` (~27 for hoodies) into its answer so the page could show them. That was 300–400 output tokens per search.
- **Extra round trips:** for "Is the Yale Brother Crewneck in medium, and how much?" it called `search_products`, then `check_stock`, then `get_product_details` (3 model calls) when one tool already had everything.

### What I changed
| Change | File | Effect |
|---|---|---|
| `openai_reasoning_effort="none"` (configurable with `CC_REASONING_EFFORT`; `minimal` isn't supported by this model) | `agent.py` | No hidden reasoning tokens for routine shop lookups. |
| `parallel_tool_calls=True`, `max_tokens=600` | `agent.py` | Independent lookups (two sizes, two products) share one round trip, and runaway replies are capped. |
| The search tool **records its results in `ShopDeps.searches`**. For a page search the agent leaves `product_ids` empty and `main.py` renders the latest search. | `tools.py`, `main.py`, `models.py` | No more re-typing ~30 ids. The page shows exactly what the search found, in its ranked order. |
| Shorter search summaries in tool results (160 → 100 chars × up to 30 matches) | `tools.py` | Less text for the model to read on every search. |
| A new **"Be fast: use the fewest tool calls"** section | `prompts/prompt.md` | Product page plus size question → just `check_stock`. Named product → `check_stock` by name (no search first). Answer color questions from the page context. Batch independent calls. |

Accuracy safeguards are unchanged: the price validator, DB-built cards and prices, and the "call a tool for every price/stock question" rule.

### Measured
I used a benchmark of 5 typical questions (category search, named product + size, typo search, "this in a large?" on a product page, filtered search), run through the real agent. A random value in the page path prevents the gateway from serving cached answers.

| | Before | After (run 1) | After (run 2) |
|---|---|---|---|
| **Median time per answer** | **4.2 s** | **3.3 s** | **3.4 s** |
| Mean time per answer | 4.3 s | 3.1 s | 3.4 s |
| Avg model round trips | 2.2 | 2.0 | 2.0 |
| Avg output tokens | 250 | 97 | 98 |
| Slowest question | 5.7 s (3 round trips) | 3.5 s | 3.5 s |

That's about **20–25% faster** typical replies and **about 60% fewer generated tokens**, and the slowest question improved the most (5.7 s → 3.5 s). The answers stayed correct: Brother Crewneck M was "only 2 left… $58", Dad Hoodie L "20 available", Branford quarter-zip $72, all matching the DB.

The remaining time is mostly the two unavoidable model calls (pick a tool, then answer) plus gateway latency.

### Why it helps customers and the business
- **Customers:** chat feels conversational instead of laggy. A shopper asking "do you have this in a large?" gets an answer in about 3 seconds, not 4–6.
- **Business:** faster answers keep shoppers engaged instead of leaving. About 60% fewer output tokens per message also **lowers the AI bill** for every conversation.
