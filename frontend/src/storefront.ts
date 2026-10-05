import { useEffect, useRef } from 'react'

// ---------- categories (derived from catalogue garment types / names) ----------

export interface CategoryProduct {
  name: string
  garment_type: string
}

export interface Category {
  key: string
  label: string
  blurb: string
  image: string // a representative product photo
  match: (p: CategoryProduct) => boolean
}

const g = (p: CategoryProduct) => p.garment_type.toLowerCase()

export const CATEGORIES: Category[] = [
  {
    key: 'hoodies',
    label: 'Hoodies',
    blurb: 'Heavyweight layers for late nights at Sterling.',
    image: '/media/fencing-left-chest-hoodie.jpg?v=web3',
    match: (p) => g(p).includes('hood'),
  },
  {
    key: 'crewnecks',
    label: 'Crewnecks',
    blurb: 'The classic Yale sweatshirt, in every shade of blue and gray.',
    image: '/media/super-heavyweight-crewneck-arched-yale-crest.jpg?v=web3',
    match: (p) => (g(p).includes('crewneck') || g(p).includes('mockneck')) && !g(p).includes('t-shirt'),
  },
  {
    key: 'tees',
    label: 'Tees',
    blurb: 'Game-day graphics and everyday basics.',
    image: '/media/2025-yale-vs-harvard-t-shirt.jpg?v=web3',
    match: (p) => g(p).includes('t-shirt') || g(p).includes('shirt'),
  },
  {
    key: 'quarter-zips',
    label: 'Quarter-Zips',
    blurb: 'Residential college crests, ready for the dining hall.',
    image: '/media/branford-1-4-zip.jpg?v=web3',
    match: (p) => g(p).includes('quarter-zip'),
  },
  {
    key: 'outerwear',
    label: 'Outerwear',
    blurb: 'Fleece and jackets for the New Haven wind.',
    image: '/media/benjamin-franklin-fleece-jacket.jpg?v=web3',
    match: (p) => g(p).includes('jacket'),
  },
  {
    key: 'family',
    label: 'For Family',
    blurb: 'Yale Mom, Dad, Grandpa and more.',
    image: '/media/yale-grandpa-hoodie.jpg?v=web3',
    match: (p) => /\b(mom|dad|aunt|uncle|grandma|grandpa|brother|sister|cousin)\b/i.test(p.name),
  },
]

export const categoryByKey = (key: string | null) => CATEGORIES.find((c) => c.key === key) ?? null

export const COLLEGES = [
  'Benjamin Franklin', 'Berkeley', 'Branford', 'Davenport', 'Grace Hopper', 'Jonathan Edwards',
  'Morse', 'Pierson', 'Saybrook', 'Timothy Dwight', 'Trumbull',
]

// ---------- chat bus: lets any page open the assistant (optionally with a question) ----------

export interface OpenChatDetail {
  prefill?: string
  send?: boolean
}

export const openChat = (detail: OpenChatDetail = {}) =>
  window.dispatchEvent(new CustomEvent<OpenChatDetail>('cc:open-chat', { detail }))

// ---------- motion: fade sections/cards up as they scroll into view ----------

export function useReveal<T extends HTMLElement>() {
  const ref = useRef<T>(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches || !('IntersectionObserver' in window)) {
      el.classList.add('is-visible')
      return
    }
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          if (e.isIntersecting) {
            e.target.classList.add('is-visible')
            io.unobserve(e.target)
          }
        }
      },
      { threshold: 0.12, rootMargin: '0px 0px -40px 0px' },
    )
    io.observe(el)
    return () => io.disconnect()
  }, [])
  return ref
}
