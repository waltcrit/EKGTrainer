#!/usr/bin/env python3
# pyright: basic

"""
PTB-XL EKG Extractor for EKGTrainer
=====================================
Downloads the PTB-XL 12-lead ECG dataset from PhysioNet and selects the
highest-quality matching record for each teaching case. Outputs anonymised
Lead-II strips and standard 12-lead PNGs in the app's house style.

Cases with no PTB-XL match are left untouched — existing synthetic PNGs stay.

Data source
-----------
PTB-XL, a large publicly available electrocardiography dataset.
  Wagner P, Strodthoff N, Bousseljot R-D, et al.
  Scientific Data 7, 154 (2020). https://doi.org/10.1038/s41597-020-0495-6

PhysioNet hosting:
  Goldberger AL, et al. PhysioBank, PhysioToolkit, and PhysioNet.
  Circulation 101(23):e215–e220 (2000). https://doi.org/10.1161/01.CIR.101.23.e215

License: Creative Commons Attribution 4.0 (CC BY 4.0)
  Derived PNG images may be redistributed with appropriate attribution.

Usage
-----
    cd EKGTrainer/scripts
    pip install -r requirements.txt
    python3 generate_ptbxl_ekgs.py               # auto-downloads ~2.5 GB
    python3 generate_ptbxl_ekgs.py --data-dir ~/ptb-xl-1.0.3/  # existing copy
    python3 generate_ptbxl_ekgs.py --list-codes  # show available SCP codes
"""

import argparse
import ast
import sys
import warnings
from pathlib import Path
from typing import Any, cast

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

warnings.filterwarnings('ignore')

# ── optional deps ──────────────────────────────────────────────────────────────
try:
    import wfdb
except ImportError:
    sys.exit("Install wfdb first:  pip install wfdb")

try:
    import pandas as pd
except ImportError:
    sys.exit("Install pandas first:  pip install pandas")

try:
    from scipy.signal import butter, filtfilt
    _SCIPY = True
except ImportError:
    _SCIPY = False
    print("⚠  scipy not found — signals won't be bandpass-filtered (pip install scipy)")

# ── paths ──────────────────────────────────────────────────────────────────────
ROOT             = Path(__file__).parent.parent
OUT_DIR          = ROOT / "web" / "public" / "cases"
DATA_DIR_DEFAULT = Path(__file__).parent / "ptbxl_data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── rendering constants (match house style) ────────────────────────────────────
BG, MINOR, MAJOR, TRACE = "#FFF5E6", "#FFBBBB", "#EE6666", "#111111"

FS  = 500           # PTB-XL high-res sample rate
DUR = 10.0          # seconds per record
N   = int(FS * DUR) # 5000 samples
T   = np.linspace(0, DUR, N)

# PTB-XL lead storage order (matches our 12-lead layout)
PTBXL_LEAD_ORDER = ["I","II","III","aVR","aVL","aVF","V1","V2","V3","V4","V5","V6"]
LEAD_IDX = {ld: i for i, ld in enumerate(PTBXL_LEAD_ORDER)}

LAYOUT = [
    [("I",0),   ("aVR",1), ("V1",2), ("V4",3)],
    [("II",0),  ("aVL",1), ("V2",2), ("V5",3)],
    [("III",0), ("aVF",1), ("V3",2), ("V6",3)],
]
COL_W = 2.5  # seconds per column in 12-lead grid


# ══════════════════════════════════════════════════════════════════════════════
# Signal conditioning
# ══════════════════════════════════════════════════════════════════════════════

def bandpass(sig: np.ndarray, low=0.5, high=40.0) -> np.ndarray:
    """Zero-phase Butterworth bandpass (0.5–40 Hz), applied column-wise."""
    if not _SCIPY:
        return sig
    nyq = FS / 2
    ba = butter(3, [low / nyq, high / nyq], btype='band', output='ba')
    if ba is None:
        return sig
    b, a = cast(tuple[np.ndarray, np.ndarray], ba)
    return filtfilt(b, a, sig, axis=0)


def get_lead(sig: np.ndarray, lead: str) -> np.ndarray:
    return sig[:, LEAD_IDX[lead]]


def lead_ylim(arr: np.ndarray, pad=0.12) -> tuple:
    """Adaptive y-limits that respect standard EKG scale but clip outliers."""
    p1, p99 = np.percentile(arr, [1, 99])
    lo = min(-0.5, p1 - pad)
    hi = max(1.4, p99 + pad)
    return lo, hi


# ══════════════════════════════════════════════════════════════════════════════
# Metadata helpers
# ══════════════════════════════════════════════════════════════════════════════

def load_df(data_dir: Path) -> "pd.DataFrame":
    csv = data_dir / "ptbxl_database.csv"
    if not csv.exists():
        sys.exit(
            f"PTB-XL database CSV not found at {csv}\n"
            f"Run with --data-dir pointing to an existing copy, or let the\n"
            f"script download it automatically (omit --data-dir)."
        )
    df = pd.read_csv(csv, index_col="ecg_id")
    df["scp_codes"] = df["scp_codes"].apply(ast.literal_eval)
    return df


def has_any(scp: dict, codes: list, min_conf: float = 50.0) -> bool:
    return any(scp.get(c, 0.0) >= min_conf for c in codes)


def max_conf(scp: dict, codes: list) -> float:
    return max((scp.get(c, 0.0) for c in codes), default=0.0)


def quality_score(row) -> float:
    """Higher = better quality record."""
    s = float(bool(row.get("validated_by_human", False))) * 8.0
    for field in ("baseline_drift", "static_noise", "burst_noise", "electrodes_problems"):
        v = row.get(field, 0) or 0
        s += max(0.0, (3.0 - float(v)) * 1.5)  # 0=clean → +4.5; 3=bad → 0
    return s


# ══════════════════════════════════════════════════════════════════════════════
# Case → PTB-XL SCP-code mapping
# ══════════════════════════════════════════════════════════════════════════════
#
# PTB-XL SCP codes reference (scp_statements.csv in the dataset):
#   Rhythm:  NORM SBRAD STACH SARRH AFIB AFLT SVTACH PACE BIGU TRIGU VT VF
#   Blocks:  1AVB 2AVB 3AVB LBBB RBBB IRBBB WPW LAFB LPFB
#   Infarct: AMI ALMI ILMI IMI IPLMI IPMI LMI PMI
#   Injury:  INJANT INJIN INJLA INJIL
#   Ischem:  ISCAN ISCAL ISCIN ISCIL ISCLA ISCLR
#   Hypert:  LVH RVH LAE RAE
#   Other:   BRGADA NDT NST_ DIG EL LNGQT SVPB VPB SVARR
#
# Format: (primary_codes, exclude_codes)
# A record matches if ANY primary code has confidence ≥ 50
# and NO exclude code has confidence ≥ 70.

QUERIES: dict = {
    "nsr_01":          (["NORM"],                   ["AFIB","AFLT","1AVB","2AVB","3AVB","LBBB","RBBB","WPW"]),
    "nsr_02":          (["NORM"],                   ["AFIB","AFLT","1AVB","2AVB","3AVB","LBBB","RBBB","WPW"]),
    "brady_01":        (["SBRAD"],                  []),
    "brady_02":        (["SBRAD"],                  []),
    "tachy_01":        (["STACH"],                  ["AFIB","AFLT","SVTACH"]),
    "tachy_02":        (["STACH"],                  ["AFIB","AFLT","SVTACH"]),
    "sarr_01":         (["SARRH"],                  []),
    "pac_01":          (["SVPB"],                   ["AFIB"]),
    "pvc_01":          (["VPB"],                    ["AFIB","BIGU"]),
    "svt_01":          (["SVTACH","PSVT"],          ["AFIB","AFLT"]),
    "afib_01":         (["AFIB"],                   ["PACE","3AVB"]),
    "afib_02":         (["AFIB"],                   ["PACE","3AVB"]),
    "aflut_01":        (["AFLT"],                   []),
    "avb1_01":         (["1AVB"],                   ["2AVB","3AVB","LBBB","RBBB"]),
    "avb2m1_01":       (["2AVB"],                   ["3AVB"]),   # Wenckebach — see keyword filter
    "avb2m2_01":       (["2AVB"],                   ["3AVB"]),   # Mobitz II
    "avb3_01":         (["3AVB"],                   []),
    "lbbb_01":         (["LBBB"],                   ["RBBB","PACE"]),
    "rbbb_01":         (["RBBB"],                   ["LBBB","PACE"]),
    "junct_01":        (["SVTACH"],                 ["AFIB","AFLT","STACH"]),
    "junct_02":        (["SVTACH"],                 ["AFIB","AFLT"]),
    "idio_01":         (["3AVB"],                   []),   # best proxy: slow escape rhythm in 3AVB
    "vtach_01":        (["VT"],                     []),
    "vtach_02":        (["VT"],                     []),
    "vfib_01":         (["VF"],                     []),
    "asys_01":         (["ASYS"],                   []),
    "stemi_ant_01":    (["AMI","ALMI","INJANT","ISCAN"],  []),
    "stemi_inf_01":    (["IMI","ILMI","INJIN","ISCIN"],   []),
    "stemi_lat_01":    (["LMI","ISCAL","INJLA"],          []),
    "stemi_post_01":   (["PMI","IPLMI","IPMI","INJIL"],   []),
    "nstemi_01":       (["NSTEMI","NST_"],                []),
    "wellens_a_01":    (["NDT"],                    ["LBBB","RBBB","LVH","AFIB"]),
    "wellens_b_01":    (["NDT"],                    ["LBBB","RBBB","LVH","AFIB"]),
    "pe_s1q3t3_01":    (["RVH","STACH"],            []),
    "pe_rv_strain_01": (["RVH"],                    []),
    "lv_strain_01":    (["LVH"],                    []),
    "rv_strain_01":    (["RVH"],                    []),
    "brugada_01":         (["BRGADA"],                 []),
    "pace_atrial_01":     (["PACE"],                   []),
    "pace_ventricular_01":(["PACE"],                   []),
    "pace_av_01":         (["PACE"],                   []),
}

# Keywords used to differentiate Mobitz I from II via report text
_WENCKEBACH = ["wenckebach","mobitz i","mobitz 1","type i","type 1","periodically"]
_MOBITZ2    = ["mobitz ii","mobitz 2","type ii","type 2","fixed pr","constant pr"]

# Cases sharing the same primary code — ensure different records are chosen
DEDUP_GROUPS = [
    ["nsr_01","nsr_02"],
    ["brady_01","brady_02"],
    ["tachy_01","tachy_02"],
    ["afib_01","afib_02"],
    ["vtach_01","vtach_02"],
    ["junct_01","junct_02"],
    ["wellens_a_01","wellens_b_01"],
    ["lv_strain_01","rv_strain_01","pe_s1q3t3_01","pe_rv_strain_01"],
    ["pace_atrial_01","pace_ventricular_01","pace_av_01"],
]


# ══════════════════════════════════════════════════════════════════════════════
# Record selection
# ══════════════════════════════════════════════════════════════════════════════

def find_record(
    df: "pd.DataFrame",
    case_id: str,
    used_ids: set,
    data_dir: Path,
) -> tuple:
    """
    Return (ecg_id, signal_ndarray_5000x12) for the best matching PTB-XL record,
    or (None, None) if no suitable record found.
    """
    primary, exclude = QUERIES[case_id]

    # Primary code match
    mask = df["scp_codes"].apply(lambda d: has_any(d, primary, 50.0))
    # Exclude unwanted codes
    if exclude:
        mask &= ~df["scp_codes"].apply(lambda d: has_any(d, exclude, 70.0))
    # Skip already-used records
    mask &= ~df.index.isin(used_ids)

    candidates = df[mask].copy()
    if candidates.empty:
        return None, None

    # Differentiate Wenckebach vs Mobitz II using report text
    if "report" in candidates.columns:
        if case_id == "avb2m1_01":
            w = candidates["report"].fillna("").str.lower().apply(
                lambda r: any(k in r for k in _WENCKEBACH))
            if w.any():
                candidates = candidates[w]
        elif case_id == "avb2m2_01":
            m = candidates["report"].fillna("").str.lower().apply(
                lambda r: any(k in r for k in _MOBITZ2))
            if m.any():
                candidates = candidates[m]

    # Score and rank
    candidates = candidates.copy()
    candidates["_conf"]  = candidates["scp_codes"].apply(lambda d: max_conf(d, primary))
    candidates["_qual"]  = candidates.apply(quality_score, axis=1)
    candidates["_total"] = candidates["_conf"] + candidates["_qual"]
    candidates = candidates.sort_values("_total", ascending=False)

    # Try records in ranked order until one reads cleanly
    for ecg_id, row in candidates.iterrows():
        try:
            fname = str(row["filename_hr"]).lstrip("./")
            record = wfdb.rdrecord(str(data_dir / fname))
            sig = getattr(record, "p_signal", None)  # (5000, 12) mV
            if sig is None or sig.shape != (N, 12):
                continue
            if np.any(np.isnan(sig)) or np.any(np.isinf(sig)):
                continue
            return int(cast(Any, ecg_id)), sig
        except Exception:
            continue

    return None, None


# ══════════════════════════════════════════════════════════════════════════════
# Renderers — identical style to the synthetic generators
# ══════════════════════════════════════════════════════════════════════════════

def _style_ax(ax, label: str, xlim: tuple, ylim: tuple):
    ax.set_facecolor(BG)
    ax.set_xticks(np.arange(0, xlim[1] + 0.04, 0.04), minor=True)
    ax.set_yticks(np.arange(ylim[0], ylim[1] + 0.10, 0.10), minor=True)
    ax.set_xticks(np.arange(0, xlim[1] + 0.20, 0.20))
    ax.set_yticks(np.arange(ylim[0], ylim[1] + 0.50, 0.50))
    ax.grid(True, which='minor', color=MINOR, linewidth=0.28, zorder=1)
    ax.grid(True, which='major', color=MAJOR, linewidth=0.65, zorder=2)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.tick_params(which='both', bottom=False, left=False,
                   labelbottom=False, labelleft=False)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.text(0.02, 0.96, label, transform=ax.transAxes,
            fontsize=7.5, fontweight='bold', va='top', color='#1a1a1a', zorder=5)


def render_strip(sig: np.ndarray, out_path: Path):
    """Lead II rhythm strip — matches generate_cases.py render() style."""
    lead_ii = get_lead(sig, "II")
    lo, hi = lead_ylim(lead_ii)

    fig, ax = plt.subplots(figsize=(12, 2.4), dpi=150)
    fig.patch.set_facecolor(BG)
    _style_ax(ax, "II", xlim=(0, DUR), ylim=(lo, hi))
    ax.plot(T, lead_ii, color=TRACE, linewidth=1.2, zorder=3, antialiased=True)
    ax.text(0.99, 0.97, '25 mm/s  |  10 mm/mV  |  Lead II',
            transform=ax.transAxes, fontsize=6.5, ha='right', va='top', color='#888888')

    plt.tight_layout(pad=0.2)
    plt.savefig(out_path, bbox_inches='tight', facecolor=BG)
    plt.close(fig)


def render_12lead(sig: np.ndarray, out_path: Path):
    """Standard 4×3+strip 12-lead — anonymised (no rhythm title in image)."""
    fig = plt.figure(figsize=(11, 8.5), dpi=150)
    fig.patch.set_facecolor(BG)

    gs = fig.add_gridspec(
        4, 4,
        height_ratios=[1, 1, 1, 0.75],
        hspace=0.06, wspace=0.04,
        left=0.02, right=0.98, top=0.96, bottom=0.03,
    )

    for row_i, row in enumerate(LAYOUT):
        for col_i, (lead, _) in enumerate(row):
            ax  = fig.add_subplot(gs[row_i, col_i])
            n0  = int(col_i * COL_W * FS)
            n1  = int((col_i + 1) * COL_W * FS)
            arr = get_lead(sig, lead)[n0:n1]
            t_w = T[n0:n1] - col_i * COL_W
            _style_ax(ax, lead, xlim=(0, COL_W), ylim=lead_ylim(arr))
            ax.plot(t_w, arr, color=TRACE, lw=1.05, zorder=3, antialiased=True)

    # Rhythm strip — Lead II full width
    ax_strip = fig.add_subplot(gs[3, :])
    lead_ii  = get_lead(sig, "II")
    _style_ax(ax_strip, "II (rhythm strip)", xlim=(0, DUR), ylim=lead_ylim(lead_ii))
    ax_strip.plot(T, lead_ii, color=TRACE, lw=1.05, zorder=3, antialiased=True)

    # Calibration only (anonymised — no diagnosis title)
    fig.text(0.985, 0.985, '25 mm/s  ·  10 mm/mV', fontsize=6.5,
             ha='right', va='top', color='#888888')

    plt.savefig(out_path, dpi=150, bbox_inches='tight', facecolor=BG)
    plt.close(fig)


# ══════════════════════════════════════════════════════════════════════════════
# Download helper
# ══════════════════════════════════════════════════════════════════════════════

def download_ptbxl(data_dir: Path):
    print(f"\nDownloading PTB-XL to {data_dir}")
    print("  This is ~2.5 GB and may take several minutes...\n")
    data_dir.mkdir(parents=True, exist_ok=True)
    wfdb.dl_database('ptb-xl', str(data_dir))
    print("\n  Download complete.")


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--data-dir', type=Path, default=DATA_DIR_DEFAULT,
                        help='Path to PTB-XL directory (default: ./ptbxl_data/)')
    parser.add_argument('--download', action='store_true',
                        help='Force re-download even if data already exists')
    parser.add_argument('--list-codes', action='store_true',
                        help='Print all SCP codes present in the dataset and exit')
    args = parser.parse_args()
    data_dir = args.data_dir

    # Download if needed
    if args.download or not (data_dir / "ptbxl_database.csv").exists():
        download_ptbxl(data_dir)

    print(f"\nLoading PTB-XL metadata from {data_dir}...")
    df = load_df(data_dir)
    print(f"  {len(df):,} records loaded.")

    if args.list_codes:
        all_codes: dict = {}
        for scp in df["scp_codes"]:
            for code, conf in scp.items():
                all_codes[code] = all_codes.get(code, 0) + 1
        print(f"\n{'Code':<12} {'Records':>8}")
        print("─" * 22)
        for code, count in sorted(all_codes.items(), key=lambda x: -x[1]):
            print(f"  {code:<10} {count:>8,}")
        return

    # Build dedup sets so paired cases get distinct records
    # Cases in the same group are processed together, each taking the next-best record
    processed_order = list(QUERIES.keys())

    used_ids: set = set()
    successes: list = []
    failures:  list = []

    print(f"\nProcessing {len(processed_order)} cases → {OUT_DIR}\n")

    for case_id in processed_order:
        ecg_id, raw_sig = find_record(df, case_id, used_ids, data_dir)

        if ecg_id is None:
            print(f"  ✗  {case_id:<24}  no PTB-XL match — synthetic PNG unchanged")
            failures.append(case_id)
            continue

        used_ids.add(ecg_id)
        sig = bandpass(raw_sig)

        render_strip( sig, OUT_DIR / f"{case_id}.png")
        render_12lead(sig, OUT_DIR / f"{case_id}_12lead.png")

        scp_codes = df.loc[ecg_id, "scp_codes"]
        scp_items = scp_codes.items() if isinstance(scp_codes, dict) else []
        codes_str = ", ".join(
            f"{k}({v:.0f})"
            for k, v in sorted(scp_items, key=lambda x: -x[1])
            if v >= 50
        )
        print(f"  ✓  {case_id:<24}  ECG {ecg_id:6d}  [{codes_str}]")
        successes.append(case_id)

    print(f"\n{'─'*65}")
    print(f"Done: {len(successes)} replaced with PTB-XL real data, "
          f"{len(failures)} kept synthetic.")
    if failures:
        print(f"\nNo PTB-XL match for: {', '.join(failures)}")
        print("(Those cases retain their synthesized PNGs as fallback.)")
    print(f"\nAttribution reminder: derived PNG images use PTB-XL data")
    print(f"(CC BY 4.0). Ensure the app includes the required citation.")


if __name__ == "__main__":
    main()
