# Campus Customs — Storefront Design (Problem 10)

**Goal:** make the site feel like a real Yale shop. It borrows Zara's calm, image-first layout and the Harvard Shop's collegiate category structure, while keeping CC's own identity.

## What changed and why it sells

| Area | What changed | Why it keeps customers around / buying |
|---|---|---|
| **Brand & imagery** | An original **CC crest** (logo, favicon, chat avatar) and a hand-drawn **Harkness Tower / Old Campus at dusk** illustration (`YaleArt.tsx`) in the home hero and About page. A real product (Yale Mom Hoodie, $68) floats over the art. | Instantly says "Yale," builds trust, and puts a buyable product in the first screen. |
| **Product photos** | `backend/main.py (photo cleanup section)` cleaned all 102 photos: it removed black letterboxing and black backgrounds (without erasing black garments), then centered each one on a uniform white 4:5 canvas. Originals are untouched. | A consistent grid looks premium and lets the products, not the backgrounds, stand out. |
| **Typography (2 fonts)** | **Playfair Display** (headings, logo, quotes) + **Inter** (everything else), self-hosted. Small uppercase "eyebrow" labels and an oversized "Wear the *Blue.*" headline set the hierarchy. | Clear reading order: headline → product → price → action. Serif display type feels collegiate and upscale. |
| **Color** | Warm ivory page, Yale navy for actions and accents, a deep-navy footer, and gold only as decoration. All text still meets **WCAG AA** (0 failures across 757 text elements, lowest ratio 6.38:1). | A calm palette makes the navy buttons pop, and everyone can read prices and sizes. |
| **Negative space** | Generous section spacing (`--space` up to 112px), a centered logo with a split nav, and one primary action per section. | Less clutter, so the eye lands on products and "Shop" buttons. |
| **Home structure** | Hero → **Shop by category** (6 tiles) → **Bulldog essentials** → navy **"For the whole family"** band → **Rep your college** chips → value props → 4-column footer. | Gives every kind of shopper (student, parent, alumni) an obvious next click. |
| **Shop page** | Breadcrumbs, a category title, filter chips (Hoodies, Crewnecks, Tees, Quarter-Zips, Outerwear, For Family), sorting by price or name, in-stock items first, and the typo-tolerant search box. Category links are shareable URLs (`/products?category=hoodies`). | Fewer clicks to the right product, and sold-out items don't crowd the top. |
| **Product page** | A large 4:5 image beside a sticky info column, color chips, **size buttons showing live stock** ("8 left" / struck-through "Sold out"), a low-stock message, and **"Ask about this item"**, which opens chat with a question ready to send. | Answers "is my size available?" instantly. Low-stock wording adds healthy urgency, and help is one tap away. |
| **Chat feel** | An "Ask CC" pill with the crest, a chat header with an online status, bubble tails, an animated typing indicator, **suggested-question chips** (different on product pages), and a full-screen panel on phones. | Feels like a friendly store associate, and suggested questions get hesitant shoppers talking. |
| **Motion** | Sections fade up on scroll, product images zoom gently on hover with a "View details" bar, the hero art rises in, and the chat slides open. All motion is off for users who set **prefers-reduced-motion**. | Subtle polish that rewards browsing without slowing anyone down. |
| **Responsive grids** | Products show 4 columns on desktop, 3 on tablet, 2 on phone. Categories go 6 → 3 → 2. The hero stacks on narrow screens, the nav becomes a hamburger drawer under 1180px, and the product page stacks on phones. Verified at 1440px, 1024px and 375px with no horizontal scrolling. | Most campus shoppers are on phones, and the store looks intentional at every size. |

## Files
`frontend/src/index.css` (design system), `components/YaleArt.tsx`, `NavBar.tsx`, `Footer.tsx`, `ChatPanel.tsx`, `ProductCard.tsx`, `Reveal.tsx`, `storefront.ts` (categories, chat-open event, scroll-reveal), `pages/*`, and `backend/main.py (photo cleanup section)` (served at `/media` from `data/products_web/`).
