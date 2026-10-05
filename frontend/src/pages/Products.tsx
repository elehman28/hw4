import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { fetchProducts, searchProducts, type Product } from '../api'
import ProductCard from '../components/ProductCard'
import { useSearchResults } from '../searchResults'
import { CATEGORIES, categoryByKey } from '../storefront'

type Sort = 'featured' | 'price-asc' | 'price-desc' | 'name'

function SearchBar() {
  const { showResults } = useSearchResults()
  const [q, setQ] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const text = q.trim()
    if (!text) return
    setBusy(true)
    setError(null)
    try {
      showResults(await searchProducts(text))
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="search-bar" role="search" onSubmit={handleSubmit}>
      <label htmlFor="product-search" className="visually-hidden">
        Search products
      </label>
      <input
        id="product-search"
        type="search"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search hoodies, crewnecks, colleges… (typos are OK)"
        maxLength={200}
      />
      <button type="submit" className="btn btn-primary" disabled={busy}>
        {busy ? 'Searching…' : 'Search'}
      </button>
      {error && <p className="error">{error}</p>}
    </form>
  )
}

function sortProducts<T extends { price: number; name: string }>(list: T[], sort: Sort): T[] {
  const out = [...list]
  if (sort === 'price-asc') out.sort((a, b) => a.price - b.price || a.name.localeCompare(b.name))
  if (sort === 'price-desc') out.sort((a, b) => b.price - a.price || a.name.localeCompare(b.name))
  if (sort === 'name') out.sort((a, b) => a.name.localeCompare(b.name))
  return out
}

export default function Products() {
  const { results, clearResults } = useSearchResults()
  const [params, setParams] = useSearchParams()
  const category = categoryByKey(params.get('category'))
  const [products, setProducts] = useState<Product[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [sort, setSort] = useState<Sort>('featured')

  useEffect(() => {
    fetchProducts()
      .then(setProducts)
      .catch((e: Error) => setError(e.message))
  }, [])

  const visible = useMemo(() => {
    if (!products) return []
    const list = category ? products.filter(category.match) : products
    // "Featured": in-stock first so shoppers see what they can actually buy.
    const featured = [...list].sort((a, b) => Number(b.total_stock > 0) - Number(a.total_stock > 0))
    return sort === 'featured' ? featured : sortProducts(list, sort)
  }, [products, category, sort])

  function pickCategory(key: string | null) {
    clearResults()
    setParams(key ? { category: key } : {})
  }

  const sortSelect = (
    <label className="sort">
      <span className="visually-hidden">Sort products</span>
      <select value={sort} onChange={(e) => setSort(e.target.value as Sort)}>
        <option value="featured">Sort: Featured</option>
        <option value="price-asc">Price: Low to high</option>
        <option value="price-desc">Price: High to low</option>
        <option value="name">Name: A–Z</option>
      </select>
    </label>
  )

  // Search results (from the chat assistant or the search box) replace the grid until cleared.
  if (results) {
    return (
      <div className="container shop">
        <SearchBar />
        <div className="results-header">
          <div>
            <p className="eyebrow">Search results</p>
            <h1>{results.title}</h1>
            {results.note && <p className="results-note">{results.note}</p>}
            <p className="muted">
              {results.products.length} {results.products.length === 1 ? 'item' : 'items'} · You asked: “
              {results.query}”
            </p>
          </div>
          <button className="btn btn-outline" onClick={clearResults}>
            Show all products
          </button>
        </div>
        <div className="product-grid">
          {results.products.map((p) => (
            <ProductCard key={p.product_id} product={p} />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="container shop">
      <nav className="breadcrumbs" aria-label="Breadcrumb">
        <Link to="/">Home</Link> <span aria-hidden="true">/</span>{' '}
        {category ? (
          <>
            <Link to="/products" onClick={() => pickCategory(null)}>
              Shop
            </Link>{' '}
            <span aria-hidden="true">/</span> <span aria-current="page">{category.label}</span>
          </>
        ) : (
          <span aria-current="page">Shop</span>
        )}
      </nav>
      <div className="shop-head">
        <div>
          <h1>{category ? category.label : 'Shop All'}</h1>
          <p className="muted">{category ? category.blurb : 'Every Campus Customs piece, in one place.'}</p>
        </div>
      </div>
      <SearchBar />
      <div className="toolbar">
        <div className="filter-chips" role="group" aria-label="Filter by category">
          <button className={`chip ${!category ? 'active' : ''}`} aria-pressed={!category} onClick={() => pickCategory(null)}>
            All
          </button>
          {CATEGORIES.map((c) => (
            <button
              key={c.key}
              className={`chip ${category?.key === c.key ? 'active' : ''}`}
              aria-pressed={category?.key === c.key}
              onClick={() => pickCategory(c.key)}
            >
              {c.label}
            </button>
          ))}
        </div>
        {sortSelect}
      </div>

      {error && <p className="error">Couldn't load products: {error}</p>}
      {!products && !error && <p className="muted">Loading products…</p>}
      {products && (
        <>
          <p className="muted count">{visible.length} items</p>
          <div className="product-grid">
            {visible.map((p) => (
              <ProductCard key={p.product_id} product={p} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
