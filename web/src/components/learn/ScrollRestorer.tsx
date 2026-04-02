"use client";

import { useEffect } from "react";
import { consumePendingScroll } from "@/lib/learn/academy-return";

/**
 * Invisible client component that restores scroll position when the user
 * returns to a lesson page from the Trainer.
 *
 * How it works:
 *   ReturnToAcademy writes the target scrollY to sessionStorage under
 *   "ekg_academy_scroll" immediately before calling router.push().
 *   This component reads that value on mount, scrolls to it, and clears the key
 *   so subsequent visits to the same page are not affected.
 *
 * Placement: add <ScrollRestorer /> anywhere inside the lesson page Server
 * Component — it renders nothing visible.
 *
 * Why useEffect and not layout effect:
 *   useLayoutEffect fires before paint but after hydration. Both work for
 *   scroll restoration; useEffect is preferred here because we want the page
 *   to paint first (showing content in position) and then jump — this avoids
 *   a flash of blank space while images / prose are loading above the fold.
 *   The jump is "instant" (no animation), so it is imperceptible to the user.
 */
export default function ScrollRestorer() {
  useEffect(() => {
    const target = consumePendingScroll();
    if (target === null) return;

    // Use requestAnimationFrame to ensure the layout has settled after the
    // Next.js App Router render cycle completes and images have their sizes.
    requestAnimationFrame(() => {
      window.scrollTo({ top: target, behavior: "instant" });
    });
  }, []);

  // Renders nothing — purely a side-effect component.
  return null;
}
