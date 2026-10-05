import { useEffect, useState } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import { useSearchResults } from '../searchResults'
import { Crest } from './YaleArt'

const shopLinks = [
  { to: '/products', label: 'Shop All' },
  { to: '/products?category=hoodies', label: 'Hoodies' },
  { to: '/products?category=crewnecks', label: 'Crewnecks' },
  { to: '/products?category=quarter-zips', label: 'Quarter-Zips' },
  { to: '/about', label: 'About Us' },
]

export default function NavBar() {
  const { user, logout } = useAuth()
  const { clearResults } = useSearchResults()
  const navigate = useNavigate()
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)

  // Close the mobile menu whenever the page changes.
  useEffect(() => {
    setMenuOpen(false)
  }, [location.pathname, location.search])

  async function handleLogout() {
    await logout()
    navigate('/')
  }

  const isActive = (to: string) => {
    const [path, query] = to.split('?')
    if (query) return location.pathname === path && location.search === `?${query}`
    return location.pathname === path && (path !== '/products' || !location.search)
  }

  return (
    <>
      <div className="announcement">Yale apparel for students, families &amp; alumni · New Haven, CT</div>
      <header className="site-header">
        <div className="header-inner">
          <button
            className="menu-toggle"
            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={menuOpen}
            aria-controls="primary-nav"
            onClick={() => setMenuOpen((o) => !o)}
          >
            <span />
            <span />
            <span />
          </button>

          <nav id="primary-nav" className={`primary-nav ${menuOpen ? 'open' : ''}`} aria-label="Main">
            {shopLinks.map((l) => (
              <Link
                key={l.to}
                to={l.to}
                onClick={() => l.to.startsWith('/products') && clearResults()}
                className={`nav-link ${isActive(l.to) ? 'active' : ''}`}
                aria-current={isActive(l.to) ? 'page' : undefined}
              >
                {l.label}
              </Link>
            ))}
            {/* account links repeat inside the mobile drawer */}
            <div className="nav-account-mobile">
              {user ? (
                <button className="nav-link nav-button" onClick={handleLogout}>
                  Log out
                </button>
              ) : (
                <>
                  <NavLink to="/login" className="nav-link">
                    Log in
                  </NavLink>
                  <NavLink to="/create-account" className="nav-link">
                    Create Account
                  </NavLink>
                </>
              )}
            </div>
          </nav>

          <Link to="/" className="brand" aria-label="Campus Customs home">
            <Crest size={30} />
            <span className="brand-word">Campus Customs</span>
          </Link>

          <div className="header-actions">
            {user ? (
              <>
                <span className="nav-user">Hi, {user.first_name}</span>
                <button className="nav-link nav-button" onClick={handleLogout}>
                  Log out
                </button>
              </>
            ) : (
              <>
                <NavLink to="/login" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
                  Log in
                </NavLink>
                <NavLink
                  to="/create-account"
                  className={({ isActive }) => `nav-link nav-cta ${isActive ? 'active' : ''}`}
                >
                  Create Account
                </NavLink>
              </>
            )}
          </div>
        </div>
      </header>
    </>
  )
}
