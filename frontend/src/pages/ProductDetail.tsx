import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { displayName, fetchProduct, formatPrice, type Product } from '../api'
import { openChat } from '../storefront'

const LOW_STOCK = 5

export default function ProductDetail() {
  const { productId } = useParams()
  const [product, setProduct] = useState<Product | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [size, setSize] = useState<string | null>(null)

  useEffect(() => {
    if (!productId) return
    setProduct(null)
    setError(null)
    setSize(null)
    fetchProduct(productId)
      .then(setProduct)
      .catch((e: Error) => setError(e.message))
  }, [productId])

  if (error) return <p className="container error">Couldn't load this product: {error}</p>
  if (!product) return <p className="container muted">Loading…</p>

  const selected = product.inventory?.find((i) => i.size === size) ?? null

  return (
    <div className="container detail-page">
      <nav className="breadcrumbs" aria-label="Breadcrumb">
        <Link to="/products" className="back-link">
          ← Back to Products
        </Link>
      </nav>
      <div className="product-detail">
        <div className="product-detail-img">
          <img src={product.image_url} alt={product.name} />
        </div>
        <div className="product-detail-info">
          <p className="eyebrow garment">{product.garment_type}</p>
          <h1>{displayName(product.name)}</h1>
          <p className="price big">{formatPrice(product.price)}</p>
          <p className="detail-desc">{product.description}</p>

          {product.colors.length > 0 && (
            <div className="detail-block">
              <h2 className="detail-label">Colors</h2>
              <ul className="color-list">
                {product.colors.map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
            </div>
          )}

          {product.inventory && (
            <div className="detail-block">
              <h2 className="detail-label" id="size-label">
                Size {selected && <span className="muted">· {selected.size}</span>}
              </h2>
              <div className="size-grid" role="group" aria-labelledby="size-label">
                {product.inventory.map((i) => {
                  const out = i.quantity === 0
                  return (
                    <button
                      key={i.size}
                      className={`size-pill ${out ? 'out' : ''} ${size === i.size ? 'selected' : ''}`}
                      aria-pressed={size === i.size}
                      aria-label={`${i.size}: ${out ? 'sold out' : `${i.quantity} in stock`}`}
                      onClick={() => setSize(i.size)}
                    >
                      <span className="size-name">{i.size}</span>
                      <span className="size-stock">{out ? 'Sold out' : `${i.quantity} left`}</span>
                    </button>
                  )
                })}
              </div>
              <p className="stock-line" aria-live="polite">
                {selected
                  ? selected.quantity === 0
                    ? `Size ${selected.size} is sold out. Try another size or ask our assistant for a similar style.`
                    : selected.quantity <= LOW_STOCK
                      ? `Only ${selected.quantity} left in ${selected.size}.`
                      : `${selected.quantity} in stock in ${selected.size}.`
                  : `${product.total_stock} available across all sizes. Select a size to check stock.`}
              </p>
            </div>
          )}

          <button
            className="btn btn-primary btn-block"
            onClick={() =>
              openChat({
                prefill: selected
                  ? `Is this available in ${selected.size}? Any similar styles?`
                  : 'Can you tell me more about this item and its sizes?',
              })
            }
          >
            Ask about this item
          </button>
          <p className="muted small">Our assistant knows which item you're viewing and checks live stock.</p>
        </div>
      </div>
    </div>
  )
}
