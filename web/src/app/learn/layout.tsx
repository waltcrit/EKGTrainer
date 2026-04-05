import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "EKG Academy",
  description: "Structured EKG reading curriculum — beginner to advanced",
};

export default function LearnLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      {/* Top nav */}
      <header className="academy-nav sticky top-0 z-30 border-b backdrop-blur-sm">
        <div className="mx-auto max-w-7xl flex items-center justify-between px-4 h-14">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="text-xs font-medium text-[var(--academy-muted)] hover:text-[var(--academy-ink)] transition-colors flex items-center gap-1"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 16 16"
                fill="currentColor"
                className="w-3.5 h-3.5"
                aria-hidden
              >
                <path
                  fillRule="evenodd"
                  d="M14 8a.75.75 0 0 1-.75.75H4.56l3.22 3.22a.75.75 0 1 1-1.06 1.06l-4.5-4.5a.75.75 0 0 1 0-1.06l4.5-4.5a.75.75 0 0 1 1.06 1.06L4.56 7.25H13.25A.75.75 0 0 1 14 8Z"
                  clipRule="evenodd"
                />
              </svg>
              Trainer
            </Link>
            <span className="text-[color-mix(in_oklab,var(--academy-muted)_38%,white)]">/</span>
            <Link
              href="/learn"
              className="academy-heading text-sm text-[var(--academy-ink)] hover:text-teal-700 transition-colors"
            >
              EKG Academy
            </Link>
          </div>

          {/* Pulse icon */}
          <div className="flex items-center gap-1.5 text-teal-700">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              className="w-4 h-4"
              aria-hidden
            >
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
            <span className="text-xs font-semibold tracking-wide uppercase text-[var(--academy-muted)] hidden sm:block">
              EKG Academy
            </span>
          </div>
        </div>
      </header>

      {children}
    </div>
  );
}
