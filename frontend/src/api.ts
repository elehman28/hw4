export interface InventoryItem {
  size: string
  quantity: number
}

export interface Product {
  product_id: string
  name: string
  garment_type: string
  description: string
  colors: string[]
  search_tags: string[]
  image_url: string
  price: number
  total_stock: number
  inventory?: InventoryItem[]
}

export interface ProductCardData {
  product_id: string
  name: string
  garment_type: string
  price: number
  image_url: string
  summary: string
  colors: string[]
  sizes_in_stock: string[]
  total_stock: number
}

// Catalogue search results from the chat agent; the Products page renders these as a grid.
export interface SearchResults {
  title: string
  query: string
  products: ProductCardData[]
  note?: string | null // e.g. "Showing results for “hoodie” (we fixed: hoddie → hoodie)"
}

export interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
}

// Where the shopper is; lets the agent resolve "this" on a product page.
export interface PageContext {
  path: string
  product_id: string | null
  search_title: string | null
}

export interface ChatHistoryItem extends ChatTurn {
  products: ProductCardData[]
  created_at: string
}

export interface ChatReply {
  reply: string
  products: ProductCardData[] // mini cards inside the chat widget
  search_results: SearchResults | null // present only for catalogue searches
}

export interface User {
  id: number
  first_name: string
  last_name: string
  email: string
}

export interface AuthResponse {
  token: string
  user: User
}

export interface SignupData {
  first_name: string
  last_name: string
  email: string
  password: string
  confirm_password: string
}

async function getJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    // FastAPI errors look like {"detail": "..."}; surface that message.
    const body = await res.json().catch(() => null)
    const detail = typeof body?.detail === 'string' ? body.detail : `${res.status} ${res.statusText}`
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

const postJson = <T>(url: string, data: unknown, token?: string | null) =>
  getJson<T>(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(data),
  })

export const signup = (data: SignupData) => postJson<AuthResponse>('/api/auth/signup', data)

export const login = (email: string, password: string) =>
  postJson<AuthResponse>('/api/auth/login', { email, password })

export const fetchMe = (token: string) =>
  getJson<{ user: User }>('/api/auth/me', { headers: { Authorization: `Bearer ${token}` } })

export const logout = (token: string) => postJson<{ ok: boolean }>('/api/auth/logout', {}, token)

export const fetchProducts = () => getJson<Product[]>('/api/products')

// Site search box: same typo-tolerant search the chat agent uses.
export const searchProducts = (q: string) =>
  getJson<SearchResults>(`/api/search?q=${encodeURIComponent(q)}`)

export const fetchProduct = (id: string) =>
  getJson<Product>(`/api/products/${encodeURIComponent(id)}`)

// Logged-in users send their token (history is loaded server-side);
// guests send their recent turns so the agent has context.
export const sendChat = (message: string, history: ChatTurn[], token: string | null, page: PageContext) =>
  postJson<ChatReply>('/api/chat', { message, history: token ? [] : history.slice(-20), page }, token)

export const fetchChatHistory = (token: string) =>
  getJson<ChatHistoryItem[]>('/api/chat/history', { headers: { Authorization: `Bearer ${token}` } })

export const formatPrice = (price: number) => `$${price.toFixed(2)}`

// Catalogue names come from file slugs ("Branford 1 4 Zip"); tidy them for display only.
export const displayName = (name: string) => name.replace(/\b1 4 Zip\b/g, '1/4 Zip').replace(/\bUa\b/g, 'UA')
