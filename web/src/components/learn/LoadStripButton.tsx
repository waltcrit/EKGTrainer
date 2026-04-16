"use client";

import { useRouter } from "next/navigation";
import { saveAcademyLocation } from "@/lib/learn/academy-return";

interface Props {
  /** Case ID matching cases.json, e.g. "nsr_01" */
  stripId: string;
  label?: string;
  className?: string;
  /**
   * The lesson title displayed in the ReturnToAcademy banner.
   * Pass the current lesson's title so the banner reads
   * "Back to Academy — continue 'The QT Interval'".
   */
  lessonTitle?: string;
}

/**
 * Navigates to the main Trainer with a specific case pre-loaded.
 * Before navigating, saves the current Academy URL and scroll position to
 * sessionStorage so ReturnToAcademy can offer a one-click path back.
 */
export default function LoadStripButton({
  stripId,
  label,
  className = "",
  lessonTitle,
}: Props) {
  const router = useRouter();

  function handleClick() {
    // Snapshot current location before leaving the Academy.
    saveAcademyLocation(lessonTitle);
    router.push(`/?caseId=${encodeURIComponent(stripId)}&tab=practice`);
  }

  return (
    <button
      onClick={handleClick}
      className={`inline-flex items-center gap-2 rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-sky-500 active:bg-sky-700 transition-colors ${className}`}
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 20 20"
        fill="currentColor"
        className="w-4 h-4"
        aria-hidden
      >
        <path
          fillRule="evenodd"
          d="M2 4.75A.75.75 0 0 1 2.75 4h14.5a.75.75 0 0 1 0 1.5H2.75A.75.75 0 0 1 2 4.75Zm0 10.5a.75.75 0 0 1 .75-.75h14.5a.75.75 0 0 1 0 1.5H2.75a.75.75 0 0 1-.75-.75ZM2 10a.75.75 0 0 1 .75-.75h4.5a.75.75 0 0 1 0 1.5h-4.5A.75.75 0 0 1 2 10Z"
          clipRule="evenodd"
        />
      </svg>
      {label ?? `Open strip in Home`}
    </button>
  );
}
