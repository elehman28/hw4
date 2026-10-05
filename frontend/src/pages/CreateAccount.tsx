import { useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import PasswordInput from '../components/PasswordInput'
import type { SignupData } from '../api'

const EMPTY: SignupData = {
  first_name: '',
  last_name: '',
  email: '',
  password: '',
  confirm_password: '',
}

export default function CreateAccount() {
  const { signup } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState<SignupData>(EMPTY)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const update = (field: keyof SignupData) => (e: ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [field]: e.target.value }))

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (form.password !== form.confirm_password) {
      setError('Passwords do not match.')
      return
    }
    setSubmitting(true)
    try {
      await signup(form)
      navigate('/products')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="auth-card">
      <h1>Create Account</h1>
      <form onSubmit={handleSubmit}>
        <label>
          First name
          <input value={form.first_name} onChange={update('first_name')} required autoComplete="given-name" />
        </label>
        <label>
          Last name
          <input value={form.last_name} onChange={update('last_name')} required autoComplete="family-name" />
        </label>
        <label>
          Email
          <input type="email" value={form.email} onChange={update('email')} required autoComplete="email" />
        </label>
        <PasswordInput
          label="Password"
          value={form.password}
          onChange={update('password')}
          autoComplete="new-password"
          minLength={8}
        />
        <PasswordInput
          label="Confirm password"
          value={form.confirm_password}
          onChange={update('confirm_password')}
          autoComplete="new-password"
          minLength={8}
        />
        {error && <p className="error">{error}</p>}
        <button type="submit" className="btn" disabled={submitting}>
          {submitting ? 'Creating account…' : 'Create Account'}
        </button>
      </form>
      <p>
        Already have an account? <Link to="/login">Log in</Link>
      </p>
    </section>
  )
}
