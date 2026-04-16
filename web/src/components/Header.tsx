const Header = () => (
  <header className="academy-nav sticky top-0 z-50 border-b backdrop-blur-sm">
    <div className="max-w-4xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-4">
      <div className="flex items-center gap-3 shrink-0">
        <img src="/ekg-academy-logo.png" alt="EKG Academy Logo" className="navbar-logo" />
        <button
          onClick={() => setLanded(false)}
          className="academy-pill flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-all duration-150"
        >
          Home
        </button>
      </div>
      <nav className="flex items-center gap-0.5">
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all duration-150
              ${tab === id ? "academy-pill-active" : "academy-pill"}`}
          >
            {label}
          </button>
        ))}
        <Link
          href="/learn"
          className="ml-1 academy-pill px-4 py-1.5 rounded-full text-sm font-medium text-teal-700 hover:bg-teal-50 transition-all duration-150"
        >
          Academy
        </Link>
      </nav>
    </div>
  </header>
);

export default Header;