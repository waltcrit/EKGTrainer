/**
 * Academy return-path utilities.
 *
 * Flow:
 *   1. User is on a lesson page (e.g. /learn/beginner/09-pr-interval).
 *   2. They click <LoadStripButton> → saveAcademyLocation() saves the
 *      current URL + scrollY to sessionStorage.
 *   3. Trainer page (/) mounts → reads the saved location and renders
 *      <ReturnToAcademy>, which shows a dismissible "Back to Academy" banner.
 *   4. User clicks "Return" → we write the scroll target to sessionStorage
 *      under a separate key, navigate to the saved href, and <ScrollRestorer>
 *      on the lesson page applies window.scrollTo on mount.
 *
 * sessionStorage is chosen (over localStorage) so the state is tab-scoped
 * and cleared when the tab closes, which is the expected lifetime.
 */

const RETURN_KEY = "ekg_academy_return";
const SCROLL_KEY = "ekg_academy_scroll";

// ── Types ────────────────────────────────────────────────────────────────────

export interface AcademyLocation {
  /** Full URL including origin (e.g. http://localhost:3000/learn/beginner/09-pr-interval) */
  href: string;
  /** window.scrollY at the time of navigation */
  scrollY: number;
  /** Human-readable lesson title for the banner ("Back to …") */
  title?: string;
}

// ── Save / read / clear location ─────────────────────────────────────────────

/**
 * Called by LoadStripButton immediately before navigating to the Trainer.
 * Snapshots the current URL and scroll position.
 */
export function saveAcademyLocation(title?: string): void {
  if (typeof window === "undefined") return;
  const loc: AcademyLocation = {
    href: window.location.href,
    scrollY: window.scrollY,
    title,
  };
  try {
    sessionStorage.setItem(RETURN_KEY, JSON.stringify(loc));
  } catch {
    // sessionStorage may be unavailable in some privacy modes — fail silently.
  }
}

/**
 * Called by ReturnToAcademy on mount to check whether a return path exists.
 * Returns null if nothing was saved or if parsing fails.
 */
export function getAcademyLocation(): AcademyLocation | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(RETURN_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as AcademyLocation;
  } catch {
    return null;
  }
}

/**
 * Removes the saved return location.
 * Call this after the user dismisses the banner or completes the return.
 */
export function clearAcademyLocation(): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.removeItem(RETURN_KEY);
  } catch {
    // ignore
  }
}

// ── Pending scroll (written by ReturnToAcademy, read by ScrollRestorer) ──────

/**
 * Saves the Y position that the lesson page should scroll to on next mount.
 * Written immediately before navigating back to the lesson.
 */
export function savePendingScroll(y: number): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.setItem(SCROLL_KEY, String(y));
  } catch {
    // ignore
  }
}

/**
 * Reads and clears the pending scroll value.
 * Returns null if no pending scroll exists.
 */
export function consumePendingScroll(): number | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(SCROLL_KEY);
    if (raw === null) return null;
    sessionStorage.removeItem(SCROLL_KEY);
    const parsed = Number(raw);
    return Number.isFinite(parsed) ? parsed : null;
  } catch {
    return null;
  }
}
