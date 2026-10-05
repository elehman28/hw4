import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, matchPath, useLocation, useNavigate } from 'react-router-dom'
import { displayName, fetchChatHistory, formatPrice, sendChat } from '../api'
import type { ChatTurn, PageContext, ProductCardData } from '../api'
import { useAuth } from '../auth'
import { useSearchResults } from '../searchResults'
import type { OpenChatDetail } from '../storefront'
import { Crest } from './YaleArt'

interface Message extends ChatTurn {
  products?: ProductCardData[]
  pageResults?: { title: string; count: number }
  isError?: boolean
}

const GREETING: Message = {
  role: 'assistant',
  content: "Hi! I'm the Campus Customs assistant. Ask me about our Yale gear, sizes, or stock.",
}

const GENERAL_SUGGESTIONS = ['What hoodies do you have?', 'Gifts for a Yale parent', 'Gray crewnecks under $60']
const PRODUCT_SUGGESTIONS = ['Is this in stock in M?', 'What colors does this come in?', 'Show me similar styles']

function ChatProductCard({ p }: { p: ProductCardData }) {
  return (
    <Link to={`/products/${p.product_id}`} className="chat-product">
      <img src={p.image_url} alt={p.name} />
      <div>
        <div className="chat-product-name">{displayName(p.name)}</div>
        <div className="chat-product-price">{formatPrice(p.price)}</div>
        <div className="chat-product-sizes">
          {p.sizes_in_stock.length ? `In stock: ${p.sizes_in_stock.join(', ')}` : 'Sold out'}
        </div>
      </div>
    </Link>
  )
}

export default function ChatPanel() {
  const { user, token } = useAuth()
  const { results, showResults } = useSearchResults()
  const navigate = useNavigate()
  const location = useLocation()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([GREETING])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Reset the conversation when the user logs in or out; logged-in users get their saved history.
  useEffect(() => {
    setMessages([GREETING])
    if (!token) return
    fetchChatHistory(token)
      .then((items) => setMessages([GREETING, ...items]))
      .catch(() => undefined)
  }, [token])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending, open])

  // Any page can open the assistant ("Ask our assistant", "Ask about this item").
  useEffect(() => {
    const onOpen = (e: Event) => {
      const detail = (e as CustomEvent<OpenChatDetail>).detail ?? {}
      setOpen(true)
      if (detail.prefill) setInput(detail.prefill)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
    window.addEventListener('cc:open-chat', onOpen)
    return () => window.removeEventListener('cc:open-chat', onOpen)
  }, [])

  const onProductPage = !!matchPath('/products/:productId', location.pathname)

  // Page context sent with every message (the server re-checks product_id against the DB).
  function currentPage(): PageContext {
    const detail = matchPath('/products/:productId', location.pathname)
    return {
      path: location.pathname,
      product_id: detail?.params.productId ?? null,
      search_title: location.pathname === '/products' && results ? results.title : null,
    }
  }

  async function send(text: string) {
    text = text.trim()
    if (!text || sending) return
    const history: ChatTurn[] = messages
      .slice(1) // skip the canned greeting
      .filter((m) => !m.isError)
      .map(({ role, content }) => ({ role, content }))
    setMessages((m) => [...m, { role: 'user', content: text }])
    setInput('')
    setSending(true)
    try {
      const res = await sendChat(text, history, token, currentPage())
      const sr = res.search_results
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          content: res.reply,
          products: res.products,
          pageResults: sr ? { title: sr.title, count: sr.products.length } : undefined,
        },
      ])
      // Catalogue search: render the full results on the Products page.
      if (sr) {
        showResults(sr)
        if (location.pathname !== '/products') navigate('/products')
        window.scrollTo({ top: 0, behavior: 'smooth' })
      }
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: 'assistant', content: (err as Error).message || 'Something went wrong.', isError: true },
      ])
    } finally {
      setSending(false)
    }
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    void send(input)
  }

  if (!open) {
    return (
      <button className="chat-launcher" onClick={() => setOpen(true)} aria-label="Open chat with the Campus Customs assistant">
        <Crest size={22} />
        <span>Ask CC</span>
      </button>
    )
  }

  const showSuggestions = messages.length <= 1 && !sending

  return (
    <div className="chat-panel" role="dialog" aria-label="Campus Customs chat">
      <div className="chat-header">
        <Crest size={30} />
        <div className="chat-title">
          <span className="chat-name">CC Assistant{user ? ` · Hi, ${user.first_name}` : ''}</span>
          <span className="chat-status">
            <span className="dot" aria-hidden="true" /> Online · checks live stock
          </span>
        </div>
        <button className="chat-close" onClick={() => setOpen(false)} aria-label="Close chat">
          ×
        </button>
      </div>
      <div className="chat-messages" aria-live="polite">
        {messages.map((m, i) => (
          <div key={i} className={`chat-turn ${m.role}`}>
            <div className={`chat-bubble ${m.role}${m.isError ? ' error' : ''}`}>{m.content}</div>
            {m.pageResults && (
              <Link to="/products" className="chat-page-note">
                Showing {m.pageResults.count} {m.pageResults.title.toLowerCase()} on the page →
              </Link>
            )}
            {m.products && m.products.length > 0 && (
              <div className="chat-products">
                {m.products.map((p) => (
                  <ChatProductCard key={p.product_id} p={p} />
                ))}
              </div>
            )}
          </div>
        ))}
        {sending && (
          <div className="chat-bubble assistant typing" aria-label="Assistant is typing">
            <span />
            <span />
            <span />
          </div>
        )}
        {showSuggestions && (
          <div className="chat-suggestions" aria-label="Suggested questions">
            {(onProductPage ? PRODUCT_SUGGESTIONS : GENERAL_SUGGESTIONS).map((s) => (
              <button key={s} className="chip" onClick={() => void send(s)}>
                {s}
              </button>
            ))}
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <form className="chat-input" onSubmit={handleSubmit}>
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about a product…"
          aria-label="Chat message"
          maxLength={1000}
        />
        <button type="submit" disabled={sending || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  )
}
