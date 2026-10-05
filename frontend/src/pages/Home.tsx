import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { displayName, fetchProducts, searchProducts, type Product } from '../api'
import ProductCard from '../components/ProductCard'
import Reveal from '../components/Reveal'
import { HarknessSkyline } from '../components/YaleArt'
import { useSearchResults } from '../searchResults'
import { CATEGORIES, COLLEGES, openChat } from '../storefront'

// Showcase picks (photos with naturally clean backgrounds); the first is the hero card.
const FEATURED_IDS = [
  'yale-mom-hoodie',
  'super-heavyweight-crewneck-arched-yale-crest',
  '2025-yale-vs-harvard-t-shirt',
  'branford-1-4-zip',
]

export default function Home() {
  const [featured, setFeatured] = useState<Product[]>([])
  const { showResults } = useSearchResults()
  const navigate = useNavigate()

  useEffect(() => {
    fetchProducts()
      .then((all) => {
        const picked = FEATURED_IDS.map((id) => all.find((p) => p.product_id === id)).filter(
          (p): p is Product => !!p && p.total_stock > 0,
        )
        setFeatured(picked.length === 4 ? picked : all.filter((p) => p.total_stock > 0).slice(0, 4))
      })
      .catch(() => setFeatured([]))
  }, [])

  async function shopCollege(name: string) {
    showResults(await searchProducts(name))
    navigate('/products')
  }

  return (
    <>
      {/* Hero */}
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">New Haven, Connecticut</p>
          <h1>
            Wear the <em>Blue.</em>
          </h1>
          <p className="hero-sub">
            Hoodies, crewnecks and quarter-zips for game days, late nights at Sterling, and every
            chilly walk across Old Campus.
          </p>
          <div className="hero-ctas">
            <Link to="/products" className="btn btn-primary">
              Shop the collection
            </Link>
            <button className="btn btn-ghost" onClick={() => openChat()}>
              Ask our assistant
            </button>
          </div>
        </div>
        <div className="hero-art">
          <HarknessSkyline className="hero-skyline" />
          {featured[0] && (
            <Link to={`/products/${featured[0].product_id}`} className="hero-product" aria-label={featured[0].name}>
              <img src={featured[0].image_url} alt="" />
              <span>
                {displayName(featured[0].name)} · ${featured[0].price.toFixed(0)}
              </span>
            </Link>
          )}
        </div>
      </section>

      {/* Shop by category */}
      <Reveal className="container section">
        <div className="section-head">
          <p className="eyebrow">Shop by category</p>
          <h2>Find your layer</h2>
        </div>
        <div className="category-grid">
          {CATEGORIES.map((c) => (
            <Link key={c.key} to={`/products?category=${c.key}`} className="category-tile">
              <div className="category-img">
                <img src={c.image} alt="" loading="lazy" />
              </div>
              <h3>{c.label}</h3>
              <p>{c.blurb}</p>
            </Link>
          ))}
        </div>
      </Reveal>

      {/* Featured */}
      {featured.length > 0 && (
        <Reveal className="container section">
          <div className="section-head row">
            <div>
              <p className="eyebrow">Fan favorites</p>
              <h2>Bulldog essentials</h2>
            </div>
            <Link to="/products" className="text-link">
              View all products →
            </Link>
          </div>
          <div className="product-grid">
            {featured.map((p) => (
              <ProductCard key={p.product_id} product={p} />
            ))}
          </div>
        </Reveal>
      )}

      {/* Editorial band */}
      <Reveal className="band">
        <div className="band-inner">
          <p className="eyebrow light">For the whole family</p>
          <blockquote>For Bulldogs, and everyone who cheers for them.</blockquote>
          <p>Yale Mom, Dad, Grandpa, Aunt and more, so the people back home can wear the blue too.</p>
          <Link to="/products?category=family" className="btn btn-light">
            Shop family gear
          </Link>
        </div>
      </Reveal>

      {/* Residential colleges */}
      <Reveal className="container section">
        <div className="section-head">
          <p className="eyebrow">Residential colleges</p>
          <h2>Rep your college</h2>
          <p className="muted">Crests and logos from across campus. Pick yours.</p>
        </div>
        <div className="college-chips">
          {COLLEGES.map((c) => (
            <button key={c} className="chip" onClick={() => shopCollege(c)}>
              {c}
            </button>
          ))}
        </div>
      </Reveal>

      {/* Value props */}
      <Reveal className="container section values">
        <div>
          <h3>Live stock, every size</h3>
          <p>Each product page shows exactly which sizes are on the shelf right now.</p>
        </div>
        <div>
          <h3>A Yale gear assistant</h3>
          <p>Ask in plain words, typos and all, and get real prices and sizes in seconds.</p>
        </div>
        <div>
          <h3>Gear for every Bulldog</h3>
          <p>Students, parents, grandparents and alumni: there's a sweatshirt with your name on it.</p>
        </div>
      </Reveal>
    </>
  )
}
