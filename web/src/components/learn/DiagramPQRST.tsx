"use client";

export type Segment =
  | "p"
  | "pr"
  | "qrs"
  | "st"
  | "t"
  | "qt"
  | "baseline"
  | "qrs_notch";

interface Props {
  /** Which segments to highlight. All others render in muted slate. */
  highlight?: Segment[] | string;
  /** Width of the SVG (default 520). Height is auto-scaled. */
  width?: number;
  className?: string;
}

const HIGHLIGHT_COLOR = "#0284c7"; // sky-600 for stronger emphasis
const MUTED_COLOR = "#cbd5e1"; // slate-300
const LABEL_COLOR = "#64748b"; // slate-500
const GRID_COLOR = "#e2e8f0"; // slate-200

/**
 * Simplified P-QRS-T waveform diagram with optional segment highlighting.
 * Coordinates drawn on a 520×200 canvas.
 */
export default function DiagramPQRST({
  highlight = [],
  width = 520,
  className = "",
}: Props) {
  const normalizedHighlight: Segment[] = Array.isArray(highlight)
    ? highlight
    : highlight
      .split(",")
      .map((s) => s.trim().toLowerCase())
      .filter(Boolean)
      .filter((s): s is Segment => ["p", "pr", "qrs", "st", "t", "qt", "baseline", "qrs_notch"].includes(s));

  const h = 200;
  const ratio = width / 520;

  function color(seg: Segment): string {
    return normalizedHighlight.length === 0 || normalizedHighlight.includes(seg)
      ? HIGHLIGHT_COLOR
      : MUTED_COLOR;
  }

  function isActive(seg: Segment): boolean {
    return normalizedHighlight.length === 0 || normalizedHighlight.includes(seg);
  }

  // Render waveform as per-segment paths so highlighted lessons visibly stand out.
  const waveSegments: { seg: Segment; d: string }[] = [
    { seg: "p", d: "M 60,140 C 75,140 80,110 90,110 C 100,110 105,140 120,140" },
    { seg: "pr", d: "M 120,140 L 160,140" },
    { seg: "qrs", d: "M 160,140 L 175,148 L 195,40 L 210,148 L 230,140" },
    { seg: "st", d: "M 230,140 L 290,140" },
    { seg: "t", d: "M 290,140 C 305,140 315,95 335,90 C 355,85 365,140 380,140" },
  ];

  // Interval indicator positions
  const intervals: { seg: Segment; x1: number; x2: number; label: string; yLine: number }[] = [
    { seg: "pr", x1: 60, x2: 160, label: "PR", yLine: 170 },
    { seg: "qrs", x1: 160, x2: 230, label: "QRS", yLine: 185 },
    { seg: "qt", x1: 160, x2: 380, label: "QT", yLine: 198 },
  ];
  const visibleIntervals = normalizedHighlight.length === 0
    ? intervals
    : intervals.filter(({ seg }) => normalizedHighlight.includes(seg));

  // Segment label positions
  const labels: { seg: Segment; x: number; y: number; text: string }[] = [
    { seg: "p", x: 90, y: 100, text: "P" },
    { seg: "qrs", x: 193, y: 30, text: "R" },
    { seg: "qrs", x: 167, y: 158, text: "Q" },
    { seg: "qrs", x: 215, y: 162, text: "S" },
    { seg: "st", x: 260, y: 132, text: "ST" },
    { seg: "t", x: 335, y: 78, text: "T" },
  ];

  return (
    <div className={className}>
      <svg
        viewBox={`0 0 520 ${h}`}
        width={width}
        height={h * ratio}
        role="img"
        aria-label="P-QRS-T waveform diagram"
        className="block"
      >
        {/* Grid lines */}
        {[40, 90, 140, 190].map((y) => (
          <line key={y} x1={0} y1={y} x2={520} y2={y} stroke={GRID_COLOR} strokeWidth={1} />
        ))}
        {[100, 200, 300, 400, 500].map((x) => (
          <line key={x} x1={x} y1={0} x2={x} y2={h} stroke={GRID_COLOR} strokeWidth={1} />
        ))}

        {/* Baseline */}
        <line
          x1={0} y1={140} x2={520} y2={140}
          stroke={normalizedHighlight.includes("baseline") || normalizedHighlight.length === 0 ? "#cbd5e1" : MUTED_COLOR}
          strokeWidth={1}
          strokeDasharray="4 4"
        />

        {/* Unlabeled baseline tails before/after waveform */}
        <path d="M 20,140 L 60,140" fill="none" stroke={MUTED_COLOR} strokeWidth={2.25} strokeLinecap="round" opacity={0.7} />
        <path d="M 380,140 L 500,140" fill="none" stroke={MUTED_COLOR} strokeWidth={2.25} strokeLinecap="round" opacity={0.7} />

        {/* Waveform segments */}
        {waveSegments.map(({ seg, d }) => (
          <path
            key={seg}
            d={d}
            fill="none"
            stroke={color(seg)}
            strokeWidth={isActive(seg) ? 3.2 : 2.0}
            opacity={isActive(seg) ? 1 : 0.42}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        ))}

        {/* Interval brackets */}
        {visibleIntervals.map(({ seg, x1, x2, label, yLine }) => (
          <g key={seg}>
            <line
              x1={x1} y1={yLine} x2={x2} y2={yLine}
              stroke={color(seg)}
              strokeWidth={isActive(seg) ? 2 : 1.2}
              markerStart={`url(#arrow-${seg})`}
              markerEnd={`url(#arrow-${seg})`}
            />
            <line x1={x1} y1={140} x2={x1} y2={yLine} stroke={color(seg)} strokeWidth={1} strokeDasharray="2 2" opacity={0.8} />
            <line x1={x2} y1={140} x2={x2} y2={yLine} stroke={color(seg)} strokeWidth={1} strokeDasharray="2 2" opacity={0.8} />
            <text
              x={(x1 + x2) / 2}
              y={yLine - 3}
              fontSize={9}
              fill={color(seg)}
              textAnchor="middle"
              fontFamily="ui-monospace, monospace"
              fontWeight="600"
            >
              {label}
            </text>
          </g>
        ))}

        {/* Wave labels */}
        {labels.map(({ seg, x, y, text }) => (
          <text
            key={`${seg}-${text}`}
            x={x}
            y={y}
            fontSize={11}
            fill={color(seg)}
            opacity={isActive(seg) ? 1 : 0.45}
            textAnchor="middle"
            fontFamily="ui-sans-serif, system-ui, sans-serif"
            fontWeight="700"
          >
            {text}
          </text>
        ))}
      </svg>

      {/* Legend */}
      {normalizedHighlight.length > 0 && (
        <p className="mt-1 text-xs text-slate-400 text-center">
          Highlighted:{" "}
          <span className="font-semibold text-sky-500">
            {normalizedHighlight.join(", ").toUpperCase()}
          </span>
        </p>
      )}
    </div>
  );
}
