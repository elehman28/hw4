import { useId, useState } from 'react'
import type { ChangeEvent } from 'react'

interface Props {
  label: string
  value: string
  onChange: (e: ChangeEvent<HTMLInputElement>) => void
  autoComplete: 'current-password' | 'new-password'
  minLength?: number
}

function EyeIcon({ open }: { open: boolean }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z" />
      <circle cx="12" cy="12" r="3" />
      {!open && <line x1="3" y1="3" x2="21" y2="21" />}
    </svg>
  )
}

// Password field with an eye button to show/hide what's typed, so shoppers can check for typos.
export default function PasswordInput({ label, value, onChange, autoComplete, minLength }: Props) {
  const id = useId()
  const [visible, setVisible] = useState(false)

  return (
    <div className="password-field">
      <label htmlFor={id}>{label}</label>
      <div className="password-wrap">
        <input
          id={id}
          type={visible ? 'text' : 'password'}
          value={value}
          onChange={onChange}
          required
          minLength={minLength}
          autoComplete={autoComplete}
          // Don't let spellcheck/autocorrect services see the password while it's visible.
          spellCheck={false}
          autoCapitalize="off"
          autoCorrect="off"
        />
        <button
          type="button"
          className="password-toggle"
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? `Hide ${label.toLowerCase()}` : `Show ${label.toLowerCase()}`}
          aria-pressed={visible}
          aria-controls={id}
          title={visible ? 'Hide password' : 'Show password'}
        >
          <EyeIcon open={!visible} />
        </button>
      </div>
    </div>
  )
}
