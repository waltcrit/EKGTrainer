"use client";

import { useRouter } from "next/navigation";

interface Props {
  /** Case ID matching cases.json, e.g. "nsr_01" */
  stripId: string;
  label?: string;
  className?: string;
}

/**
 * Navigates to Home with a specific case pre-loaded.
 * The home page reads ?caseId= on mount.
 */
export default function LoadStripButton({
  stripId,
  label,
  className = "",
}: Props) {
  const router = useRouter();

  function handleClick() {
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
