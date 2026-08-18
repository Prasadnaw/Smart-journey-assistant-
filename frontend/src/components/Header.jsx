import { Link } from 'react-router-dom'

export default function Header() {
  return (
    <header className="site-header">
      <Link to="/" className="brand">
        <span className="brand-mark">◆</span>
        <span className="brand-name">JourneyAI <span className="brand-india">India</span></span>
      </Link>
      <div className="brand-tagline">One search. Every practical way there.</div>
    </header>
  )
}
