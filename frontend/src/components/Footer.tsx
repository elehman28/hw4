import { Link } from 'react-router-dom'
import { openChat } from '../storefront'
import { Crest } from './YaleArt'

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <Crest size={40} />
          <p className="footer-word">Campus Customs</p>
          <p>Yale apparel for everyone who calls New Haven home, even if just for four years.</p>
        </div>
        <div>
          <h2 className="footer-heading">Shop</h2>
          <Link to="/products?category=hoodies">Hoodies</Link>
          <Link to="/products?category=crewnecks">Crewnecks</Link>
          <Link to="/products?category=tees">Tees</Link>
          <Link to="/products?category=quarter-zips">Quarter-Zips</Link>
          <Link to="/products?category=family">For Family</Link>
        </div>
        <div>
          <h2 className="footer-heading">Help</h2>
          <button className="footer-link-button" onClick={() => openChat()}>
            Chat with our assistant
          </button>
          <Link to="/login">Log in</Link>
          <Link to="/create-account">Create an account</Link>
        </div>
        <div>
          <h2 className="footer-heading">Visit</h2>
          <Link to="/about">About Campus Customs</Link>
          <p>New Haven, Connecticut</p>
        </div>
      </div>
      <p className="footer-fine">© {new Date().getFullYear()} Campus Customs · Boola Boola</p>
    </footer>
  )
}
