#!/usr/bin/env python3
# pyright: basic

"""
EKG Teaching Case Generator
Generates synthetic rhythm strip PNG images + cases.json metadata
for the EKGTrainer teaching library.

Run from the repository root:
    python3 scripts/generate_cases.py [--render-style {house,physionet}]
"""

import argparse
import json
import warnings
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

warnings.filterwarnings('ignore')

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT      = Path(__file__).parent.parent
CASES_DIR = ROOT / "web" / "public" / "cases"
DATA_DIR  = ROOT / "web" / "src" / "data"
CASES_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── Signal parameters ────────────────────────────────────────────────────────
SR  = 500                      # Hz
DUR = 10                       # seconds
N   = SR * DUR                 # samples
T   = np.linspace(0, DUR, N)  # time array

# ── EKG paper appearance ─────────────────────────────────────────────────────
BG    = "#FFF5E6"   # traditional tan paper
MINOR = "#FFBBBB"   # fine red grid
MAJOR = "#EE6666"   # bold red grid
TRACE = "#111111"

# Render styles: house (traditional tan) and physionet (neutral white/gray)
RENDER_STYLES = {
    "house": {
        "bg": "#FFF5E6",
        "minor": "#FFBBBB",
        "major": "#EE6666",
        "trace": "#111111",
    },
    "physionet": {
        "bg": "#ffffff",
        "minor": "#e3e3e3",
        "major": "#bdbdbd",
        "trace": "#111111",
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# Waveform Primitives
# ═══════════════════════════════════════════════════════════════════════════════

def gauss(t, center, fwhm_ms, amp):
    """Gaussian bump for P/Q/R/S/T wave approximation."""
    sigma = (fwhm_ms / 1000.0) / 2.3548
    return amp * np.exp(-0.5 * ((t - center) / sigma) ** 2)


def st_plateau(t, j_point, t_onset, amp):
    """Smooth ST-segment plateau between J-point and T-wave onset."""
    if t_onset <= j_point:
        return np.zeros_like(t)
    edge = 0.012
    up = 0.5 * (1.0 + np.tanh((t - j_point) / edge))
    down = 0.5 * (1.0 + np.tanh((t_onset - t) / edge))
    return amp * up * down


def place_normal_beat(sig, t, r_at,
                      pr_ms=160, qrs_ms=80, qt_ms=380,
                      p_amp=0.15, r_amp=1.0, t_amp=0.30,
                      no_p=False, inverted_p=False):
    """Add a normal narrow-QRS PQRST complex to sig at r_at seconds."""
    if not no_p:
        p_center = r_at - pr_ms / 1000.0 + 0.040
        direction = -1 if inverted_p else 1
        sig += gauss(t, p_center, 45, direction * p_amp)

    hw = (qrs_ms / 1000.0) / 2
    sig += gauss(t, r_at - hw * 0.4, qrs_ms * 0.25, -0.08 * r_amp)   # Q
    sig += gauss(t, r_at,            qrs_ms * 0.45,  r_amp)           # R
    sig += gauss(t, r_at + hw * 0.7, qrs_ms * 0.30, -0.15 * r_amp)   # S
    sig += gauss(t, r_at + (qt_ms / 1000.0) * 0.62, 100, t_amp)      # T


def place_wide_beat(sig, t, r_at, style="ventricular", qt_ms=440, r_amp=1.0):
    """Add a wide-QRS complex (PVC / ventricular / BBB)."""
    if style == "pvc":
        sig += gauss(t, r_at - 0.020,  80, -0.55 * r_amp)
        sig += gauss(t, r_at + 0.040, 100,  r_amp)
        sig += gauss(t, r_at + 0.100,  40, -0.28 * r_amp)
        sig += gauss(t, r_at + (qt_ms / 1000) * 0.60, 120, -0.25 * r_amp)

    elif style == "vt":
        # Monomorphic VT: broad, regular, dominant wide complex with discordant T.
        sig += gauss(t, r_at - 0.022, 48, -0.18 * r_amp)
        sig += gauss(t, r_at + 0.010, 120, 1.10 * r_amp)
        sig += gauss(t, r_at + 0.082, 68, -0.22 * r_amp)
        sig += gauss(t, r_at + (qt_ms / 1000) * 0.56, 95, -0.18 * r_amp)

    elif style == "lbbb":
        sig += gauss(t, r_at,          130,  r_amp)
        sig += gauss(t, r_at + 0.070,   30, -0.04 * r_amp)
        sig += gauss(t, r_at + (qt_ms / 1000) * 0.60, 110, -0.20 * r_amp)

    elif style == "rbbb":
        sig += gauss(t, r_at - 0.010,  20, -0.07 * r_amp)   # Q
        sig += gauss(t, r_at,           28,  0.85 * r_amp)   # R
        sig += gauss(t, r_at + 0.040,   22, -0.35 * r_amp)  # S
        sig += gauss(t, r_at + 0.080,   32,  0.50 * r_amp)  # R'
        sig += gauss(t, r_at + (qt_ms / 1000) * 0.60, 85, 0.20 * r_amp)  # T

    else:  # generic ventricular escape
        sig += gauss(t, r_at - 0.015,   60, -0.40 * r_amp)
        sig += gauss(t, r_at + 0.030,  100,  r_amp)
        sig += gauss(t, r_at + (qt_ms / 1000) * 0.60, 120, -0.20 * r_amp)


def regular_r_times(heart_rate, start=0.3):
    """R wave positions for a regular rhythm over DUR seconds."""
    rr = 60.0 / heart_rate
    return np.arange(start, DUR - 0.1, rr)


# ═══════════════════════════════════════════════════════════════════════════════
# Rhythm Generators
# ═══════════════════════════════════════════════════════════════════════════════

def normal_sinus(heart_rate=75, pr_ms=160):
    sig = np.zeros(N)
    for r in regular_r_times(heart_rate):
        place_normal_beat(sig, T, r, pr_ms=pr_ms)
    return sig


def sinus_arrhythmia(base_rate=70):
    sig = np.zeros(N)
    rr_base = 60.0 / base_rate
    r, cycle = 0.3, 0
    while r < DUR - 0.2:
        place_normal_beat(sig, T, r)
        variation = 0.15 * rr_base * np.sin(2 * np.pi * cycle / 6)
        r += rr_base + variation
        cycle += 1
    return sig


def with_pacs(heart_rate=70):
    sig = np.zeros(N)
    r_times = list(regular_r_times(heart_rate))
    rr = 60.0 / heart_rate
    pac_indices = {2, 5, 8} if len(r_times) > 9 else {2, 5}
    for r in r_times:
        place_normal_beat(sig, T, r)
    for i in sorted(idx for idx in pac_indices if idx < len(r_times) - 1):
        pac_r = r_times[i] + rr * 0.40
        place_normal_beat(sig, T, pac_r, pr_ms=95, p_amp=0.26, inverted_p=True,
                          r_amp=0.82, t_amp=0.18)
    return sig


def with_pvcs(heart_rate=70):
    sig = np.zeros(N)
    r_times = list(regular_r_times(heart_rate))
    rr = 60.0 / heart_rate
    pvc_indices = {2, 5, 8} if len(r_times) > 9 else {2, 5}
    for r in r_times:
        place_normal_beat(sig, T, r)
    for i in sorted(idx for idx in pvc_indices if idx < len(r_times) - 1):
        pvc_r = r_times[i] + rr * 0.52
        place_wide_beat(sig, T, pvc_r, style="vt", r_amp=1.18)
    return sig


def svt(heart_rate=190):
    sig = np.zeros(N)
    for r in regular_r_times(heart_rate):
        place_normal_beat(sig, T, r, no_p=True, r_amp=0.85, t_amp=0.25)
    return sig


def atrial_fibrillation(avg_rate=80):
    sig = np.zeros(N)
    freqs = np.random.uniform(350, 600, 15)
    for f in freqs:
        sig += np.random.uniform(0.02, 0.06) * np.sin(
            2 * np.pi * (f / 60) * T + np.random.uniform(0, 2 * np.pi)
        )
    r = 0.35
    while r < DUR - 0.2:
        place_normal_beat(sig, T, r, no_p=True, r_amp=0.9)
        r += (60.0 / avg_rate) * np.random.lognormal(0, 0.25)
    return sig


def atrial_flutter(flutter_rate=300, ratio=2):
    sig = np.zeros(N)
    ventricular_rate = flutter_rate / ratio
    flutter_period = 60.0 / flutter_rate
    for f_start in np.arange(0.1, DUR, flutter_period):
        mask = (T >= f_start) & (T < f_start + flutter_period)
        sig[mask] += -0.18 * ((T[mask] - f_start) / flutter_period - 0.5)
    for r in regular_r_times(ventricular_rate):
        place_normal_beat(sig, T, r, no_p=True, r_amp=0.95, t_amp=0.20)
    return sig


def first_degree_avb(heart_rate=70):
    sig = np.zeros(N)
    for r in regular_r_times(heart_rate):
        place_normal_beat(sig, T, r, pr_ms=280)
    return sig


def mobitz_i(base_rate=75):
    sig = np.zeros(N)
    pr_cycle = [160, 210, 260, 300]
    r, beat = 0.4, 0
    while r < DUR - 0.3:
        idx = beat % (len(pr_cycle) + 1)
        if idx == len(pr_cycle):
            # Dropped beat — P wave only
            p_center = r - pr_cycle[-1] / 1000.0 + 0.040
            sig += gauss(T, p_center, 45, 0.15)
            r += (60.0 / base_rate) * 1.15
        else:
            place_normal_beat(sig, T, r, pr_ms=pr_cycle[idx])
            r += 60.0 / base_rate
        beat += 1
    return sig


def mobitz_ii(base_rate=75, ratio=3):
    sig = np.zeros(N)
    p_times = np.arange(0.3, DUR, 60.0 / base_rate)
    for i, p_t in enumerate(p_times):
        sig += gauss(T, p_t, 45, 0.15)
        if i % ratio == 0:
            r_at = p_t + 0.160
            if r_at < DUR - 0.2:
                sig += gauss(T, r_at - 0.010, 20, -0.07)
                sig += gauss(T, r_at,          30,  0.95)
                sig += gauss(T, r_at + 0.030,  20, -0.12)
                sig += gauss(T, r_at + 0.240,  90,  0.28)
    return sig


def third_degree_avb():
    sig = np.zeros(N)
    for p_t in np.arange(0.25, DUR, 60.0 / 72):
        sig += gauss(T, p_t, 45, 0.15)
    for r in regular_r_times(33, start=0.6):
        place_wide_beat(sig, T, r, style="ventricular", r_amp=0.9)
    return sig


def lbbb(heart_rate=70):
    sig = np.zeros(N)
    for r in regular_r_times(heart_rate):
        sig += gauss(T, r - 0.120, 45, 0.15)   # P wave
        place_wide_beat(sig, T, r, style="lbbb")
    return sig


def rbbb(heart_rate=75):
    sig = np.zeros(N)
    for r in regular_r_times(heart_rate):
        sig += gauss(T, r - 0.120, 45, 0.15)   # P wave
        place_wide_beat(sig, T, r, style="rbbb")
    return sig


def junctional(heart_rate=50):
    sig = np.zeros(N)
    for r in regular_r_times(heart_rate):
        place_normal_beat(sig, T, r, inverted_p=True, p_amp=0.12,
                          pr_ms=100, r_amp=0.85)
    return sig


def idioventricular(heart_rate=33):
    sig = np.zeros(N)
    for r in regular_r_times(heart_rate):
        place_wide_beat(sig, T, r, style="ventricular", r_amp=0.85)
    return sig


def ventricular_tachycardia(heart_rate=175):
    sig = np.zeros(N)
    for r in regular_r_times(heart_rate, start=0.16):
        place_wide_beat(sig, T, r, style="vt", r_amp=1.20)
    return sig


def ventricular_fibrillation():
    sig = np.zeros(N)
    np.random.seed(42)
    for f in np.concatenate([np.random.uniform(200, 400, 20),
                              np.random.uniform(50, 200, 10)]):
        amp = np.random.exponential(0.12)
        phase = np.random.uniform(0, 2 * np.pi)
        sig += amp * np.sin(2 * np.pi * (f / 60) * T + phase)
    envelope = np.clip(0.5 + 0.5 * np.cos(2 * np.pi * T / (DUR * 2)), 0.3, 1.0)
    return sig * envelope


def asystole():
    return np.random.normal(0, 0.015, N)


# ═══════════════════════════════════════════════════════════════════════════════
# Generalised lead-signal builder
# ═══════════════════════════════════════════════════════════════════════════════

def lead_signal(r_times,
                pr_ms=160, qrs_ms=80, qt_ms=380,
                p_amp=0.15, p_inverted=False, no_p=False,
                r_amp=1.0, q_frac=0.08, s_frac=0.15,
                st_offset=0.0,          # + elevation  – depression (mV)
                t_amp=0.30, t_inverted=False,
                big_q=False,            # pathological Q wave
                wide=False,             # wide QRS (e.g. RBBB/LBBB morphology)
                rsrp=False,             # add terminal R' after S (RBBB)
                broad_r=False):         # broad monophasic R (LBBB)
    """Build an arbitrary-lead ECG signal from beat-position list."""
    sig = np.zeros(N)
    for r in r_times:
        if not no_p:
            p_c = r - pr_ms / 1000.0 + 0.040
            sig += gauss(T, p_c, 45, (-1 if p_inverted else 1) * p_amp)

        hw = (qrs_ms / 1000.0) / 2
        if big_q:
            sig += gauss(T, r - 0.048, 38, -0.38 * r_amp)
        else:
            sig += gauss(T, r - hw * 0.4, qrs_ms * 0.25, -q_frac * r_amp)

        if broad_r:                             # LBBB — wide monophasic R
            sig += gauss(T, r + 0.018, 130, r_amp)
            sig += gauss(T, r + 0.080,  28, -0.04 * r_amp)
        elif rsrp:                              # RBBB — RSR' pattern
            sig += gauss(T, r,           28,  0.85 * r_amp)
            sig += gauss(T, r + 0.038,   22, -0.35 * r_amp)
            sig += gauss(T, r + 0.078,   32,  0.50 * r_amp)
        else:
            sig += gauss(T, r, qrs_ms * 0.45, r_amp)
            sig += gauss(T, r + hw * 0.7, qrs_ms * 0.30, -s_frac * r_amp)

        # ST displacement as a plateau from J-point to early T onset.
        if abs(st_offset) > 0.005:
            j_point = r + max(0.045, (qrs_ms / 1000.0) * 0.55)
            t_onset = r + (qt_ms / 1000.0) * 0.50
            sig += st_plateau(T, j_point, t_onset, st_offset)

        t_c = r + (qt_ms / 1000.0) * 0.63
        sig += gauss(T, t_c, 100, (-1 if t_inverted else 1) * abs(t_amp))

    return sig


# ═══════════════════════════════════════════════════════════════════════════════
# Multi-lead renderer  (stacks 2–4 leads vertically)
# ═══════════════════════════════════════════════════════════════════════════════

def _style_ax(ax, label, render_style="house"):
    style = RENDER_STYLES.get(render_style, RENDER_STYLES["house"])
    bg = style["bg"]
    minor = style["minor"]
    major = style["major"]
    
    ax.set_facecolor(bg)
    ax.set_xticks(np.arange(0, DUR + 0.04, 0.04), minor=True)
    ax.set_yticks(np.arange(-0.6, 1.7, 0.10), minor=True)
    ax.set_xticks(np.arange(0, DUR + 0.20, 0.20))
    ax.set_yticks(np.arange(-0.5, 1.6, 0.50))
    ax.grid(True, which='minor', color=minor, linewidth=0.30, zorder=1)
    ax.grid(True, which='major', color=major, linewidth=0.70, zorder=2)
    ax.set_xlim(0, DUR)
    ax.set_ylim(-0.5, 1.5)
    ax.tick_params(which='both', bottom=False, left=False,
                   labelbottom=False, labelleft=False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.text(0.005, 0.96, label.split(" — ")[0], transform=ax.transAxes,
            fontsize=8, fontweight='bold', va='top', color='#222222', zorder=5)


def render_multilead(leads, rhythm_label, out_path, render_style="house"):
    """
    leads: list of (signal_array, lead_name_str)
    """
    style = RENDER_STYLES.get(render_style, RENDER_STYLES["house"])
    bg = style["bg"]
    trace = style["trace"]
    
    n = len(leads)
    fig, axes = plt.subplots(n, 1, figsize=(12, n * 1.85), dpi=150,
                              gridspec_kw={"hspace": 0.06})
    fig.patch.set_facecolor(bg)
    if n == 1:
        axes = [axes]

    for ax, (sig, name) in zip(axes, leads):
        _style_ax(ax, name, render_style=render_style)
        ax.plot(T, sig, color=trace, linewidth=1.2, zorder=3, antialiased=True)

    axes[0].text(0.99, 0.96, '25 mm/s  |  10 mm/mV',
                 transform=axes[0].transAxes, fontsize=6.5,
                 ha='right', va='top', color='#888888', zorder=5)
    plt.savefig(out_path, bbox_inches='tight', facecolor=bg)
    plt.close(fig)
    print(f"  ✓  {out_path.name}")


# ═══════════════════════════════════════════════════════════════════════════════
# 12-lead pathology generators  (return list of (signal, lead_name))
# ═══════════════════════════════════════════════════════════════════════════════

def _rr(hr, start=0.35):
    return list(regular_r_times(hr, start))


def anterior_stemi(hr=80):
    rs = _rr(hr)
    return [
        (lead_signal(rs, st_offset=+0.74, t_amp=0.58, big_q=True, qrs_ms=96, r_amp=0.82), "V2 — tombstone ST elevation"),
        (lead_signal(rs, st_offset=+0.66, t_amp=0.54, big_q=True, qrs_ms=94, r_amp=0.88), "V3 — tombstone ST elevation"),
        (lead_signal(rs, st_offset=+0.46, t_amp=0.44, qrs_ms=90),                           "V4 — ST elevation"),
        (lead_signal(rs, st_offset=-0.24, t_inverted=True, t_amp=0.20), "aVL — reciprocal depression"),
    ]


def inferior_stemi(hr=78):
    rs = _rr(hr)
    return [
        (lead_signal(rs, st_offset=+0.35, t_amp=0.50, big_q=True),   "III — ST elevation"),
        (lead_signal(rs, st_offset=+0.25, t_amp=0.42, big_q=True),   "II — ST elevation"),
        (lead_signal(rs, st_offset=-0.22, t_inverted=True),           "aVL — reciprocal"),
    ]


def lateral_stemi(hr=82):
    rs = _rr(hr)
    return [
        (lead_signal(rs, st_offset=+0.30, t_amp=0.48),               "I — ST elevation"),
        (lead_signal(rs, st_offset=+0.28, t_amp=0.44),                "aVL — ST elevation"),
        (lead_signal(rs, st_offset=-0.18, t_inverted=True),           "III — reciprocal"),
    ]


def posterior_stemi(hr=76):
    """Posterior MI shows as ST depression + tall R in V1–V3 (reciprocal)."""
    rs = _rr(hr)
    # Posterior wall STEMI is electrically 'upside down' in anterior leads
    return [
        (lead_signal(rs, r_amp=1.35, s_frac=0.04, st_offset=-0.28, t_inverted=False, t_amp=0.55),
         "V1 — tall R, ST depression (posterior)"),
        (lead_signal(rs, r_amp=1.20, s_frac=0.06, st_offset=-0.22, t_amp=0.45),
         "V2 — tall R, ST depression (posterior)"),
        (lead_signal(rs, st_offset=-0.12),
         "V3 — ST depression"),
    ]


def nstemi_st_depression(hr=88):
    rs = _rr(hr)
    return [
        (lead_signal(rs, st_offset=-0.20, t_inverted=True,  t_amp=0.22),  "V4 — ST depression"),
        (lead_signal(rs, st_offset=-0.18, t_inverted=True,  t_amp=0.20),  "V5 — ST depression"),
        (lead_signal(rs, st_offset=-0.14, t_amp=0.28),                    "II — reference"),
    ]


def wellens_a(hr=72):
    """Type A Wellens: biphasic T in V2–V3 (positive then negative deflection)."""
    rs = _rr(hr)
    def biphasic_t_lead(r_times):
        sig = lead_signal(r_times, st_offset=0.0, t_amp=0.0)  # base without T
        for r in r_times:
            t_c = r + 0.240
            sig += gauss(T, t_c - 0.025, 35,  0.18)   # initial positive
            sig += gauss(T, t_c + 0.045, 45, -0.22)   # terminal negative
        return sig
    return [
        (biphasic_t_lead(rs),                                "V2 — biphasic T (Wellens A)"),
        (biphasic_t_lead(rs),                                "V3 — biphasic T (Wellens A)"),
        (lead_signal(rs, t_amp=0.30),                        "V5 — reference (normal T)"),
    ]


def wellens_b(hr=68):
    """Type B Wellens: deep symmetric T inversion V2–V3."""
    rs = _rr(hr)
    return [
        (lead_signal(rs, t_inverted=True, t_amp=0.55, st_offset=0.0), "V2 — deep T inversion (Wellens B)"),
        (lead_signal(rs, t_inverted=True, t_amp=0.48, st_offset=0.0), "V3 — deep T inversion (Wellens B)"),
        (lead_signal(rs, t_amp=0.30),                                  "V5 — reference (normal T)"),
    ]


def pe_s1q3t3(hr=108):
    """Classic PE pattern: S1Q3T3 + sinus tachycardia."""
    rs = _rr(hr)
    return [
        # Lead I: prominent S wave (deep, wide S)
        (lead_signal(rs, s_frac=0.55, t_amp=0.22),           "I — prominent S wave (S1)"),
        # Lead III: Q wave + inverted T (Q3T3)
        (lead_signal(rs, big_q=True, t_inverted=True, t_amp=0.30, st_offset=0.0),
         "III — Q wave + T inversion (Q3T3)"),
        # V1: right heart strain — T inversion, partial RBBB
        (lead_signal(rs, rsrp=True, t_inverted=True, t_amp=0.28), "V1 — RV strain / partial RBBB"),
    ]


def pe_rv_strain(hr=112):
    """PE: right precordial T inversions — right heart strain pattern."""
    rs = _rr(hr)
    return [
        (lead_signal(rs, t_inverted=True, t_amp=0.35),   "V1 — T inversion (RV strain)"),
        (lead_signal(rs, t_inverted=True, t_amp=0.40),   "V2 — T inversion (RV strain)"),
        (lead_signal(rs, t_inverted=True, t_amp=0.32),   "V3 — T inversion (RV strain)"),
    ]


def lv_strain(hr=72):
    """LVH with strain: tall lateral R, ST depression + T inversion."""
    rs = _rr(hr)
    return [
        # V5: tall R (LVH criterion), strain ST-T
        (lead_signal(rs, r_amp=2.20, s_frac=0.04, st_offset=-0.18, t_inverted=True, t_amp=0.32),
         "V5 — tall R (LVH), strain ST-T"),
        # I: lateral strain
        (lead_signal(rs, r_amp=1.40, st_offset=-0.14, t_inverted=True, t_amp=0.25),
         "I — lateral strain"),
        # V1: deep S (LVH criterion, reciprocal)
        (lead_signal(rs, r_amp=0.25, s_frac=1.80, t_amp=0.18),
         "V1 — deep S wave (LVH)"),
    ]


def rv_strain_pattern(hr=90):
    """RV strain without PE-specific features — right precordial T inversions."""
    rs = _rr(hr)
    return [
        (lead_signal(rs, t_inverted=True, t_amp=0.38, s_frac=0.30),  "V1 — T inversion, RV strain"),
        (lead_signal(rs, t_inverted=True, t_amp=0.42),                "V2 — T inversion"),
        (lead_signal(rs, t_inverted=True, t_amp=0.28),                "V3 — T inversion"),
    ]


def _pace_spike(sig, t, spike_t, amp=0.80):
    """Narrow pacer spike: very tight Gaussian (~3 ms FWHM) to simulate impulse artifact."""
    sig += gauss(t, spike_t, 3, amp)


def atrial_paced(hr=70, pr_ms=160):
    """AAI pacing: atrial spike + normal AV conduction → narrow QRS."""
    sig = np.zeros(N)
    for r in regular_r_times(hr):
        spike_t = r - pr_ms / 1000.0 + 0.040 - 0.020  # spike just before P
        _pace_spike(sig, T, spike_t)
        place_normal_beat(sig, T, r, pr_ms=pr_ms, p_amp=0.10)
    return sig


def ventricular_paced(hr=70):
    """VVI pacing: ventricular spike + wide LBBB-morphology QRS, no preceding P."""
    sig = np.zeros(N)
    for r in regular_r_times(hr):
        _pace_spike(sig, T, r - 0.010)
        place_wide_beat(sig, T, r, style="lbbb", r_amp=0.90)
    return sig


def av_paced(hr=70, pr_ms=200):
    """DDD pacing: atrial spike + atrial activity + ventricular spike + wide QRS."""
    sig = np.zeros(N)
    for r in regular_r_times(hr):
        a_spike_t = r - pr_ms / 1000.0 + 0.040 - 0.020
        _pace_spike(sig, T, a_spike_t, amp=0.70)
        sig += gauss(T, a_spike_t + 0.025, 45, 0.10)  # paced P wave
        _pace_spike(sig, T, r - 0.010, amp=0.80)
        place_wide_beat(sig, T, r, style="lbbb", r_amp=0.90)
    return sig


def brugada_type1_strip(hr=72):
    """Brugada Type 1: coved ST elevation + T inversion V1–V2, RBBB-like morphology."""
    rs = _rr(hr)
    return [
        (lead_signal(rs, rsrp=True, r_amp=0.55, st_offset=+0.30, t_inverted=True, t_amp=0.24), "V1"),
        (lead_signal(rs, rsrp=True, r_amp=0.65, st_offset=+0.20, t_inverted=True, t_amp=0.18), "V2"),
        (lead_signal(rs, r_amp=0.78, st_offset=+0.06),                                         "V3"),
    ]


def wpw_strip(hr=72):
    """WPW: shortened PR (~90 ms), delta slur, wide QRS — Lead II rhythm strip."""
    rs = _rr(hr)
    return lead_signal(rs, pr_ms=90, qrs_ms=120, qt_ms=360,
                       p_amp=0.14, r_amp=1.0, s_frac=0.18,
                       st_offset=-0.08, t_inverted=True, t_amp=0.20)


def long_qt_strip(hr=68):
    """Long QT: markedly prolonged QT (>500 ms), normal P/QRS, sinus rhythm."""
    rs = _rr(hr)
    return lead_signal(rs, pr_ms=160, qrs_ms=80, qt_ms=520,
                       p_amp=0.15, r_amp=1.0, s_frac=0.15,
                       t_amp=0.22)


# ═══════════════════════════════════════════════════════════════════════════════
# Rendering
def hyperkalemia_strip(hr=65):
    """Hyperkalemia: absent P waves, widened QRS (~140 ms), very tall tented T waves.
    Models moderate-to-severe hyperkalaemia (K+ ≥ 6.5 mEq/L) in Lead II."""
    sig = np.zeros(N)
    for r in regular_r_times(hr):
        # Wide QRS — no P wave; narrow tented T added separately
        place_normal_beat(sig, T, r, no_p=True, qrs_ms=140, qt_ms=350, t_amp=0.0)
        # Tall, narrow, symmetric ("tented") T wave
        sig += gauss(T, r + 0.225, 62, 0.64)
    return sig


def lae_strip(hr=70):
    """Left Atrial Enlargement: broad notched M-shaped P waves (P mitrale), Lead II."""
    sig = np.zeros(N)
    for r in regular_r_times(hr):
        p_center = r - 0.160 + 0.040   # P midpoint for PR = 160 ms
        # M-shaped / notched P: RA component (earlier) + LA component (later)
        sig += gauss(T, p_center - 0.027, 34, 0.12)    # right-atrial hump
        sig += gauss(T, p_center + 0.030, 34, 0.11)    # left-atrial hump
        place_normal_beat(sig, T, r, no_p=True, pr_ms=180)
    return sig


def rae_strip(hr=72):
    """Right Atrial Enlargement: tall, peaked P waves (P pulmonale ≥ 0.25 mV), Lead II."""
    sig = np.zeros(N)
    for r in regular_r_times(hr):
        p_center = r - 0.160 + 0.040
        sig += gauss(T, p_center, 27, 0.30)     # tall narrow peaked P (RA dominant)
        place_normal_beat(sig, T, r, no_p=True)
    return sig


def lafb_strip(hr=70):
    """LAFB: rS pattern in Lead II reflecting left-axis deviation (~−60°). QRS < 120 ms."""
    sig = np.zeros(N)
    for r in regular_r_times(hr):
        p_center = r - 0.160 + 0.040
        sig += gauss(T, p_center, 40, 0.10)     # small P in Lead II with LAD
        sig += gauss(T, r, 22, 0.24)            # small r wave
        sig += gauss(T, r + 0.026, 26, -0.80)  # deep S wave (axis deviation)
        sig += gauss(T, r + 0.228, 90, 0.20)   # upright T wave
    return sig


def bigeminy_strip(hr=72):
    """Ventricular Bigeminy: every other beat is a PVC — sinus → PVC → pause repeats."""
    sig = np.zeros(N)
    rr_int = 60.0 / hr
    r = 0.35
    while r < DUR - 0.20:
        place_normal_beat(sig, T, r)                    # sinus beat
        pvc_r = r + rr_int * 0.55                       # PVC at coupling interval
        if pvc_r < DUR - 0.20:
            place_wide_beat(sig, T, pvc_r, style="pvc", r_amp=1.15)
        r += rr_int * 2.0                               # compensatory pause
    return sig


def trigeminy_strip(hr=70):
    """Ventricular Trigeminy: every third beat is a PVC — sinus → sinus → PVC pattern."""
    sig = np.zeros(N)
    rr_int = 60.0 / hr
    r = 0.35
    while r < DUR - 0.20:
        place_normal_beat(sig, T, r)                    # first sinus beat
        r2 = r + rr_int
        if r2 < DUR - 0.20:
            place_normal_beat(sig, T, r2)               # second sinus beat
        pvc_r = r2 + rr_int * 0.58                      # PVC after second beat
        if pvc_r < DUR - 0.20:
            place_wide_beat(sig, T, pvc_r, style="pvc", r_amp=1.12)
        r += rr_int * 3.0                               # next group at 3× RR
    return sig


# ═══════════════════════════════════════════════════════════════════════════════
# Rendering
# ═══════════════════════════════════════════════════════════════════════════════

def render(signal, rhythm_label, out_path, render_style="house"):
    style = RENDER_STYLES.get(render_style, RENDER_STYLES["house"])
    bg = style["bg"]
    minor = style["minor"]
    major = style["major"]
    trace = style["trace"]
    
    fig, ax = plt.subplots(figsize=(12, 2.4), dpi=150)
    fig.patch.set_facecolor(bg)
    ax.set_facecolor(bg)

    ax.set_xticks(np.arange(0, DUR + 0.04, 0.04), minor=True)
    ax.set_yticks(np.arange(-0.6, 1.7, 0.1), minor=True)
    ax.set_xticks(np.arange(0, DUR + 0.2, 0.2))
    ax.set_yticks(np.arange(-0.5, 1.6, 0.5))
    ax.grid(True, which='minor', color=minor, linewidth=0.3, zorder=1)
    ax.grid(True, which='major', color=major, linewidth=0.7, zorder=2)

    ax.set_xlim(0, DUR)
    ax.set_ylim(-0.5, 1.5)
    ax.tick_params(which='both', bottom=False, left=False,
                   labelbottom=False, labelleft=False)
    for s in ax.spines.values():
        s.set_visible(False)

    ax.plot(T, signal, color=trace, linewidth=1.2, zorder=3, antialiased=True)

    ax.text(0.99, 0.97, '25 mm/s  |  10 mm/mV  |  Lead II',
            transform=ax.transAxes, fontsize=6.5, ha='right',
            va='top', color='#888888')
    plt.tight_layout(pad=0.2)
    plt.savefig(out_path, bbox_inches='tight', facecolor=bg)
    plt.close(fig)

# ═══════════════════════════════════════════════════════════════════════════════
# Case Definitions
# ═══════════════════════════════════════════════════════════════════════════════

CASES = [
    # ── Sinus rhythms ──────────────────────────────────────────────────────────
    dict(id="nsr_01", rhythm="Normal Sinus Rhythm", category="sinus", difficulty=1,
         generator=lambda: normal_sinus(75), rate=75, regularity="regular",
         key_features=["Rate 60–100 bpm", "Regular rhythm", "Upright P wave before each QRS",
                       "Normal PR interval (120–200 ms)", "Narrow QRS (<120 ms)"],
         teaching="The SA node fires regularly at 75 bpm. Every P wave is followed by a QRS. "
                  "All intervals are within normal limits — the baseline rhythm for comparison."),

    dict(id="nsr_02", rhythm="Normal Sinus Rhythm", category="sinus", difficulty=1,
         generator=lambda: normal_sinus(88), rate=88, regularity="regular",
         key_features=["Rate 88 bpm", "Regular", "1:1 P:QRS ratio", "Narrow QRS"],
         teaching="A slightly faster NSR — still within normal limits. "
                  "Note how P waves are closer to the preceding T wave at higher rates."),

    dict(id="brady_01", rhythm="Sinus Bradycardia", category="sinus", difficulty=1,
         generator=lambda: normal_sinus(45), rate=45, regularity="regular",
         key_features=["Rate <60 bpm", "Regular", "Normal P waves",
                       "Normal PR interval", "Narrow QRS"],
         teaching="All features of NSR except rate <60 bpm. Common in athletes and during sleep. "
                  "Treat only if symptomatic (hypotension, altered mentation)."),

    dict(id="brady_02", rhythm="Sinus Bradycardia", category="sinus", difficulty=1,
         generator=lambda: normal_sinus(38), rate=38, regularity="regular",
         key_features=["Rate 38 bpm — marked bradycardia", "Regular", "Normal P morphology"],
         teaching="Marked bradycardia at 38 bpm. Wide R-R intervals are visible even on a "
                  "10-second strip. Consider atropine or pacing if symptomatic."),

    dict(id="tachy_01", rhythm="Sinus Tachycardia", category="sinus", difficulty=1,
         generator=lambda: normal_sinus(115), rate=115, regularity="regular",
         key_features=["Rate >100 bpm", "Regular", "Upright P in lead II",
                       "Normal PR", "Narrow QRS"],
         teaching="SA node firing >100 bpm. Always identify the underlying cause: "
                  "pain, fever, hypovolemia, anxiety, or PE."),

    dict(id="tachy_02", rhythm="Sinus Tachycardia", category="sinus", difficulty=2,
         generator=lambda: normal_sinus(140), rate=140, regularity="regular",
         key_features=["Rate 140 bpm", "P waves partially merge with T waves",
                       "Regular", "Narrow QRS"],
         teaching="At 140 bpm the P wave begins merging with the preceding T wave. "
                  "Identify P waves carefully to distinguish from SVT."),

    dict(id="sarr_01", rhythm="Sinus Arrhythmia", category="sinus", difficulty=2,
         generator=lambda: sinus_arrhythmia(68), rate=68, regularity="regularly_irregular",
         key_features=["Rate varies with respiration", "Irregular but patterned",
                       "Normal P waves and PR interval", "R-R varies >0.12 s"],
         teaching="R-R intervals vary cyclically with respiration — a normal variant, "
                  "especially in younger patients. Note the repeating pattern."),

    # ── Ectopic beats ─────────────────────────────────────────────────────────
    dict(id="pac_01", rhythm="Premature Atrial Contractions (PACs)", category="atrial", difficulty=2,
         generator=lambda: with_pacs(70), rate=70, regularity="irregular",
         key_features=["Early narrow QRS", "Different P wave morphology",
                       "Incomplete compensatory pause", "Regular background rhythm"],
         teaching="PACs originate outside the SA node. The P wave differs from sinus P waves. "
                  "The pause following a PAC is incomplete (compensatory pause is <2 normal R-R)."),

    dict(id="pvc_01", rhythm="Premature Ventricular Contractions (PVCs)", category="ventricular", difficulty=2,
         generator=lambda: with_pvcs(70), rate=70, regularity="irregular",
         key_features=["Early wide bizarre QRS (≥120 ms)", "No preceding P wave",
                       "Full compensatory pause", "Discordant T wave"],
         teaching="PVCs arise from ventricular tissue. Wide, bizarre, not preceded by a P wave. "
                  "The compensatory pause is complete (the next sinus beat arrives on time)."),

    # ── Supraventricular ──────────────────────────────────────────────────────
    dict(id="svt_01", rhythm="SVT (Supraventricular Tachycardia)", category="supraventricular", difficulty=2,
         generator=lambda: svt(190), rate=190, regularity="regular",
         key_features=["Rate 150–250 bpm", "Regular", "Narrow QRS",
                       "P waves absent or buried in QRS/T wave"],
         teaching="Regular narrow-complex tachycardia. Abrupt onset and termination distinguish "
                  "SVT from sinus tachycardia. Vagal maneuvers or adenosine to break."),

    dict(id="afib_01", rhythm="Atrial Fibrillation", category="atrial", difficulty=2,
         generator=lambda: atrial_fibrillation(80), rate=80, regularity="irregularly_irregular",
         key_features=["Irregularly irregular rhythm", "No identifiable P waves",
                       "Fibrillatory baseline", "Narrow QRS"],
         teaching="The hallmark of AFib: irregularly irregular with no P waves. "
                  "The atria fire chaotically at 350–600 bpm; the AV node filters randomly."),

    dict(id="afib_02", rhythm="Atrial Fibrillation (RVR)", category="atrial", difficulty=2,
         generator=lambda: atrial_fibrillation(130), rate=130, regularity="irregularly_irregular",
         key_features=["Rapid irregular rhythm", "No P waves", "Ventricular rate >100 bpm"],
         teaching="AFib with rapid ventricular response (RVR). Rate control is the priority. "
                  "The irregular rhythm differentiates this from SVT."),

    dict(id="aflut_01", rhythm="Atrial Flutter (4:1)", category="atrial", difficulty=3,
         generator=lambda: atrial_flutter(300, 4), rate=75, regularity="regular",
         key_features=["Atrial rate ~300 bpm", "Sawtooth flutter waves clearly visible (II, III, aVF)",
                       "Regular ventricular rate ~75 bpm", "4:1 conduction — 3 flutter waves between QRS"],
         teaching="Classic sawtooth at 300 bpm with 4:1 conduction. Three flutter waves are clearly "
                  "visible between each QRS. When in doubt about an oddly regular rhythm, look for the "
                  "telltale sawtooth in inferior leads. Flutter can conduct at 2:1, 3:1, or 4:1."),

    # ── AV Blocks ─────────────────────────────────────────────────────────────
    dict(id="avb1_01", rhythm="1st Degree AV Block", category="av_block", difficulty=2,
         generator=lambda: first_degree_avb(70), rate=70, regularity="regular",
         key_features=["PR interval >200 ms", "Regular rhythm",
                       "Every P followed by a QRS", "Narrow QRS"],
         teaching="PR is prolonged (>5 small boxes) but every P wave is conducted. "
                  "Not a true block — a conduction delay. Rarely needs treatment alone."),

    dict(id="avb2m1_01", rhythm="2nd Degree AV Block — Mobitz I (Wenckebach)",
         category="av_block", difficulty=3,
         generator=lambda: mobitz_i(75), rate=75, regularity="regularly_irregular",
         key_features=["PR progressively lengthens", "QRS eventually dropped",
                       "Pattern repeats (group beating)", "Narrow QRS"],
         teaching="Progressive PR lengthening followed by a non-conducted P wave. "
                  "The RR intervals shorten before the pause. Usually benign, AV node level."),

    dict(id="avb2m2_01", rhythm="2nd Degree AV Block — Mobitz II",
         category="av_block", difficulty=3,
         generator=lambda: mobitz_ii(75, 3), rate=75, regularity="regularly_irregular",
         key_features=["Fixed PR interval", "Sudden dropped QRS without warning",
                       "P:QRS ratio 3:1", "Often wide QRS"],
         teaching="Fixed PR with unexpected dropped beats. More ominous than Wenckebach — "
                  "below the AV node (His-Purkinje). Often requires permanent pacing."),

    dict(id="avb3_01", rhythm="3rd Degree (Complete) AV Block",
         category="av_block", difficulty=4,
         generator=lambda: third_degree_avb(), rate=33, regularity="regular",
         key_features=["P waves and QRS march out independently",
                       "P rate > QRS rate", "Wide escape QRS",
                       "No fixed relationship between P and QRS"],
         teaching="Complete dissociation — atria and ventricles beat independently. "
                  "A ventricular escape rhythm keeps the patient alive. Requires pacing."),

    # ── Bundle Branch Blocks ──────────────────────────────────────────────────
    dict(id="lbbb_01", rhythm="Left Bundle Branch Block (LBBB)",
         category="bundle_branch", difficulty=3,
         generator=lambda: lbbb(72), rate=72, regularity="regular",
         key_features=["Wide QRS ≥120 ms", "Broad monophasic R in lateral leads",
                       "No septal Q in lateral leads", "Discordant ST-T"],
         teaching="Left ventricle activates late via slow cell-to-cell conduction. "
                  "LBBB invalidates ST analysis — never diagnose ischemia from ST segments in LBBB alone."),

    dict(id="rbbb_01", rhythm="Right Bundle Branch Block (RBBB)",
         category="bundle_branch", difficulty=3,
         generator=lambda: rbbb(75), rate=75, regularity="regular",
         key_features=["Wide QRS ≥120 ms", "RSR' pattern in V1 ('rabbit ears')",
                       "Wide slurred S in lateral leads", "T wave inversion V1–V2"],
         teaching="Delayed right ventricular activation produces the RSR' in V1. "
                  "RBBB can be a normal variant; new RBBB warrants investigation."),

    # ── Junctional / Escape ───────────────────────────────────────────────────
    dict(id="junct_01", rhythm="Junctional Rhythm", category="junctional", difficulty=3,
         generator=lambda: junctional(48), rate=48, regularity="regular",
         key_features=["Rate 40–60 bpm", "Narrow QRS",
                       "Inverted P waves in lead II", "P may be before, during, or after QRS"],
         teaching="AV node serves as pacemaker when SA node fails. "
                  "Retrograde atrial activation produces inverted P waves in lead II."),

    dict(id="junct_02", rhythm="Accelerated Junctional Rhythm",
         category="junctional", difficulty=3,
         generator=lambda: junctional(85), rate=85, regularity="regular",
         key_features=["Rate 60–100 bpm", "Narrow QRS", "Inverted or absent P waves"],
         teaching="Junctional rate exceeds 60 bpm — 'accelerated'. "
                  "Associated with digitalis toxicity, inferior MI, or post-cardiac surgery."),

    dict(id="idio_01", rhythm="Idioventricular Rhythm", category="ventricular", difficulty=3,
         generator=lambda: idioventricular(33), rate=33, regularity="regular",
         key_features=["Rate 20–40 bpm", "Wide bizarre QRS", "No P waves",
                       "Ventricular escape rhythm"],
         teaching="The ventricle's last-resort pacemaker at 20–40 bpm. "
                  "Seen in severe bradycardia, complete heart block, and post-arrest."),

    # ── Life-threatening ──────────────────────────────────────────────────────
    dict(id="vtach_01", rhythm="Ventricular Tachycardia (VTach)",
         category="ventricular", difficulty=3,
         generator=lambda: ventricular_tachycardia(175), rate=175, regularity="regular",
         key_features=["Rate >100 bpm", "Wide QRS ≥120 ms", "Regular",
                       "AV dissociation if P waves visible", "Treat immediately"],
         teaching="Wide-complex, fast, regular tachycardia. "
                  "Any wide-complex tachycardia is VTach until proven otherwise. Treat as VTach."),

    dict(id="vtach_02", rhythm="Ventricular Tachycardia (VTach)",
         category="ventricular", difficulty=3,
         generator=lambda: ventricular_tachycardia(200), rate=200, regularity="regular",
         key_features=["Rate 200 bpm", "Wide QRS", "Regular", "Life-threatening"],
         teaching="Faster VTach at 200 bpm. May degenerate to VFib. "
                  "Immediate synchronized cardioversion if pulse present; defibrillation if pulseless."),

    dict(id="vfib_01", rhythm="Ventricular Fibrillation (VFib)",
         category="ventricular", difficulty=1,
         generator=lambda: ventricular_fibrillation(), rate=None, regularity="chaotic",
         key_features=["Chaotic disorganized waveform", "No identifiable P, QRS, or T",
                       "Amplitude varies", "Cardiac arrest — CPR + defibrillation"],
         teaching="The ventricles quiver without coordinated contraction. "
                  "Immediate defibrillation and high-quality CPR are required. Do not delay."),

    dict(id="asys_01", rhythm="Asystole", category="ventricular", difficulty=1,
         generator=lambda: asystole(), rate=0, regularity="none",
         key_features=["Flat or near-flat line", "No P waves, QRS, or T waves",
                       "Cardiac arrest", "CPR and treat reversible causes"],
         teaching="Absence of electrical activity. Confirm in two leads to rule out fine VFib. "
                  "Treat reversible causes: the Hs and Ts."),

    # ── STEMI ─────────────────────────────────────────────────────────────────
    dict(id="stemi_ant_01", rhythm="Anterior STEMI", category="stemi", difficulty=3,
         multilead=True, generator=lambda: anterior_stemi(80),
         rate=80, regularity="regular",
         key_features=["ST elevation V1–V4 (LAD territory)", "Hyperacute T waves",
                       "Reciprocal ST depression in aVL/inferior leads",
                       "May develop pathological Q waves", "Immediate reperfusion required"],
         teaching="Anterior STEMI is caused by LAD occlusion. ST elevation ≥1mm in 2 contiguous "
                  "precordial leads (V1–V4). Watch for reciprocal depression in aVL. "
                  "The larger the territory, the worse the prognosis."),

    dict(id="stemi_inf_01", rhythm="Inferior STEMI", category="stemi", difficulty=3,
         multilead=True, generator=lambda: inferior_stemi(78),
         rate=78, regularity="regular",
         key_features=["ST elevation in II, III, aVF (RCA territory)",
                       "Reciprocal ST depression in I and aVL",
                       "Check V4R for right ventricular involvement",
                       "Q waves may form in II, III, aVF"],
         teaching="Inferior STEMI is most often caused by RCA occlusion. "
                  "ST elevation in II, III, aVF with reciprocal changes in I and aVL. "
                  "Always get right-sided leads (V4R) to screen for RV infarct."),

    dict(id="stemi_lat_01", rhythm="Lateral STEMI", category="stemi", difficulty=3,
         multilead=True, generator=lambda: lateral_stemi(82),
         rate=82, regularity="regular",
         key_features=["ST elevation in I, aVL, V5–V6 (circumflex territory)",
                       "Reciprocal depression in III and aVF",
                       "Often caused by circumflex (LCx) occlusion",
                       "May be missed without high lateral leads"],
         teaching="Lateral STEMI involves the circumflex artery. ST elevation in I, aVL, V5–V6 "
                  "with reciprocal changes inferiorly. High lateral STEMI (I, aVL only) "
                  "can be subtle — measure carefully."),

    dict(id="stemi_post_01", rhythm="Posterior STEMI", category="stemi", difficulty=4,
         multilead=True, generator=lambda: posterior_stemi(76),
         rate=76, regularity="regular",
         key_features=["ST depression in V1–V3 (reciprocal to posterior elevation)",
                       "Tall broad R wave in V1–V2 (reciprocal to posterior Q)",
                       "No obvious ST elevation on standard 12-lead",
                       "Confirm with posterior leads V7–V9"],
         teaching="Posterior STEMI is a 'hidden' STEMI — the posterior wall isn't covered by "
                  "standard leads. You see its mirror image: ST depression and tall R in V1–V3. "
                  "Flip V2 upside down mentally — it looks like STEMI. Confirm with V7–V9."),

    # ── NSTEMI / ACS ──────────────────────────────────────────────────────────
    dict(id="nstemi_01", rhythm="NSTEMI — ST Depression", category="nstemi", difficulty=3,
         multilead=True, generator=lambda: nstemi_st_depression(88),
         rate=88, regularity="regular",
         key_features=["Horizontal or downsloping ST depression ≥0.5mm",
                       "T wave flattening or inversion",
                       "No ST elevation",
                       "Troponin elevation confirms myocardial injury",
                       "Urgent cardiology consult"],
         teaching="NSTEMI presents with ST depression and/or T wave changes without ST elevation. "
                  "The degree of ST depression correlates with ischemia severity. "
                  "Horizontal or downsloping depression is more specific than upsloping."),

    dict(id="wellens_a_01", rhythm="Wellens Syndrome — Type A", category="nstemi", difficulty=4,
         multilead=True, generator=lambda: wellens_a(72),
         rate=72, regularity="regular",
         key_features=["Biphasic T waves in V2–V3 (positive then negative)",
                       "Minimal or no ST elevation",
                       "Usually pain-free at time of ECG",
                       "Indicates critical proximal LAD stenosis",
                       "Do NOT stress test — high risk of anterior STEMI"],
         teaching="Wellens Syndrome indicates critical proximal LAD stenosis between pain episodes. "
                  "Type A: biphasic T waves in V2–V3. Type B: deep symmetric inversions. "
                  "These patients are at imminent risk of massive anterior STEMI — do not discharge."),

    dict(id="wellens_b_01", rhythm="Wellens Syndrome — Type B", category="nstemi", difficulty=4,
         multilead=True, generator=lambda: wellens_b(68),
         rate=68, regularity="regular",
         key_features=["Deep symmetric T wave inversion in V2–V3",
                       "No significant ST elevation",
                       "Normal or minimally elevated troponin",
                       "Critical proximal LAD stenosis — do NOT stress test"],
         teaching="Wellens Type B shows deep symmetric T inversions in V2–V3 during pain-free periods. "
                  "This is a pre-infarction pattern. The patient needs urgent cath, not observation. "
                  "A negative troponin does not rule out the danger."),

    # ── Pulmonary Embolism ────────────────────────────────────────────────────
    dict(id="pe_s1q3t3_01", rhythm="Pulmonary Embolism — S1Q3T3", category="pe_strain", difficulty=4,
         multilead=True, generator=lambda: pe_s1q3t3(108),
         rate=108, regularity="regular",
         key_features=["Sinus tachycardia (most common ECG finding in PE)",
                       "S wave in lead I (S1)",
                       "Q wave + T wave inversion in lead III (Q3T3)",
                       "RV strain in V1 — T inversion, partial RBBB",
                       "S1Q3T3 is specific but only present in ~20% of PE"],
         teaching="S1Q3T3 is the classic ECG pattern of massive PE but is neither sensitive nor specific. "
                  "Sinus tachycardia is the most common finding. The pattern reflects acute right "
                  "heart strain from sudden pulmonary hypertension. Always correlate with clinical picture."),

    dict(id="pe_rv_strain_01", rhythm="Pulmonary Embolism — RV Strain", category="pe_strain", difficulty=3,
         multilead=True, generator=lambda: pe_rv_strain(112),
         rate=112, regularity="regular",
         key_features=["T wave inversions in V1–V4 (right precordial)",
                       "Sinus tachycardia",
                       "May have new RBBB",
                       "Indicates significant RV pressure overload",
                       "More common than classic S1Q3T3"],
         teaching="Right precordial T inversions (V1–V4) with tachycardia are the most common "
                  "ECG manifestation of significant PE. They reflect RV strain from elevated "
                  "pulmonary pressures. New RBBB in this context is a high-risk finding."),

    # ── Strain Patterns ───────────────────────────────────────────────────────
    dict(id="lv_strain_01", rhythm="LVH with Strain Pattern", category="pe_strain", difficulty=3,
         multilead=True, generator=lambda: lv_strain(72),
         rate=72, regularity="regular",
         key_features=["Tall R wave in V5–V6 (LVH voltage criteria)",
                       "Deep S wave in V1 (Sokolow: SV1 + RV5 ≥35mm)",
                       "ST depression + T wave inversion in lateral leads",
                       "Strain pattern = pressure overload (hypertension, aortic stenosis)",
                       "Do not confuse with ischemia"],
         teaching="The LV strain pattern — asymmetric ST depression with T inversion in lateral leads "
                  "— accompanies LVH in pressure-overloaded ventricles (hypertension, AS). "
                  "It differs from ischemic ST changes by its gradual upslope and asymmetric T wave."),

    dict(id="rv_strain_01", rhythm="RV Strain Pattern", category="pe_strain", difficulty=3,
         multilead=True, generator=lambda: rv_strain_pattern(90),
         rate=90, regularity="regular",
         key_features=["T wave inversions in V1–V3 (right precordial)",
                       "May extend to V4",
                       "Right axis deviation on full 12-lead",
                       "Causes: PE, pulmonary hypertension, cor pulmonale, RVOT obstruction"],
         teaching="Right precordial T inversions indicate RV pressure overload. "
                  "Unlike anterior ischemia (which also inverts precordial T waves), RV strain "
                  "is associated with right axis deviation and clinical signs of RV failure."),

    # ── Pacemaker Rhythms ─────────────────────────────────────────────────────
    dict(id="pace_atrial_01", rhythm="Atrial Pacing (AAI)", category="pacemaker", difficulty=2,
         generator=lambda: atrial_paced(70),
         rate=70, regularity="regular",
         key_features=["Pacing spike immediately before each P wave",
                       "Normal PR interval (patient's own AV conduction)",
                       "Narrow QRS (native ventricular conduction preserved)",
                       "Paced P wave may have different morphology than sinus P",
                       "Failure to capture: spike without P wave"],
         teaching="Atrial pacing (AAI mode) fires in the atrium and relies on intact AV conduction. "
                  "Each beat shows an atrial spike followed by a P wave and narrow QRS. "
                  "It maintains AV synchrony and is used for sick sinus syndrome with normal AV node."),

    dict(id="pace_ventricular_01", rhythm="Ventricular Pacing (VVI)", category="pacemaker", difficulty=2,
         generator=lambda: ventricular_paced(70),
         rate=70, regularity="regular",
         key_features=["Pacing spike immediately before each QRS",
                       "Wide, bizarre QRS with LBBB morphology (RV apex stimulation)",
                       "Discordant ST-T changes (opposite to QRS deflection)",
                       "No consistent P wave before each QRS",
                       "Left axis deviation typical"],
         teaching="Ventricular pacing (VVI mode) stimulates the RV apex, producing an LBBB-like wide QRS. "
                  "The pacing spike immediately precedes each QRS. There are no P waves coordinated with "
                  "the paced beats — AV synchrony is lost. Look for the telltale spike before the wide complex."),

    dict(id="pace_av_01", rhythm="AV Sequential Pacing (DDD)", category="pacemaker", difficulty=3,
         generator=lambda: av_paced(70),
         rate=70, regularity="regular",
         key_features=["Two pacing spikes per beat: atrial spike then ventricular spike",
                       "First spike precedes P wave (atrial); second precedes QRS (ventricular)",
                       "Wide QRS with LBBB morphology",
                       "AV synchrony maintained — paced PR interval programmed",
                       "Most physiological pacing mode"],
         teaching="DDD pacing is dual-chamber: the atrium and ventricle are both paced. "
                  "Look for two spikes per beat — an atrial spike before the P wave and a ventricular spike "
                  "before the wide QRS. The programmable AV delay preserves atrial contribution to cardiac output."),

    # ── Channelopathies ───────────────────────────────────────────────────────
    dict(id="brugada_01", rhythm="Brugada Syndrome — Type 1", category="channelopathy", difficulty=4,
         multilead=True, generator=lambda: brugada_type1_strip(72),
         rate=72, regularity="regular",
         key_features=["Coved ST elevation ≥2mm in V1–V2 (Type 1 pattern)",
                       "Downsloping ST with terminal T-wave inversion",
                       "RBBB-like QRS morphology (rSR' or r' in V1)",
                       "Normal QTc, no ischemia elsewhere",
                       "Can precipitate ventricular fibrillation"],
         teaching="Brugada syndrome is a sodium channelopathy (SCN5A) causing sudden cardiac death risk. "
                  "Type 1 (coved) is the only diagnostic pattern: ≥2mm coved ST elevation in ≥1 right "
                  "precordial lead (V1–V2 in standard position or V1–V2 one intercostal space higher). "
                  "Can be spontaneous or unmasked by fever, Na-channel blockers, or cocaine. "
                  "Treat symptomatic patients with an ICD. Screen all first-degree relatives."),

    dict(id="wpw_01", rhythm="Wolff-Parkinson-White (WPW)", category="channelopathy", difficulty=3,
         generator=lambda: wpw_strip(72),
         rate=72, regularity="regular",
         key_features=["Short PR interval (<120 ms)",
                       "Delta wave (slurred upstroke on QRS)",
                       "Wide QRS (≥120 ms) due to ventricular pre-excitation",
                       "Secondary ST-T changes discordant to delta wave",
                       "Risk of SVT, atrial fibrillation, and sudden death"],
         teaching="WPW results from an accessory pathway (Bundle of Kent) bypassing the AV node. "
                  "Pre-excitation produces the triad: short PR, delta wave, and wide QRS. "
                  "The danger is AFib conducting rapidly down the pathway — can degenerate to VF. "
                  "Avoid AV nodal blockers (adenosine, beta-blockers, digoxin) in AFib with WPW. "
                  "Definitive treatment is catheter ablation of the accessory pathway."),

    dict(id="lngqt_01", rhythm="Long QT Syndrome", category="channelopathy", difficulty=3,
         generator=lambda: long_qt_strip(68),
         rate=68, regularity="regular",
         key_features=["QTc >500 ms (markedly prolonged)",
                       "Normal P wave and QRS",
                       "T wave may be broad, notched, or biphasic",
                       "Risk of Torsades de Pointes (TdP)",
                       "Triggered by bradycardia, hypokalemia, or QT-prolonging drugs"],
         teaching="Long QT syndrome predisposes to Torsades de Pointes — a polymorphic VT that can "
                  "cause syncope or degenerate to VF. The corrected QT (QTc = QT / √RR) >500 ms is "
                  "high risk. Causes: congenital (LQTS1-3), electrolyte abnormalities (↓K, ↓Mg), "
                  "and drugs (antiarrhythmics, antipsychotics, antibiotics). "
                  "Treat: correct electrolytes, remove offending drugs, magnesium IV for TdP, ICD for congenital LQTS."),
]


# ── Review cases (not yet in cases.json — awaiting approval) ─────────────────
REVIEW_CASES = [

    dict(id="hyperkal_01", rhythm="Hyperkalemia", category="electrolyte", difficulty=3,
        review=True, generator=lambda: hyperkalemia_strip(65),
        rate=65, regularity="regular",
        key_features=["Absent P waves (flat or invisible)",
                   "Widened QRS complex (≥120 ms)",
                   "Very tall, narrow, symmetric ('tented') T waves",
                   "Shortened QT interval",
                   "Progressive sine-wave QRS pattern at severe K+ levels"],
        teaching="Hyperkalemia produces a sequential ECG progression. Early changes: peaked tented T waves. "
               "Moderate: P wave flattening/disappearance, widening QRS. Severe: sine-wave pattern, VF risk. "
               "The tented T is characteristically narrow and symmetric — unlike the broad T of ischemia. "
               "Treat urgently: IV calcium (stabilises membrane), insulin + glucose, sodium bicarb, dialysis."),

    dict(id="lae_01", rhythm="Left Atrial Enlargement (LAE)", category="structural", difficulty=2,
        review=True, generator=lambda: lae_strip(70),
        rate=70, regularity="regular",
        key_features=["Broad, notched (M-shaped) P wave in Lead II (P mitrale)",
                   "P wave duration ≥ 120 ms (≥ 3 small squares)",
                   "Biphasic P in V1 with deep wide negative terminal deflection",
                   "Associated with mitral valve disease, hypertension",
                   "Often co-exists with atrial fibrillation or flutter"],
        teaching="LAE prolongs left-atrial depolarisation, producing a bifid (M-shaped) P wave in Lead II "
               "called P mitrale (duration ≥120 ms). In V1, the terminal component is negative (wide and deep), "
               "reflecting delayed LA depolarisation. Common causes: mitral stenosis, hypertension, "
               "dilated cardiomyopathy. Patients with LAE are at high risk for atrial fibrillation."),

    dict(id="rae_01", rhythm="Right Atrial Enlargement (RAE)", category="structural", difficulty=2,
        review=True, generator=lambda: rae_strip(72),
        rate=72, regularity="regular",
        key_features=["Tall, peaked P wave ≥ 0.25 mV (2.5 mm) in II, III, aVF — P pulmonale",
                   "P wave duration normal (< 120 ms) — amplitude is the hallmark",
                   "Also peaked P in V1–V2",
                   "Associated with pulmonary hypertension, COPD, pulmonary stenosis",
                   "Often seen with right ventricular hypertrophy"],
        teaching="RAE enlarges the right atrium, making right-atrial depolarisation dominate the P vector. "
               "The result is a tall, narrow, peaked P wave (P pulmonale) ≥2.5 mm in II, III, aVF. "
               "Duration is normal (<120 ms) because only amplitude is affected — unlike LAE where duration "
               "is prolonged. Causes: cor pulmonale, COPD, pulmonary hypertension, tricuspid stenosis."),

    dict(id="lafb_01", rhythm="Left Anterior Fascicular Block (LAFB)", category="conduction", difficulty=3,
        review=True, generator=lambda: lafb_strip(70),
        rate=70, regularity="regular",
        key_features=["Left axis deviation (−45° to −90°) — the key criterion",
                   "rS pattern in II, III, aVF (small r, deep S)",
                   "qR pattern in I and aVL (small q, tall R)",
                   "Narrow QRS (< 120 ms) — not a bundled branch block",
                   "No other cause of LAD (inferior MI, hyperkalemia) present"],
        teaching="LAFB blocks the anterior fascicle of the left bundle, redirecting ventricular activation "
               "superiorly and leftward. The axis shifts to −45° to −90° (left axis deviation). "
               "In Lead II: small initial r then deep S (rS). In Leads I and aVL: small q then tall R (qR). "
               "QRS is narrow (<120 ms) — distinguish from LBBB. Causes: CAD, cardiomyopathy, hypertension."),

    dict(id="bigu_01", rhythm="Ventricular Bigeminy", category="ventricular", difficulty=2,
        review=True, generator=lambda: bigeminy_strip(72),
        rate=72, regularity="regular",
        key_features=["Every other beat is a PVC (alternating sinus-PVC pattern)",
                   "PVC: wide, bizarre QRS > 120 ms; no preceding P wave",
                   "Compensatory pause after each PVC",
                   "Short coupling interval (< 70 % of RR) from sinus to PVC",
                   "Underlying rate often appears slow due to bigeminal pauses"],
        teaching="Bigeminy describes a pattern where every other beat is ectopic. In ventricular bigeminy, "
               "a narrow-complex sinus beat alternates with a wide-complex PVC. The PVC couples at ~55–65 % "
               "of the sinus RR, followed by a compensatory pause. Causes: structural heart disease, CAD, "
               "hypokalemia, digoxin toxicity, stimulants. Treat the underlying cause; beta-blockers if symptomatic."),

    dict(id="trigu_01", rhythm="Ventricular Trigeminy", category="ventricular", difficulty=2,
        review=True, generator=lambda: trigeminy_strip(70),
        rate=70, regularity="regular",
        key_features=["Every third beat is a PVC (sinus-sinus-PVC pattern repeats)",
                   "PVC: wide, bizarre QRS > 120 ms; no preceding P wave",
                   "Compensatory pause after each PVC maintains underlying sinus rate",
                   "Two normal narrow complexes precede each wide complex",
                   "Effective ventricular rate lower than the underlying sinus rate"],
        teaching="Trigeminy describes a grouping of three beats: two sinus beats followed by one PVC, "
               "repeating throughout the tracing. The PVC fires prematurely after the second sinus beat, "
               "followed by a compensatory pause. Same causes as bigeminy: structual disease, electrolyte "
               "imbalance (hypokalemia, hypomagnesemia), digoxin toxicity. Treatment: address the underlying trigger."),
]

CASES = CASES + REVIEW_CASES


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--render-style',
        type=str,
        default='house',
        choices=sorted(RENDER_STYLES.keys()),
        help='Rendering palette/style for PNG outputs (default: house)'
    )
    args = parser.parse_args()
    
    np.random.seed(0)
    metadata = []

    print(f"\nGenerating {len(CASES)} EKG cases → {CASES_DIR}\n")

    for case in CASES:
        out_path = CASES_DIR / f"{case['id']}.png"
        output = case["generator"]()
        if case.get("multilead"):
            render_multilead(output, case["rhythm"], out_path, render_style=args.render_style)
        else:
            render(output, case["rhythm"], out_path, render_style=args.render_style)

        metadata.append({
            "id":              case["id"],
            "rhythm":          case["rhythm"],
            "category":        case["category"],
            "difficulty":      case["difficulty"],
            "imagePath":       f"/cases/{case['id']}.png",
            "twelveleadPath":  f"/cases/{case['id']}_12lead.png",
            "rate":            case["rate"],
            "regularity":      case["regularity"],
            "keyFeatures":     case["key_features"],
            "teaching":        case["teaching"],
        })

    live_count = 0
    review_count = 0
    REVIEW_DIR = CASES_DIR / "review"
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)

    for case in CASES:
        is_review = case.get("review", False)
        out_dir = REVIEW_DIR if is_review else CASES_DIR
        out_path = out_dir / f"{case['id']}.png"
        output = case["generator"]()
        if case.get("multilead"):
            render_multilead(output, case["rhythm"], out_path, render_style=args.render_style)
        else:
            render(output, case["rhythm"], out_path, render_style=args.render_style)

        if is_review:
            review_count += 1
            print(f"  ⏳  {case['id']:<28} → review/  (awaiting approval)")
        else:
            live_count += 1
            metadata.append({
                "id":              case["id"],
                "rhythm":          case["rhythm"],
                "category":        case["category"],
                "difficulty":      case["difficulty"],
                "imagePath":       f"/cases/{case['id']}.png",
                "twelveleadPath":  f"/cases/{case['id']}_12lead.png",
                "rate":            case["rate"],
                "regularity":      case["regularity"],
                "keyFeatures":     case["key_features"],
                "teaching":        case["teaching"],
            })

    out = DATA_DIR / "cases.json"
    out.write_text(json.dumps(metadata, indent=2))
    print(f"\n✓  Wrote {live_count} live entries to {out}")
    if review_count:
        print(f"⏳  {review_count} review strip(s) → {REVIEW_DIR}")
    print("Done.\n")


if __name__ == "__main__":
    main()
