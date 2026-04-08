import Image from "next/image";

type DiagramVariant = "3lead" | "5lead" | "12lead-limb" | "12lead-chest" | "easi";

interface ElectrodePoint {
  key: string;
  label: string;
  color: string;
  swatchClass: string;
  note: string;
}

interface VariantConfig {
  title: string;
  subtitle: string;
  footer: string;
  imageSrc: string;
  imageAlt: string;
  points: ElectrodePoint[];
}

interface Props {
  variant: DiagramVariant;
}

const VARIANTS: Record<DiagramVariant, VariantConfig> = {
  "3lead": {
    title: "3-Lead Monitoring",
    subtitle: "Basic rhythm monitoring using three electrodes on the torso.",
    footer: "The monitor derives lead I, II, or III from RA, LA, and LL.",
    imageSrc: "/learn/lead-placement/ecg-electrode-placement.png",
    imageAlt: "Diagram showing 3-lead ECG electrode placement on the torso",
    points: [
      { key: "RA", label: "RA", color: "#0f766e", swatchClass: "bg-teal-700", note: "Right upper chest, below the clavicle" },
      { key: "LA", label: "LA", color: "#0f766e", swatchClass: "bg-teal-700", note: "Left upper chest, below the clavicle" },
      { key: "LL", label: "LL", color: "#0284c7", swatchClass: "bg-sky-600", note: "Left lower chest or upper abdomen" },
    ],
  },
  "5lead": {
    title: "5-Lead Monitoring",
    subtitle: "Telemetry setup with four limb electrodes on the torso plus one chest electrode.",
    footer: "The V electrode is often placed at V1 for arrhythmia monitoring or V5 for ischemia monitoring.",
    imageSrc: "/learn/lead-placement/ecg-limb-and-chest-electrodes-placement.png",
    imageAlt: "Diagram showing 5-lead ECG electrode placement with limb and chest electrodes",
    points: [
      { key: "RA", label: "RA", color: "#0f766e", swatchClass: "bg-teal-700", note: "Right upper chest" },
      { key: "LA", label: "LA", color: "#0f766e", swatchClass: "bg-teal-700", note: "Left upper chest" },
      { key: "RL", label: "RL", color: "#f59e0b", swatchClass: "bg-amber-500", note: "Right lower chest or upper abdomen" },
      { key: "LL", label: "LL", color: "#0284c7", swatchClass: "bg-sky-600", note: "Left lower chest or upper abdomen" },
      { key: "V", label: "V", color: "#dc2626", swatchClass: "bg-red-600", note: "One chest position — V1 or V5 per clinical goal" },
    ],
  },
  "12lead-limb": {
    title: "12-Lead Limb Electrodes",
    subtitle: "Diagnostic limb electrodes should represent the limbs, not casual torso substitutions.",
    footer: "These four electrodes create leads I, II, III, aVR, aVL, and aVF.",
    imageSrc: "/learn/lead-placement/ecg-limb-and-chest-electrodes-placement.png",
    imageAlt: "Diagram showing limb electrode placement for a diagnostic 12-lead ECG",
    points: [
      { key: "RA", label: "RA", color: "#0f766e", swatchClass: "bg-teal-700", note: "Right arm / proximal upper limb / right shoulder" },
      { key: "LA", label: "LA", color: "#0f766e", swatchClass: "bg-teal-700", note: "Left arm / proximal upper limb / left shoulder" },
      { key: "RL", label: "RL", color: "#f59e0b", swatchClass: "bg-amber-500", note: "Right leg / right lower torso / proximal lower limb" },
      { key: "LL", label: "LL", color: "#0284c7", swatchClass: "bg-sky-600", note: "Left leg / left lower torso / proximal lower limb" },
    ],
  },
  "12lead-chest": {
    title: "12-Lead Chest Electrodes (V1–V6)",
    subtitle: "Place V1 to V6 from the sternum outward, keeping V4 to V6 level with each other.",
    footer: "Find V1 and V2 first at the 4th ICS; then place V4 at the 5th ICS midclavicular line; then fill in V3, V5, and V6.",
    imageSrc: "/learn/lead-placement/precordial-leads-3.svg",
    imageAlt: "Diagram showing precordial lead placement (V1–V6) on the chest",
    points: [
      { key: "V1", label: "V1", color: "#dc2626", swatchClass: "bg-red-600", note: "4th intercostal space, right sternal border" },
      { key: "V2", label: "V2", color: "#dc2626", swatchClass: "bg-red-600", note: "4th intercostal space, left sternal border" },
      { key: "V3", label: "V3", color: "#ea580c", swatchClass: "bg-orange-600", note: "Midway between V2 and V4" },
      { key: "V4", label: "V4", color: "#0284c7", swatchClass: "bg-sky-600", note: "5th intercostal space, midclavicular line" },
      { key: "V5", label: "V5", color: "#0284c7", swatchClass: "bg-sky-600", note: "Left anterior axillary line, level with V4" },
      { key: "V6", label: "V6", color: "#0284c7", swatchClass: "bg-sky-600", note: "Left midaxillary line, level with V4" },
    ],
  },
  easi: {
    title: "EASI Placement",
    subtitle: "A reduced-electrode monitoring system that mathematically reconstructs an approximate 12-lead view.",
    footer: "EASI is useful for continuous monitoring, but it is not a substitute for a standard diagnostic 12-lead ECG.",
    imageSrc: "/learn/lead-placement/ecg-limb-and-chest-electrodes-placement.png",
    imageAlt: "Diagram showing EASI electrode placement for derived 12-lead monitoring",
    points: [
      { key: "S", label: "S", color: "#7c3aed", swatchClass: "bg-violet-600", note: "Upper sternum / manubrium" },
      { key: "E", label: "E", color: "#dc2626", swatchClass: "bg-red-600", note: "Lower sternum / xiphoid level" },
      { key: "A", label: "A", color: "#0284c7", swatchClass: "bg-sky-600", note: "Left midaxillary line, level with E" },
      { key: "I", label: "I", color: "#0f766e", swatchClass: "bg-teal-700", note: "Right midaxillary line, level with E" },
      { key: "G", label: "G", color: "#f59e0b", swatchClass: "bg-amber-500", note: "Ground / reference electrode, lower torso" },
    ],
  },
};

export default function LeadPlacementDiagram({ variant }: Props) {
  const config = VARIANTS[variant];

  return (
    <div className="academy-panel my-6 overflow-hidden rounded-3xl">
      <div className="border-b border-[var(--academy-line)] bg-[color:color-mix(in_oklab,var(--academy-brand-soft)_32%,white)] px-5 py-4">
        <p className="academy-heading text-lg font-semibold text-slate-900">{config.title}</p>
        <p className="mt-1 text-sm text-slate-600">{config.subtitle}</p>
      </div>

      <div className="grid gap-6 px-5 py-5 lg:grid-cols-[minmax(0,1.3fr)_minmax(16rem,0.9fr)]">
        <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
          <Image
            src={config.imageSrc}
            alt={config.imageAlt}
            width={640}
            height={480}
            className="h-auto w-full object-contain"
            sizes="(max-width: 768px) 100vw, 50vw"
          />
        </div>

        <div className="space-y-3 self-center">
          {config.points.map((point) => (
            <div key={point.key} className="rounded-2xl border border-slate-200 bg-white/70 px-3 py-2">
              <div className="flex items-center gap-2">
                <span className={`inline-block h-2.5 w-2.5 rounded-full ${point.swatchClass}`} aria-hidden />
                <span className="font-mono text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {point.label}
                </span>
              </div>
              <p className="mt-1 text-sm text-slate-700">{point.note}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="border-t border-[var(--academy-line)] bg-slate-50/80 px-5 py-3 text-sm text-slate-600">
        {config.footer}
      </div>
    </div>
  );
}
