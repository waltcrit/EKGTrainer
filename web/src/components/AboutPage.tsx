"use client";

export default function AboutPage() {
  return (
    <div className="max-w-2xl mx-auto flex flex-col gap-6 pb-8">

      {/* ── App overview ─────────────────────────────────────────────────── */}
      <div className="academy-panel rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-[var(--academy-line)]">
          <p className="academy-heading text-xs font-semibold tracking-[0.22em] text-[var(--academy-muted)] uppercase">About</p>
        </div>
        <div className="px-5 py-4 flex flex-col gap-3">
          <p className="text-sm text-[var(--academy-ink)] leading-relaxed">
            EKG Academy is an educational tool for learning systematic ECG interpretation. It
            presents rhythm strips and 12-lead tracings in quiz and reference modes, backed by
            AI-powered analysis using Claude. It is intended for medical students,
            residents, nurses, and paramedics — not for clinical diagnosis.
          </p>
          <p className="text-sm text-[var(--academy-ink)] leading-relaxed">
            The systematic framework used throughout follows the standard 10-step approach: confirm
            basics, rate, rhythm, P waves, PR interval, QRS complex, ST segments and T waves, QT
            interval, compare with prior, and synthesize.
          </p>
          <p className="text-sm text-[var(--academy-ink)] leading-relaxed">
            ECG analysis uses a signal processing pipeline: uploaded images are digitized to
            extract waveform data, then BioSPPy measures intervals and detects features
            algorithmically. These measurements are passed to Claude, which provides the
            plain-language interpretation. This approach is significantly more accurate than
            pure image-based AI analysis.
          </p>
        </div>
      </div>

      {/* ── Data attribution ─────────────────────────────────────────────── */}
      <div className="academy-panel rounded-xl border-teal-100 bg-teal-50/70 overflow-hidden">
        <div className="px-5 py-4 border-b border-teal-100">
          <p className="academy-heading text-xs font-semibold tracking-[0.2em] text-teal-700 uppercase">
            Data Attribution
          </p>
        </div>
        <div className="px-5 py-4 flex flex-col gap-4">
          <p className="text-sm text-[var(--academy-ink)] leading-relaxed">
            ECG recordings used in this app are derived from the{" "}
            <strong>PTB-XL ECG dataset</strong>, a large publicly available 12-lead ECG database.
          </p>

          {/* Primary citation */}
          <div className="rounded-lg bg-white/95 border border-teal-100 px-4 py-3 flex flex-col gap-1">
            <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--academy-muted)] mb-1">
              Dataset Citation
            </p>
            <p className="text-xs text-[var(--academy-ink)] leading-relaxed">
              Wagner P, Strodthoff N, Bousseljot R-D, Kreiseler D, Lunze FI, Samek W, Schaeffter T.
              PTB-XL, a large publicly available electrocardiography dataset.{" "}
              <em>Scientific Data</em> 7, 154 (2020).{" "}
              <a
                href="https://doi.org/10.1038/s41597-020-0495-6"
                target="_blank"
                rel="noopener noreferrer"
                className="text-teal-700 hover:text-teal-900 underline underline-offset-2"
              >
                doi:10.1038/s41597-020-0495-6
              </a>
            </p>
          </div>

          {/* PhysioNet citation */}
          <div className="rounded-lg bg-white/95 border border-teal-100 px-4 py-3 flex flex-col gap-1">
            <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--academy-muted)] mb-1">
              PhysioNet Citation
            </p>
            <p className="text-xs text-[var(--academy-ink)] leading-relaxed">
              Goldberger AL, Amaral LAN, Glass L, Hausdorff JM, Ivanov PCh, Mark RG, Mietus JE,
              Moody GB, Peng C-K, Stanley HE. PhysioBank, PhysioToolkit, and PhysioNet: Components
              of a New Research Resource for Complex Physiologic Signals.{" "}
              <em>Circulation</em> 101(23): e215–e220 (2000).{" "}
              <a
                href="https://doi.org/10.1161/01.CIR.101.23.e215"
                target="_blank"
                rel="noopener noreferrer"
                className="text-teal-700 hover:text-teal-900 underline underline-offset-2"
              >
                doi:10.1161/01.CIR.101.23.e215
              </a>
            </p>
          </div>

          {/* License */}
          <div className="flex items-start gap-3 rounded-lg bg-white/95 border border-teal-100 px-4 py-3">
            <svg className="w-4 h-4 text-teal-500 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
            </svg>
            <p className="text-xs text-[var(--academy-ink)] leading-relaxed">
              PTB-XL is licensed under{" "}
              <a
                href="https://creativecommons.org/licenses/by/4.0/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-teal-700 hover:text-teal-900 underline underline-offset-2"
              >
                Creative Commons Attribution 4.0 (CC BY 4.0)
              </a>
              . Derived ECG images in this app are used and distributed in compliance with that license.
            </p>
          </div>
        </div>
      </div>

      {/* ── Software credits ─────────────────────────────────────────────── */}
      <div className="academy-panel rounded-xl border-emerald-100 bg-emerald-50/70 overflow-hidden">
        <div className="px-5 py-4 border-b border-emerald-100">
          <p className="academy-heading text-xs font-semibold tracking-[0.2em] text-emerald-700 uppercase">
            Analysis Software
          </p>
        </div>
        <div className="px-5 py-4 flex flex-col gap-3">

          {/* BioSPPy */}
          <div className="rounded-lg bg-white/95 border border-emerald-100 px-4 py-3 flex flex-col gap-1">
            <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--academy-muted)] mb-1">
              BioSPPy — Signal Processing
            </p>
            <p className="text-xs text-[var(--academy-ink)] leading-relaxed">
              Carreiras C, Alves AP, Lourenço A, Canento F, Silva H, Fred A, et al.
              BioSPPy: Biosignal Processing in Python. 2015.{" "}
              <a
                href="https://github.com/PIA-Group/BioSPPy"
                target="_blank"
                rel="noopener noreferrer"
                className="text-emerald-700 hover:text-emerald-900 underline underline-offset-2"
              >
                github.com/PIA-Group/BioSPPy
              </a>
            </p>
            <p className="text-xs text-[var(--academy-muted)] leading-relaxed">
              Used for R-peak detection, RR interval measurement, QRS width estimation,
              and rhythm regularity classification.
            </p>
          </div>

          {/* ECG-Digitiser */}
          <div className="rounded-lg bg-white/95 border border-emerald-100 px-4 py-3 flex flex-col gap-1">
            <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--academy-muted)] mb-1">
              ECG-Digitiser — Image Digitization
            </p>
            <p className="text-xs text-[var(--academy-ink)] leading-relaxed">
              Krones F. ECG-Digitiser. Winner, George B. Moody PhysioNet Challenge 2024:
              Digitization and Classification of ECG Images. 2024.{" "}
              <a
                href="https://github.com/felixkrones/ECG-Digitiser"
                target="_blank"
                rel="noopener noreferrer"
                className="text-emerald-700 hover:text-emerald-900 underline underline-offset-2"
              >
                github.com/felixkrones/ECG-Digitiser
              </a>
            </p>
            <p className="text-xs text-[var(--academy-muted)] leading-relaxed">
              Used to convert uploaded ECG images to digital waveforms prior to signal analysis.
            </p>
          </div>

          {/* PhysioNet Challenge */}
          <div className="rounded-lg bg-white/95 border border-emerald-100 px-4 py-3 flex flex-col gap-1">
            <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--academy-muted)] mb-1">
              George B. Moody PhysioNet Challenge 2024
            </p>
            <p className="text-xs text-[var(--academy-ink)] leading-relaxed">
              Reyna MA, Deepanshi, Weigle J, Kiyasseh D, Elola A, Rad AB, Seyedi S,
              McDonald A, Clifford GD, Sameni R. Digitization and Classification of ECG Images:
              The PhysioNet/Computing in Cardiology Challenge 2024.{" "}
              <a
                href="https://moody-challenge.physionet.org/2024/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-emerald-700 hover:text-emerald-900 underline underline-offset-2"
              >
                moody-challenge.physionet.org/2024
              </a>
            </p>
          </div>

          {/* Claude / Anthropic */}
          <div className="rounded-lg bg-white/95 border border-emerald-100 px-4 py-3 flex flex-col gap-1">
            <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--academy-muted)] mb-1">
              Claude — AI Interpretation
            </p>
            <p className="text-xs text-[var(--academy-ink)] leading-relaxed">
              Anthropic. Claude (claude-haiku-4-5). 2024.{" "}
              <a
                href="https://www.anthropic.com"
                target="_blank"
                rel="noopener noreferrer"
                className="text-emerald-700 hover:text-emerald-900 underline underline-offset-2"
              >
                anthropic.com
              </a>
            </p>
            <p className="text-xs text-[var(--academy-muted)] leading-relaxed">
              Provides plain-language rhythm interpretation guided by signal-derived measurements.
            </p>
          </div>

        </div>
      </div>

      {/* ── Disclaimer ───────────────────────────────────────────────────── */}
      <div className="rounded-xl border border-amber-200 bg-amber-50 px-5 py-4 flex items-start gap-3">
        <svg className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
        </svg>
        <div className="flex flex-col gap-1">
          <p className="text-xs font-semibold text-amber-800">Educational use only</p>
          <p className="text-xs text-amber-700 leading-relaxed">
            This application is intended solely for educational purposes. It is not a medical
            device and must not be used for clinical diagnosis, patient care, or any other
            clinical decision-making. AI-generated analysis is provided for learning purposes only
            and may be incorrect.
          </p>
        </div>
      </div>

    </div>
  );
}
