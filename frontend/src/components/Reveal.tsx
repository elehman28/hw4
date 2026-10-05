import type { ReactNode } from 'react'
import { useReveal } from '../storefront'

// Wraps a section so it fades up when scrolled into view (disabled for reduced-motion users).
export default function Reveal({
  children,
  className = '',
  as: Tag = 'section',
}: {
  children: ReactNode
  className?: string
  as?: 'section' | 'div'
}) {
  const ref = useReveal<HTMLElement>()
  return (
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    <Tag ref={ref as any} className={`reveal ${className}`}>
      {children}
    </Tag>
  )
}
