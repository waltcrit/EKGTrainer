"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  getAcademyLocation,
  clearAcademyLocation,
  savePendingScroll,
  type AcademyLocation,
} from "@/lib/learn/academy-return";

/**
 * Renders a dismissible banner when the user has navigated to the Trainer
 * from an Academy lesson and can return to exactly where they left off.
 *
 * Mount this component anywhere inside the Trainer page (e.g. just below the
 * tab navigation bar). It is invisible when there is no saved return path.
 *
 * Hydration safety: all sessionStorage access is deferred to useEffect,
 * so the component renders null on the server and on first client paint,
 * then shows the banner after hydration if a return path exists.
 */
export default function ReturnToAcademy() {
  const [location, setLocation] = useState<AcademyLocation | null>(null);
  const router = useRouter();

  useEffect(() => {
    setLocation(getAcademyLocation());
  }, []);

  if (!location) return null;

  const displayTitle = location.title
    ? `"${location.title}"`
    : "your Academy lesson";

  function handleReturn() {
    if (!location) return;
    // Write the scroll target before navigating so ScrollRestorer can pick it up.
    savePendingScroll(location.scrollY);
    clearAcademyLocation();
    setLocation(null);
    // Next.js App Router: push to the full href.
    // pathname + search + hash is enough; origin is stripped by the router.
    const url = new URL(location.href);
    router.push(url.pathname + url.search + url.hash);
  }

  function handleDismiss() {
    clearAcademyLocation();
    setLocation(null);
  }

  return (
    <div
      role="status"
      aria-live="polite"
      className="flex items-center gap-3 rounded-lg border border-sky-200 bg-sky-50 px-4 py-2.5 text-sm"
    >
      {/* Book icon */}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 20 20"
        fill="currentColor"
        className="w-4 h-4 text-sky-500 shrink-0"
        aria-hidden
      >
        <path d="M10.75 16.82A7.462 7.462 0 0 1 15 15.5c.71 0 1.396.098 2.046.282A.75.75 0 0 0 18 15.06v-11a.75.75 0 0 0-.546-.721A9.006 9.006 0 0 0 15 3a8.963 8.963 0 0 0-4.25 1.065V16.82ZM9.25 4.065A8.963 8.963 0 0 0 5 3c-.85 0-1.673.118-2.454.339A.75.75 0 0 0 2 4.06v11a.75.75 0 0 0 .954.721A7.506 7.506 0 0 1 5 15.5c1.579 0 3.042.487 4.25 1.32V4.065Z" />
      </svg>

      <span className="flex-1 text-sky-800">
        <span className="font-semibold">Back to Academy</span>
        {" — "}
        <span className="opacity-80">continue {displayTitle}</span>
      </span>

      <button
        onClick={handleReturn}
        className="shrink-0 rounded-md bg-sky-600 px-3 py-1 text-xs font-semibold text-white shadow-sm hover:bg-sky-500 active:bg-sky-700 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-600"
      >
        Return
      </button>

      <button
        onClick={handleDismiss}
        aria-label="Dismiss return banner"
        className="shrink-0 rounded p-0.5 text-sky-400 hover:text-sky-600 hover:bg-sky-100 transition-colors"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 16 16"
          fill="currentColor"
          className="w-3.5 h-3.5"
          aria-hidden
        >
          <path d="M5.28 4.22a.75.75 0 0 0-1.06 1.06L6.94 8l-2.72 2.72a.75.75 0 1 0 1.06 1.06L8 9.06l2.72 2.72a.75.75 0 1 0 1.06-1.06L9.06 8l2.72-2.72a.75.75 0 0 0-1.06-1.06L8 6.94 5.28 4.22Z" />
        </svg>
      </button>
    </div>
  );
}
