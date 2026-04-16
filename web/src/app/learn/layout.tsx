import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "EKG Academy",
  description: "Structured EKG reading curriculum — beginner to advanced",
};

function EcgMark({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 48 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polyline points="0,12 8,12 11,4 14,20 17,12 21,12 24,7 27,12 30,12 33,16 36,12 48,12" />
    </svg>
  );
}

export default function LearnLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      {/* Top nav */}
      <header className="academy-nav sticky top-0 z-30 border-b backdrop-blur-sm">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 shrink-0">
            <div className="flex items-center gap-2.5">
              <EcgMark className="w-8 h-4 text-sky-600" />
              <span className="academy-heading text-[var(--academy-ink)] text-[17px] leading-none select-none">
                EKG Academy
              </span>
            </div>
            <Link
              href="/"
              className="academy-pill flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-all duration-150"
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
              Home
            </Link>
          </div>
        </div>
      </header>

      {children}
    </div>
  );
}
