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
import json
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
SEGMENT_PAD = 0.012  # keep trace slightly off the boundary to avoid false continuity

RENDER_STYLES: dict[str, dict[str, float | str]] = {
    "house": {
        "bg": BG,
        "minor": MINOR,
        "major": MAJOR,
        "trace": TRACE,
        "label": "#1a1a1a",
        "calib": "#888888",
        "segment_pad": SEGMENT_PAD,
    },
    # PhysioNet-like neutral paper/grid tones for easier visual comparison.
    "physionet": {
        "bg": "#ffffff",
        "minor": "#e3e3e3",
        "major": "#bdbdbd",
        "trace": "#111111",
        "label": "#111111",
        "calib": "#666666",
        "segment_pad": 0.0,
    },
}


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


def shared_ylim(sig: np.ndarray, pad=0.15) -> tuple:
    """Shared zero-centered limits for continuous 12-lead rows."""
    q = np.percentile(np.abs(sig), 99.5)
    amp = float(np.clip(q + pad, 1.2, 3.0))
    return -amp, amp


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


def load_df_remote() -> "pd.DataFrame":
    """Load PTB-XL metadata directly from PhysioNet without local download."""
    csv_url = "https://physionet.org/files/ptb-xl/1.0.3/ptbxl_database.csv?download"
    df = pd.read_csv(csv_url, index_col="ecg_id")
    df["scp_codes"] = df["scp_codes"].apply(ast.literal_eval)
    return df


def has_any(scp: dict, codes: list, min_conf: float = 50.0) -> bool:
    return any(scp.get(c, 0.0) >= min_conf for c in codes)


def max_conf(scp: dict, codes: list) -> float:
    return max((scp.get(c, 0.0) for c in codes), default=0.0)


def quality_score(row) -> float:
    """Higher = better quality record."""
    def _num(v: object, default: float = 0.0) -> float:
        try:
            if v is None:
                return default
            return float(pd.to_numeric(v, errors="coerce"))
        except Exception:
            return default

    s = float(bool(row.get("validated_by_human", False))) * 8.0
    for field in ("baseline_drift", "static_noise", "burst_noise", "electrodes_problems"):
        v = _num(row.get(field, 0), default=0.0)
        s += max(0.0, (3.0 - v) * 1.5)  # 0=clean → +4.5; 3=bad → 0
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
    "wpw_01":             (["WPW"],                    []),
    "lngqt_01":           (["LNGQT"],                  []),
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
    remote: bool = False,
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
            if remote:
                fpath = Path(fname)
                record = wfdb.rdrecord(
                    fpath.name,
                    pn_dir=f"ptb-xl/1.0.3/{fpath.parent.as_posix()}",
                )
            else:
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


def rank_candidates(
    df: "pd.DataFrame",
    case_id: str,
    used_ids: set,
) -> "pd.DataFrame":
    """Return ranked candidate rows for a case before signal loading."""
    primary, exclude = QUERIES[case_id]

    mask = df["scp_codes"].apply(lambda d: has_any(d, primary, 50.0))
    if exclude:
        mask &= ~df["scp_codes"].apply(lambda d: has_any(d, exclude, 70.0))
    mask &= ~df.index.isin(used_ids)

    candidates = df[mask].copy()
    if candidates.empty:
        return candidates

    if "report" in candidates.columns:
        if case_id == "avb2m1_01":
            w = candidates["report"].fillna("").str.lower().apply(
                lambda r: any(k in r for k in _WENCKEBACH)
            )
            if w.any():
                candidates = candidates[w]
        elif case_id == "avb2m2_01":
            m = candidates["report"].fillna("").str.lower().apply(
                lambda r: any(k in r for k in _MOBITZ2)
            )
            if m.any():
                candidates = candidates[m]

    candidates = candidates.copy()
    candidates["_conf"] = candidates["scp_codes"].apply(lambda d: max_conf(d, primary))
    candidates["_qual"] = candidates.apply(quality_score, axis=1)
    candidates["_total"] = candidates["_conf"] + candidates["_qual"]
    return candidates.sort_values("_total", ascending=False)


def load_candidate_signal(row: "pd.Series", data_dir: Path, remote: bool) -> np.ndarray | None:
    """Load and validate one candidate ECG signal."""
    try:
        fname = str(row["filename_hr"]).lstrip("./")
        if remote:
            fpath = Path(fname)
            record = wfdb.rdrecord(
                fpath.name,
                pn_dir=f"ptb-xl/1.0.3/{fpath.parent.as_posix()}",
            )
        else:
            record = wfdb.rdrecord(str(data_dir / fname))
        sig = getattr(record, "p_signal", None)
        if sig is None or sig.shape != (N, 12):
            return None
        if np.any(np.isnan(sig)) or np.any(np.isinf(sig)):
            return None
        return sig
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
# Renderers — identical style to the synthetic generators
# ══════════════════════════════════════════════════════════════════════════════

def _style_ax(ax, label: str, xlim: tuple, ylim: tuple, *,
              bg: str = BG,
              minor: str = MINOR,
              major: str = MAJOR,
              label_color: str = '#1a1a1a'):
    ax.set_facecolor(bg)
    major_x = np.arange(0, xlim[1] + 1e-9, 0.20)
    minor_x = np.arange(0, xlim[1] + 1e-9, 0.04)
    minor_x = minor_x[np.abs((minor_x / 0.20) - np.round(minor_x / 0.20)) > 1e-9]
    major_y = np.arange(ylim[0], ylim[1] + 1e-9, 0.50)
    minor_y = np.arange(ylim[0], ylim[1] + 1e-9, 0.10)
    minor_y = minor_y[np.abs((minor_y / 0.50) - np.round(minor_y / 0.50)) > 1e-9]
    ax.set_xticks(minor_x, minor=True)
    ax.set_yticks(minor_y, minor=True)
    ax.set_xticks(major_x)
    ax.set_yticks(major_y)
    ax.grid(True, which='minor', color=minor, linewidth=0.28, zorder=1)
    ax.grid(True, which='major', color=major, linewidth=0.65, zorder=2)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.tick_params(which='both', bottom=False, left=False,
                   labelbottom=False, labelleft=False)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.text(0.02, 0.96, label, transform=ax.transAxes,
            fontsize=7.5, fontweight='bold', va='top', color=label_color, zorder=5)


def _get_style(style_name: str) -> dict[str, float | str]:
    style = RENDER_STYLES.get(style_name)
    if style is None:
        raise ValueError(
            f"Unknown render style '{style_name}'. "
            f"Choose one of: {', '.join(sorted(RENDER_STYLES))}."
        )
    return style


def render_strip(sig: np.ndarray, out_path: Path, render_style: str = "house"):
    """Lead II rhythm strip — matches generate_cases.py render() style."""
    style = _get_style(render_style)
    lead_ii = get_lead(sig, "II")
    lo, hi = lead_ylim(lead_ii)

    fig, ax = plt.subplots(figsize=(12, 2.4), dpi=150)
    fig.patch.set_facecolor(str(style["bg"]))
    _style_ax(ax, "II", xlim=(0, DUR), ylim=(lo, hi),
              bg=str(style["bg"]),
              minor=str(style["minor"]),
              major=str(style["major"]),
              label_color=str(style["label"]))
    ax.plot(T, lead_ii, color=str(style["trace"]), linewidth=1.2, zorder=3, antialiased=True)
    ax.text(0.99, 0.97, '25 mm/s  |  10 mm/mV  |  Lead II',
            transform=ax.transAxes, fontsize=6.5, ha='right', va='top', color=str(style["calib"]))

    plt.tight_layout(pad=0.2)
    plt.savefig(out_path, bbox_inches='tight', facecolor=str(style["bg"]))
    plt.close(fig)


def render_12lead(sig: np.ndarray, out_path: Path, render_style: str = "house"):
    """Standard 4×3+strip 12-lead on continuous row grids."""
    style = _get_style(render_style)
    segment_pad = float(style["segment_pad"])

    fig = plt.figure(figsize=(11, 8.5), dpi=150)
    fig.patch.set_facecolor(str(style["bg"]))

    gs = fig.add_gridspec(
        4, 1,
        height_ratios=[1, 1, 1, 0.75],
        hspace=0.05,
        left=0.02, right=0.98, top=0.96, bottom=0.03,
    )

    ylim = shared_ylim(sig)

    for row_i, row in enumerate(LAYOUT):
        ax = fig.add_subplot(gs[row_i, 0])
        _style_ax(ax, "", xlim=(0, DUR), ylim=ylim,
                  bg=str(style["bg"]),
                  minor=str(style["minor"]),
                  major=str(style["major"]),
                  label_color=str(style["label"]))

        for col_i, (lead, _) in enumerate(row):
            n0  = int(col_i * COL_W * FS)
            n1  = int((col_i + 1) * COL_W * FS)
            pad_n = int(segment_pad * FS)
            seg_n0 = min(n1, n0 + pad_n)
            seg_n1 = max(seg_n0, n1 - pad_n)
            arr = get_lead(sig, lead)[seg_n0:seg_n1]
            t_w = T[seg_n0:seg_n1]
            ax.plot(t_w, arr, color=str(style["trace"]), lw=1.05, zorder=3, antialiased=True)
            ax.text(col_i * COL_W + 0.04, ylim[1] - 0.08, lead,
                    fontsize=7.5, fontweight='bold', va='top',
                    color=str(style["label"]), zorder=5)

    # Rhythm strip — Lead II full width
    ax_strip = fig.add_subplot(gs[3, 0])
    lead_ii  = get_lead(sig, "II")
    _style_ax(ax_strip, "II (rhythm strip)", xlim=(0, DUR), ylim=ylim,
              bg=str(style["bg"]),
              minor=str(style["minor"]),
              major=str(style["major"]),
              label_color=str(style["label"]))
    ax_strip.plot(T, lead_ii, color=str(style["trace"]), lw=1.05, zorder=3, antialiased=True)

    # Calibration only (anonymised — no diagnosis title)
    fig.text(0.985, 0.985, '25 mm/s  ·  10 mm/mV', fontsize=6.5,
             ha='right', va='top', color=str(style["calib"]))

    plt.savefig(out_path, dpi=150, bbox_inches='tight', facecolor=str(style["bg"]))
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
    parser.add_argument('--cases', type=str, default='',
                        help='Comma-separated case IDs to process (default: all)')
    parser.add_argument('--remote', action='store_true',
                        help='Read PTB-XL directly from PhysioNet (no local download)')
    parser.add_argument('--max-candidates', type=int, default=1,
                        help='Generate up to N ranked candidates per case (default: 1)')
    parser.add_argument('--render-style', type=str, default='house',
                        choices=sorted(RENDER_STYLES.keys()),
                        help='Rendering palette/style for PNG outputs (default: house)')
    args = parser.parse_args()
    data_dir = args.data_dir

    if args.remote:
        print("\nLoading PTB-XL metadata from PhysioNet (remote mode)...")
        df = load_df_remote()
    else:
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
    if args.cases.strip():
        requested = [c.strip() for c in args.cases.split(',') if c.strip()]
        unknown = [c for c in requested if c not in QUERIES]
        if unknown:
            sys.exit(f"Unknown case IDs: {', '.join(unknown)}")
        processed_order = requested

    used_ids: set = set()
    successes: list = []
    failures:  list = []
    max_candidates = max(1, min(4, args.max_candidates))
    candidates_root = OUT_DIR / "candidates"
    candidates_root.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, list[dict[str, Any]]] = {}

    print(f"\nProcessing {len(processed_order)} cases → {OUT_DIR}\n")

    for case_id in processed_order:
        ranked = rank_candidates(df, case_id, used_ids)
        if ranked.empty:
            print(f"  ✗  {case_id:<24}  no PTB-XL match — synthetic PNG unchanged")
            failures.append(case_id)
            continue

        chosen_ecg_id: int | None = None
        chosen_sig: np.ndarray | None = None
        case_manifest: list[dict[str, Any]] = []

        for ecg_id, row in ranked.head(300).iterrows():
            raw_sig = load_candidate_signal(row, data_dir, args.remote)
            if raw_sig is None:
                continue
            sig = bandpass(raw_sig)
            scp_codes = row["scp_codes"] if isinstance(row.get("scp_codes"), dict) else {}
            scp_items = scp_codes.items() if isinstance(scp_codes, dict) else []
            codes_str = ", ".join(
                f"{k}({v:.0f})"
                for k, v in sorted(scp_items, key=lambda x: -x[1])
                if v >= 50
            )

            if chosen_ecg_id is None:
                chosen_ecg_id = int(cast(Any, ecg_id))
                chosen_sig = sig

            if len(case_manifest) < max_candidates:
                idx = len(case_manifest) + 1
                case_dir = candidates_root / case_id
                case_dir.mkdir(parents=True, exist_ok=True)
                strip_name = f"{case_id}__c{idx}_ecg{int(cast(Any, ecg_id))}.png"
                lead_name = f"{case_id}__c{idx}_ecg{int(cast(Any, ecg_id))}_12lead.png"
                strip_path = case_dir / strip_name
                lead_path = case_dir / lead_name
                render_strip(sig, strip_path, args.render_style)
                render_12lead(sig, lead_path, args.render_style)
                case_manifest.append({
                    "rank": idx,
                    "ecg_id": int(cast(Any, ecg_id)),
                    "codes": codes_str,
                    "stripPath": f"/cases/candidates/{case_id}/{strip_name}",
                    "twelveleadPath": f"/cases/candidates/{case_id}/{lead_name}",
                })

            if len(case_manifest) >= max_candidates and chosen_ecg_id is not None:
                break

        if chosen_ecg_id is None or chosen_sig is None:
            print(f"  ✗  {case_id:<24}  no PTB-XL match — synthetic PNG unchanged")
            failures.append(case_id)
            continue

        used_ids.add(chosen_ecg_id)
        render_strip(chosen_sig, OUT_DIR / f"{case_id}.png", args.render_style)
        render_12lead(chosen_sig, OUT_DIR / f"{case_id}_12lead.png", args.render_style)
        manifest[case_id] = case_manifest

        top_codes = case_manifest[0]["codes"] if case_manifest else ""
        print(
            f"  ✓  {case_id:<24}  ECG {chosen_ecg_id:6d}  [{top_codes}]"
            f"  candidates={len(case_manifest)}"
        )
        successes.append(case_id)

    manifest_path = ROOT / "web" / "src" / "data" / "ptbxl_candidates.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    print(f"\n{'─'*65}")
    print(f"Done: {len(successes)} replaced with PTB-XL real data, "
          f"{len(failures)} kept synthetic.")
    if failures:
        print(f"\nNo PTB-XL match for: {', '.join(failures)}")
        print("(Those cases retain their synthesized PNGs as fallback.)")
    print(f"\nAttribution reminder: derived PNG images use PTB-XL data")
    print(f"(CC BY 4.0). Ensure the app includes the required citation.")
    print(f"Candidate manifest written: {manifest_path}")


if __name__ == "__main__":
    main()
