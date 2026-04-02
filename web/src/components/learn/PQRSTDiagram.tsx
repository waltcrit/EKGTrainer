"use client";

/**
 * PQRSTDiagram — a fully-labelled, self-explanatory PQRST waveform diagram.
 *
 * Designed to appear *early* in the Academy curriculum (Beginner lesson 2:
 * "What Is an ECG?") to give learners an immediate visual map of the waveform
 * before individual components are discussed in depth.
 *
 * Differences from DiagramPQRST (the segment-highlighting variant):
 *   • All labels are always visible — no highlight prop, no muted segments.
 *   • Annotation leader lines connect each label to its wave feature.
 *   • An optional wave-meaning legend ("P = atrial depolarization …") is
 *     shown below the SVG when showLegend is true (default).
 *   • Interval brackets include normal duration ranges.
 *   • The component is self-contained with no external dependencies.
 */

interface Props {
  /**
   * Pixel width of the rendered SVG. Height scales proportionally.
   * Default: 560
   */
  width?: number;
  /**
   * Show the wave-meaning legend below the diagram.
   * Default: true
   */
  showLegend?: boolean;
  className?: string;
}

// ── Design tokens ─────────────────────────────────────────────────────────────

const C = {
  waveform: "#0ea5e9",      // sky-500 — the waveform line
  label: "#0369a1",         // sky-700 — wave letter labels (P, Q, R, S, T)
  leader: "#7dd3fc",        // sky-300 — annotation leader lines
  interval: "#64748b",      // slate-500 — interval brackets + labels
  grid: "#e2e8f0",          // slate-200
  baseline: "#cbd5e1",      // slate-300 — isoelectric line (dashed)
  baseline2: "#0ea5e9",      // sky-500 — baseline segment of waveform (reuse waveform)
  intervalAlt: "#0891b2",   // cyan-600 — QT bracket (longer interval, visually distinct)
  bg: "transparent",
} as const;

// ── SVG layout constants ───────────────────────────────────────────────────────
//
// Viewbox: 580 × 270.  Waveform baseline sits at y = 155.
// All x/y coordinates below are in viewbox units.

const VB_W = 580;
const VB_H = 270;
const BASELINE_Y = 155; // isoelectric line

// Waveform path (single normal-sinus beat, left-padded with flat line).
//
// Anatomy:
//   Flat (pre-P)   : x 20  → 65
//   P wave         : x 65  → 125  (gentle dome, peak at x=95, y=115)
//   PR segment     : x 125 → 170  (flat at baseline)
//   Q notch        : x 170 → 185  (small dip to y=165)
//   R spike        : x 185 → 215  (tall peak to y=40)
//   S notch        : x 215 → 235  (dip to y=168)
//   ST segment     : x 235 → 305  (flat at baseline)
//   T wave         : x 305 → 410  (broad dome, peak at x=358, y=102)
//   Post-T flat    : x 410 → 555

const WAVE_PATH = `
  M 20,${BASELINE_Y}
  L 65,${BASELINE_Y}
  C 78,${BASELINE_Y} 82,115 95,115
  C 108,115 112,${BASELINE_Y} 125,${BASELINE_Y}
  L 170,${BASELINE_Y}
  L 185,165
  L 200,40
  L 215,168
  L 235,${BASELINE_Y}
  L 305,${BASELINE_Y}
  C 322,${BASELINE_Y} 338,102 358,102
  C 378,102 394,${BASELINE_Y} 410,${BASELINE_Y}
  L 555,${BASELINE_Y}
`;

// ── Named waveform positions ───────────────────────────────────────────────────

const POS = {
  // P wave
  pPeak: { x: 95, y: 115 },
  pOnset: { x: 65, y: BASELINE_Y },
  pOffset: { x: 125, y: BASELINE_Y },

  // QRS
  qDip: { x: 185, y: 165 },
  rPeak: { x: 200, y: 40 },
  sDip: { x: 215, y: 168 },
  qrsOnset: { x: 170, y: BASELINE_Y },  // first deviation from baseline into Q
  qrsOffset: { x: 235, y: BASELINE_Y }, // return to baseline after S

  // T wave
  tPeak: { x: 358, y: 102 },
  tOffset: { x: 410, y: BASELINE_Y },

  // ST segment midpoint
  stMid: { x: 270, y: BASELINE_Y },
};

// ── Wave labels — letter + leader line config ─────────────────────────────────

interface WaveLabel {
  letter: string;
  // Label anchor position
  lx: number;
  ly: number;
  // Leader line endpoint (the point on the waveform to point at)
  px: number;
  py: number;
  anchor: "start" | "middle" | "end";
}

const WAVE_LABELS: WaveLabel[] = [
  {
    letter: "P",
    lx: 95, ly: 88,
    px: POS.pPeak.x, py: POS.pPeak.y + 4,
    anchor: "middle",
  },
  {
    letter: "Q",
    lx: 174, ly: 192,
    px: POS.qDip.x, py: POS.qDip.y - 3,
    anchor: "middle",
  },
  {
    letter: "R",
    lx: 200, ly: 20,
    px: POS.rPeak.x, py: POS.rPeak.y + 4,
    anchor: "middle",
  },
  {
    letter: "S",
    lx: 228, ly: 192,
    px: POS.sDip.x, py: POS.sDip.y - 3,
    anchor: "middle",
  },
  {
    letter: "T",
    lx: 358, ly: 75,
    px: POS.tPeak.x, py: POS.tPeak.y + 4,
    anchor: "middle",
  },
];

// ── Interval bracket config ───────────────────────────────────────────────────

interface Bracket {
  id: string;
  x1: number;
  x2: number;
  y: number;           // horizontal line y
  tickH: number;       // tick height (downward from y for bottom brackets)
  label: string;
  sublabel: string;    // e.g. "120–200 ms"
  color: string;
}

const BRACKETS: Bracket[] = [
  {
    id: "pr",
    x1: POS.pOnset.x,
    x2: POS.qrsOnset.x,
    y: 185,
    tickH: 30,
    label: "PR",
    sublabel: "120–200 ms",
    color: C.interval,
  },
  {
    id: "qrs",
    x1: POS.qrsOnset.x,
    x2: POS.qrsOffset.x,
    y: 200,
    tickH: 30,
    label: "QRS",
    sublabel: "< 120 ms",
    color: C.interval,
  },
  {
    id: "qt",
    x1: POS.qrsOnset.x,
    x2: POS.tOffset.x,
    y: 220,
    tickH: 30,
    label: "QT",
    sublabel: "360–440 ms",
    color: C.intervalAlt,
  },
];

// ── Legend rows ───────────────────────────────────────────────────────────────

const LEGEND_ROWS = [
  { symbol: "P", meaning: "Atrial depolarization — the atria contract" },
  { symbol: "QRS", meaning: "Ventricular depolarization — the ventricles contract" },
  { symbol: "T", meaning: "Ventricular repolarization — the ventricles reset" },
  { symbol: "PR", meaning: "AV conduction time (P onset → QRS onset)" },
  { symbol: "QT", meaning: "Total ventricular electrical systole" },
];

// ── Component ─────────────────────────────────────────────────────────────────

export default function PQRSTDiagram({
  width = 560,
  showLegend = true,
  className = "",
}: Props) {
  const ratio = width / VB_W;
  const height = VB_H * ratio;

  return (
    <div className={`not-prose ${className}`}>
      <svg
        viewBox={`0 0 ${VB_W} ${VB_H}`}
        width={width}
        height={height}
        role="img"
        aria-label="Labelled P-QRS-T waveform diagram showing all waves and interval brackets"
        style={{ display: "block", maxWidth: "100%" }}
      >
        {/* ── Grid ── */}
        {[50, 100, 150, 200, 250].map((y) => (
          <line key={`gy-${y}`} x1={0} y1={y} x2={VB_W} y2={y}
            stroke={C.grid} strokeWidth={1} />
        ))}
        {[100, 200, 300, 400, 500].map((x) => (
          <line key={`gx-${x}`} x1={x} y1={0} x2={x} y2={VB_H}
            stroke={C.grid} strokeWidth={1} />
        ))}

        {/* ── Isoelectric baseline ── */}
        <line
          x1={0} y1={BASELINE_Y} x2={VB_W} y2={BASELINE_Y}
          stroke={C.baseline} strokeWidth={1} strokeDasharray="5 4"
        />

        {/* ── Waveform ── */}
        <path
          d={WAVE_PATH}
          fill="none"
          stroke={C.waveform}
          strokeWidth={2.5}
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* ── Interval brackets ── */}
        {BRACKETS.map(({ id, x1, x2, y, label, sublabel, color }) => {
          const midX = (x1 + x2) / 2;
          return (
            <g key={id}>
              {/* Horizontal bar */}
              <line x1={x1} y1={y} x2={x2} y2={y}
                stroke={color} strokeWidth={1.5} />
              {/* Left tick from baseline */}
              <line x1={x1} y1={BASELINE_Y} x2={x1} y2={y}
                stroke={color} strokeWidth={1} strokeDasharray="3 2" />
              {/* Right tick from baseline */}
              <line x1={x2} y1={BASELINE_Y} x2={x2} y2={y}
                stroke={color} strokeWidth={1} strokeDasharray="3 2" />
              {/* Left arrowhead */}
              <polygon
                points={`${x1},${y} ${x1 + 5},${y - 3} ${x1 + 5},${y + 3}`}
                fill={color}
              />
              {/* Right arrowhead */}
              <polygon
                points={`${x2},${y} ${x2 - 5},${y - 3} ${x2 - 5},${y + 3}`}
                fill={color}
              />
              {/* Interval label */}
              <text
                x={midX} y={y - 4}
                fontSize={9} fontWeight="700"
                fontFamily="ui-monospace, monospace"
                fill={color} textAnchor="middle"
              >
                {label}
              </text>
              {/* Normal range sublabel */}
              <text
                x={midX} y={y + 12}
                fontSize={7.5} fontWeight="400"
                fontFamily="ui-sans-serif, sans-serif"
                fill={color} textAnchor="middle" opacity={0.75}
              >
                {sublabel}
              </text>
            </g>
          );
        })}

        {/* ── Wave labels + leader lines ── */}
        {WAVE_LABELS.map(({ letter, lx, ly, px, py }) => (
          <g key={letter}>
            {/* Leader line from label to wave point */}
            <line
              x1={lx} y1={ly + (ly < BASELINE_Y ? 10 : -10)}
              x2={px} y2={py}
              stroke={C.leader} strokeWidth={1} strokeDasharray="3 2"
            />
            {/* Letter label */}
            <text
              x={lx} y={ly}
              fontSize={16} fontWeight="800"
              fontFamily="ui-sans-serif, system-ui, sans-serif"
              fill={C.label} textAnchor="middle"
            >
              {letter}
            </text>
          </g>
        ))}

        {/* ── ST segment label (positioned between QRS offset and T onset) ── */}
        <text
          x={POS.stMid.x} y={BASELINE_Y - 10}
          fontSize={9} fontWeight="600"
          fontFamily="ui-monospace, monospace"
          fill={C.interval} textAnchor="middle" opacity={0.8}
        >
          ST
        </text>
      </svg>

      {/* ── Legend ── */}
      {showLegend && (
        <div className="mt-3 rounded-lg border border-slate-100 bg-slate-50 px-4 py-3">
          <p className="text-[11px] font-bold uppercase tracking-widest text-slate-400 mb-2">
            Wave meanings
          </p>
          <dl className="space-y-1">
            {LEGEND_ROWS.map(({ symbol, meaning }) => (
              <div key={symbol} className="flex items-baseline gap-2 text-xs">
                <dt
                  className="shrink-0 font-bold text-sky-700 font-mono w-8"
                  style={{ minWidth: "2rem" }}
                >
                  {symbol}
                </dt>
                <dd className="text-slate-600">{meaning}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}
    </div>
  );
}
