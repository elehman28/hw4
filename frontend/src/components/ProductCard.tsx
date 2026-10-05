import { Link } from 'react-router-dom'
import { displayName, formatPrice } from '../api'

// Works for both catalogue products (have `description`) and chat search cards (have `summary`).
export interface CardProduct {
  product_id: string
  name: string
  price: number
  image_url: string
  total_stock: number
  garment_type?: string
  description?: string
  summary?: string
}

function brief(text: string, max = 80) {
  const first = text.split('. ')[0]
  const t = first.length < text.length ? `${first}.` : text
  return t.length > max ? `${t.slice(0, max).trimEnd()}…` : t
}

export default function ProductCard({ product }: { product: CardProduct }) {
  const soldOut = product.total_stock === 0
  return (
    <Link to={`/products/${product.product_id}`} className="product-card">
      <div className="product-card-img">
        <img src={product.image_url} alt={product.name} loading="lazy" />
        {soldOut && <span className="badge sold-out">Sold out</span>}
        <span className="card-cta" aria-hidden="true">
          View details
        </span>
      </div>
      <div className="product-card-body">
        <h3>{displayName(product.name)}</h3>
        <p className="price">{formatPrice(product.price)}</p>
        <p className="desc">{brief(product.summary ?? product.description ?? '')}</p>
      </div>
    </Link>
  )
}
