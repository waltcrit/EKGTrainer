import Link from "next/link";

interface HeaderProps {
  onLogoClick?: () => void;
}

const Header = ({ onLogoClick }: HeaderProps) => (
  <header className="academy-nav sticky top-0 z-50 border-b backdrop-blur-sm">
    <div className="max-w-4xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-4">
      <div className="flex items-center gap-3 shrink-0">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/ekg-academy-logo.png" alt="EKG Academy Logo" className="navbar-logo h-8 w-8" />
        {onLogoClick && (
          <button
            onClick={onLogoClick}
            className="academy-pill flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-all duration-150"
          >
            Home
          </button>
        )}
      </div>
      <nav className="flex items-center gap-0.5">
        <Link
          href="/learn"
          className="academy-pill px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-150"
        >
          Academy
        </Link>
      </nav>
    </div>
  </header>
);

export default Header;