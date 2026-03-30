#!/usr/bin/env python3
"""
Full 12-lead EKG Synthesizer for EKGTrainer
Generates standard 4×3+strip PNGs for all 37 teaching cases,
replacing the existing single/multi-lead strips.

Usage (from repo root):
    pip install -r scripts/requirements.txt
    python3 scripts/generate_12lead_ekgs.py
"""

import math
import warnings
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

warnings.filterwarnings('ignore')
np.random.seed(42)

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT    = Path(__file__).parent.parent
OUT_DIR = ROOT / "web" / "public" / "cases"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Signal parameters ─────────────────────────────────────────────────────────
SR  = 500
DUR = 10.0
N   = int(SR * DUR)
T   = np.linspace(0, DUR, N)

# ── Paper style ───────────────────────────────────────────────────────────────
BG, MINOR, MAJOR, TRACE = "#FFF5E6", "#FFBBBB", "#EE6666", "#111111"

# ── Lead definitions ──────────────────────────────────────────────────────────
ALL_LEADS = ["I", "II", "III", "aVR", "aVL", "aVF",
             "V1", "V2", "V3", "V4", "V5", "V6"]
PRECORDIAL = ["V1", "V2", "V3", "V4", "V5", "V6"]
FRONTAL    = ["I", "II", "III", "aVR", "aVL", "aVF"]

# Frontal lead axes (degrees, Einthoven/Goldberger standard)
LEAD_AX = {"I": 0, "II": 60, "III": 120, "aVR": -150, "aVL": -30, "aVF": 90}

# Standard 4×3 layout: each cell = (lead_name, col_index)
# col_index determines time window: col * 2.5s → (col+1) * 2.5s
COL_W = 2.5  # seconds per column
LAYOUT = [
    [("I", 0),   ("aVR", 1), ("V1", 2), ("V4", 3)],
    [("II", 0),  ("aVL", 1), ("V2", 2), ("V5", 3)],
    [("III", 0), ("aVF", 1), ("V3", 2), ("V6", 3)],
]


# ═══════════════════════════════════════════════════════════════════════════════
# Waveform primitives
# ═══════════════════════════════════════════════════════════════════════════════

def gauss(center, fwhm_ms, amp):
    """Return Gaussian bump on the global time array T."""
    sigma = (fwhm_ms / 1000.0) / 2.3548
    return amp * np.exp(-0.5 * ((T - center) / sigma) ** 2)


def _proj(axis_deg, lead):
    """Cosine projection of a frontal cardiac vector onto a frontal lead."""
    return math.cos(math.radians(axis_deg - LEAD_AX[lead]))


def _sigmoid(x):
    return 1.0 / (1.0 + math.exp(-float(x)))


def _precordial_r(v_num, transition=3.5, peak=1.0):
    """R-wave amplitude for precordial lead V{v_num} (1-6), sigmoid transition."""
    return peak * _sigmoid((v_num - transition) / 1.2)


def _precordial_s(v_num, transition=3.5, peak=0.75):
    """S-wave amplitude for precordial lead V{v_num} (1-6), inverse sigmoid."""
    return peak * (1.0 - _sigmoid((v_num - transition) / 1.2))


# ═══════════════════════════════════════════════════════════════════════════════
# Beat placement on a signal array
# ═══════════════════════════════════════════════════════════════════════════════

def place_beat(sig, r_at, *,
               pr_ms=160, qrs_ms=80, qt_ms=380,
               p_amp=0.15, p_inv=False, no_p=False,
               r_amp=1.0, q_frac=0.08, s_frac=0.15,
               st=0.0, t_amp=0.30, t_inv=False,
               big_q=False,
               # morphology flags (mutually exclusive):
               qs=False,      # QS pattern (no positive R)
               broad_r=False, # LBBB-style broad monophasic R
               rsrp=False,    # RBBB-style RSR' triphasic
               wide_neg=False,  # wide negative (e.g. LBBB in V1)
               delta=False):  # delta wave pre-excitation
    """Add one PQRST complex to `sig` at `r_at` seconds."""
    # P wave
    if not no_p:
        p_c = r_at - pr_ms / 1000.0 + 0.040
        sig += gauss(p_c, 45, (-1 if p_inv else 1) * p_amp)

    hw = qrs_ms / 1000.0 / 2

    if qs:                        # QS — purely negative, no R
        sig += gauss(r_at - hw * 0.3, qrs_ms * 0.45, -0.50 * r_amp)
        sig += gauss(r_at + hw * 0.5, qrs_ms * 0.40, -0.25 * r_amp)
    elif wide_neg:                # Broad negative (LBBB in V1-V3)
        sig += gauss(r_at,       130, -r_amp)
        sig += gauss(r_at + 0.070, 28,  0.04 * r_amp)
    elif broad_r:                 # LBBB lateral — broad notched R
        sig += gauss(r_at + 0.018, 120,  r_amp)
        sig += gauss(r_at + 0.075, 25,  -0.04 * r_amp)  # notch
    elif rsrp:                    # RBBB — R, S, R'
        sig += gauss(r_at - 0.010, 20, -0.07 * r_amp)   # q
        sig += gauss(r_at,          28,  0.85 * r_amp)   # R
        sig += gauss(r_at + 0.040,  22, -0.35 * r_amp)  # S
        sig += gauss(r_at + 0.082,  30,  0.50 * r_amp)  # R'
    elif delta:                   # Pre-excitation: short PR, slurred onset
        sig += gauss(r_at - 0.040, 40,  0.30 * r_amp)   # delta wave
        sig += gauss(r_at + 0.015, qrs_ms * 0.40, r_amp)
        sig += gauss(r_at + hw * 0.9, qrs_ms * 0.30, -s_frac * r_amp)
    else:                         # Normal narrow QRS
        if big_q:
            sig += gauss(r_at - 0.048, 38, -0.38 * r_amp)
        else:
            sig += gauss(r_at - hw * 0.4, qrs_ms * 0.25, -q_frac * r_amp)
        sig += gauss(r_at,               qrs_ms * 0.45,   r_amp)
        sig += gauss(r_at + hw * 0.7,    qrs_ms * 0.30,  -s_frac * r_amp)

    # ST offset (Gaussian centred in ST segment)
    if abs(st) > 0.004:
        sig += gauss(r_at + 0.210, 175, st * 0.72)

    # T wave
    t_c = r_at + qt_ms / 1000.0 * 0.63
    sig += gauss(t_c, 100, (-1 if t_inv else 1) * abs(t_amp))


def build_lead(r_times, **kw):
    """Build a 10-second signal for one lead given a list of R positions."""
    sig = np.zeros(N)
    for r in r_times:
        if 0.08 < r < DUR - 0.12:
            place_beat(sig, r, **kw)
    return sig


def rr(hr, start=0.30):
    return list(np.arange(start, DUR - 0.10, 60.0 / hr))


# ═══════════════════════════════════════════════════════════════════════════════
# 12-lead builders — one function per rhythm family
# Returns dict {lead_name: np.ndarray}
# ═══════════════════════════════════════════════════════════════════════════════

def _normal_base(r_times, qrs_axis=60, pr_ms=160, qrs_ms=80, qt_ms=380,
                 p_amp=0.15, no_p=False, p_inv_inferior=False,
                 extra=None):
    """
    Build a 'normal-morphology' 12-lead from a list of R-wave times.
    extra: dict of {lead: {kwarg: value}} for per-lead overrides.
    """
    if extra is None:
        extra = {}

    leads = {}

    # ── Frontal leads via axis projection ────────────────────────────────────
    for lead in FRONTAL:
        c = _proj(qrs_axis, lead)
        kw = dict(pr_ms=pr_ms, qrs_ms=qrs_ms, qt_ms=qt_ms,
                  p_amp=p_amp, no_p=no_p)

        if lead == "aVR":
            # Always: QS, inverted P, inverted T
            kw.update(r_amp=0.80, qs=True, p_inv=True, t_inv=True, t_amp=0.20)
        elif c >= 0.6:   # strongly positive (II for axis=60°)
            kw.update(r_amp=c, q_frac=0.06, s_frac=0.12, t_amp=0.30 * c)
        elif c >= 0.1:   # moderately positive
            kw.update(r_amp=max(c, 0.35), q_frac=0.08, s_frac=0.18, t_amp=0.22 * max(c, 0.35))
        elif c >= -0.1:  # near-isoelectric (aVL at axis=60°)
            kw.update(r_amp=0.25, q_frac=0.25, s_frac=0.30, t_amp=0.08)
        else:            # negative
            kw.update(r_amp=abs(c) * 0.7, qs=(c < -0.4),
                      t_inv=(c < -0.5), t_amp=abs(c) * 0.18)

        if p_inv_inferior and lead in ("II", "III", "aVF"):
            kw['p_inv'] = True

        kw.update(extra.get(lead, {}))
        leads[lead] = build_lead(r_times, **kw)

    # ── Precordial leads via transition zone ─────────────────────────────────
    for v_num, lead in enumerate(PRECORDIAL, start=1):
        r_a = _precordial_r(v_num)
        s_a = _precordial_s(v_num)
        kw = dict(pr_ms=pr_ms, qrs_ms=qrs_ms, qt_ms=qt_ms,
                  p_amp=p_amp, no_p=no_p,
                  r_amp=r_a, s_frac=s_a / max(r_a, 0.01),
                  t_amp=max(0.12, 0.28 * r_a))
        if v_num == 1:
            kw.update(p_amp=p_amp * 0.8)   # V1 P wave often smaller/biphasic
        kw.update(extra.get(lead, {}))
        leads[lead] = build_lead(r_times, **kw)

    return leads


# ─────────────────────────────────────────────────────────────────────────────
# Sinus Rhythms
# ─────────────────────────────────────────────────────────────────────────────

def nsr(hr=75, pr_ms=160):
    return _normal_base(rr(hr), pr_ms=pr_ms)


def sinus_arrhythmia(base_hr=68):
    r_list, r, cycle = [], 0.30, 0
    rr_base = 60.0 / base_hr
    while r < DUR - 0.20:
        r_list.append(r)
        r += rr_base + 0.15 * rr_base * math.sin(2 * math.pi * cycle / 6)
        cycle += 1
    return _normal_base(r_list)


# ─────────────────────────────────────────────────────────────────────────────
# Ectopic beats
# ─────────────────────────────────────────────────────────────────────────────

def with_pacs(hr=70):
    """NSR with 2 PACs — slightly different P morphology, narrow QRS."""
    r_list = rr(hr)
    rr_int = 60.0 / hr
    pac_r = sorted({r_list[3] + rr_int * 0.65,
                    r_list[7] + rr_int * 0.65} if len(r_list) > 8 else {r_list[3] + rr_int * 0.65})
    skip = {r_list[3] + rr_int, r_list[7] + rr_int} if len(r_list) > 8 else {r_list[3] + rr_int}
    all_r = sorted([r for r in r_list if not any(abs(r - s) < 0.05 for s in skip)] + list(pac_r))

    leads = {}
    for lead in FRONTAL:
        c = _proj(60, lead)
        normal_kw = dict(pr_ms=160, qrs_ms=80, qt_ms=380,
                         p_amp=0.15, r_amp=max(c, 0.25) if c > 0 else 0.20,
                         s_frac=0.15, t_amp=0.22)
        if lead == "aVR":
            normal_kw.update(r_amp=0.80, qs=True, p_inv=True, t_inv=True, t_amp=0.20)
        sig = np.zeros(N)
        for r in all_r:
            if 0.08 < r < DUR - 0.12:
                kw = dict(normal_kw)
                if r in pac_r:
                    kw.update(pr_ms=110, p_amp=0.24)  # PAC: shorter PR, different P
                place_beat(sig, r, **kw)
        leads[lead] = sig

    for v_num, lead in enumerate(PRECORDIAL, start=1):
        r_a = _precordial_r(v_num)
        s_a = _precordial_s(v_num)
        sig = np.zeros(N)
        for r in all_r:
            if 0.08 < r < DUR - 0.12:
                kw = dict(pr_ms=160, qrs_ms=80, qt_ms=380,
                          p_amp=0.12, r_amp=r_a, s_frac=s_a/max(r_a,0.01), t_amp=max(0.12, 0.28*r_a))
                if r in pac_r:
                    kw.update(pr_ms=110, p_amp=0.22)
                place_beat(sig, r, **kw)
        leads[lead] = sig
    return leads


def with_pvcs(hr=70):
    """NSR with 2 PVCs — wide bizarre QRS, no P, full comp pause."""
    r_list = rr(hr)
    rr_int = 60.0 / hr
    pvc_times = {r_list[3], r_list[7]} if len(r_list) > 8 else {r_list[3]}
    skip_after = {r + rr_int for r in pvc_times}

    def is_skipped(r):
        return any(abs(r - s) < 0.06 for s in skip_after)

    leads = {}
    # Limb: PVC is wide negative in most leads except aVR
    for lead in FRONTAL:
        c = _proj(60, lead)
        sig = np.zeros(N)
        for r in r_list:
            if 0.08 < r < DUR - 0.12:
                if r in pvc_times:
                    # PVC: wide, bizarre, negative in inferior leads (inferior axis)
                    if lead in ("II", "III", "aVF"):
                        place_beat(sig, r, no_p=True, qrs_ms=140, qt_ms=440,
                                   r_amp=0.10, s_frac=8.0, t_amp=0.30, t_inv=False)
                    elif lead == "aVR":
                        place_beat(sig, r, no_p=True, qrs_ms=140, qt_ms=440,
                                   r_amp=0.90, qs=False, s_frac=0.10, t_inv=True, t_amp=0.25)
                    else:
                        place_beat(sig, r, no_p=True, qrs_ms=140, qt_ms=440,
                                   r_amp=max(abs(c), 0.30), s_frac=0.40, t_inv=True, t_amp=0.22)
                elif not is_skipped(r):
                    if lead == "aVR":
                        place_beat(sig, r, r_amp=0.80, qs=True, p_inv=True, t_inv=True, t_amp=0.20)
                    else:
                        place_beat(sig, r, r_amp=max(c, 0.25) if c > 0 else 0.20, t_amp=0.22)
        leads[lead] = sig

    for v_num, lead in enumerate(PRECORDIAL, start=1):
        r_a = _precordial_r(v_num)
        sig = np.zeros(N)
        for r in r_list:
            if 0.08 < r < DUR - 0.12:
                if r in pvc_times:
                    # PVC in precordial: tall positive in right (V1-V3), wide negative in left
                    if v_num <= 3:
                        place_beat(sig, r, no_p=True, qrs_ms=140, qt_ms=440,
                                   r_amp=1.1, s_frac=0.10, t_inv=True, t_amp=0.28)
                    else:
                        place_beat(sig, r, no_p=True, qrs_ms=140, qt_ms=440,
                                   r_amp=0.15, s_frac=5.0, t_amp=0.30)
                elif not is_skipped(r):
                    s_a = _precordial_s(v_num)
                    place_beat(sig, r, r_amp=r_a, s_frac=s_a/max(r_a,0.01), t_amp=max(0.12,0.28*r_a))
        leads[lead] = sig
    return leads


# ─────────────────────────────────────────────────────────────────────────────
# SVT
# ─────────────────────────────────────────────────────────────────────────────

def svt(hr=190):
    return _normal_base(rr(hr), pr_ms=160, p_amp=0.0, no_p=True,
                        extra={lead: {"t_amp": 0.20} for lead in ALL_LEADS})


# ─────────────────────────────────────────────────────────────────────────────
# Atrial arrhythmias
# ─────────────────────────────────────────────────────────────────────────────

def atrial_fibrillation(avg_hr=80):
    """AFib: irregular R-R, no P waves, fibrillatory baseline."""
    r_list = []
    r = 0.35
    while r < DUR - 0.20:
        r_list.append(r)
        r += (60.0 / avg_hr) * np.random.lognormal(0, 0.22)

    def _flutter_baseline():
        fb = np.zeros(N)
        for f in np.random.uniform(350, 600, 14):
            fb += np.random.uniform(0.02, 0.05) * np.sin(
                2 * math.pi * (f / 60) * T + np.random.uniform(0, 2 * math.pi))
        return fb

    leads = {}
    for lead in FRONTAL:
        c = _proj(60, lead)
        sig = _flutter_baseline()
        for r in r_list:
            if 0.08 < r < DUR - 0.12:
                if lead == "aVR":
                    place_beat(sig, r, no_p=True, r_amp=0.75, qs=True, t_inv=True, t_amp=0.18)
                else:
                    r_a = max(c, 0.25) if c > 0.05 else max(abs(c) * 0.5, 0.20)
                    place_beat(sig, r, no_p=True, r_amp=r_a, s_frac=0.15, t_amp=0.20)
        leads[lead] = sig

    for v_num, lead in enumerate(PRECORDIAL, start=1):
        r_a = _precordial_r(v_num)
        s_a = _precordial_s(v_num)
        sig = _flutter_baseline()
        for r in r_list:
            if 0.08 < r < DUR - 0.12:
                place_beat(sig, r, no_p=True, r_amp=r_a, s_frac=s_a/max(r_a,0.01),
                           t_amp=max(0.12, 0.25 * r_a))
        leads[lead] = sig
    return leads


def atrial_flutter(flutter_rate=300, ratio=2):
    """Flutter: sawtooth at 300 bpm, regular ventricular rate."""
    v_rate = flutter_rate / ratio
    flutter_period = 60.0 / flutter_rate
    v_r = rr(v_rate)

    def _sawtooth():
        fb = np.zeros(N)
        for f_start in np.arange(0.1, DUR, flutter_period):
            mask = (T >= f_start) & (T < f_start + flutter_period)
            fb[mask] += -0.22 * ((T[mask] - f_start) / flutter_period - 0.5)
        return fb

    leads = {}
    for lead in FRONTAL:
        c = _proj(60, lead)
        # Sawtooth most prominent in II, III, aVF; inverted in aVR, aVL
        if lead in ("II", "III", "aVF"):
            flutter_amp = 1.0
        elif lead in ("aVR", "aVL"):
            flutter_amp = -0.5
        else:  # I
            flutter_amp = 0.2
        sig = _sawtooth() * flutter_amp
        for r in v_r:
            if 0.08 < r < DUR - 0.12:
                if lead == "aVR":
                    place_beat(sig, r, no_p=True, r_amp=0.75, qs=True, t_inv=True, t_amp=0.18)
                else:
                    r_a = max(c, 0.30) if c > 0.05 else 0.20
                    place_beat(sig, r, no_p=True, r_amp=r_a, s_frac=0.12, t_amp=0.18)
        leads[lead] = sig

    for v_num, lead in enumerate(PRECORDIAL, start=1):
        r_a = _precordial_r(v_num)
        s_a = _precordial_s(v_num)
        # Flutter less visible in precordial
        amp = 0.15 if v_num <= 2 else 0.05
        sig = _sawtooth() * amp
        for r in v_r:
            if 0.08 < r < DUR - 0.12:
                place_beat(sig, r, no_p=True, r_amp=r_a, s_frac=s_a/max(r_a,0.01),
                           t_amp=max(0.12, 0.22 * r_a))
        leads[lead] = sig
    return leads


# ─────────────────────────────────────────────────────────────────────────────
# AV Blocks
# ─────────────────────────────────────────────────────────────────────────────

def first_degree_avb(hr=70, pr_ms=280):
    return _normal_base(rr(hr), pr_ms=pr_ms)


def mobitz_i(base_hr=75):
    """Wenckebach: PR lengthens 160→210→260→300, then dropped beat."""
    pr_cycle = [160, 210, 260, 300]
    r_list, p_only_list = [], []
    r, beat = 0.40, 0
    while r < DUR - 0.30:
        idx = beat % (len(pr_cycle) + 1)
        if idx == len(pr_cycle):
            p_only_list.append(r)
            r += (60.0 / base_hr) * 1.10
        else:
            r_list.append((r, pr_cycle[idx]))
            r += 60.0 / base_hr
        beat += 1

    leads = {}
    for lead in FRONTAL:
        c = _proj(60, lead)
        sig = np.zeros(N)
        for p_t in p_only_list:
            p_c = p_t - 0.160 + 0.040
            if lead == "aVR":
                sig += gauss(p_c, 45, -0.14)
            else:
                sig += gauss(p_c, 45, 0.14)
        for (r_at, pr_ms) in r_list:
            if lead == "aVR":
                place_beat(sig, r_at, pr_ms=pr_ms, r_amp=0.78, qs=True,
                           p_inv=True, t_inv=True, t_amp=0.20)
            else:
                r_a = max(c, 0.28) if c > 0.05 else 0.22
                place_beat(sig, r_at, pr_ms=pr_ms, r_amp=r_a, t_amp=0.22)
        leads[lead] = sig

    for v_num, lead in enumerate(PRECORDIAL, start=1):
        r_a = _precordial_r(v_num)
        s_a = _precordial_s(v_num)
        sig = np.zeros(N)
        for p_t in p_only_list:
            p_c = p_t - 0.160 + 0.040
            sig += gauss(p_c, 45, 0.11)
        for (r_at, pr_ms) in r_list:
            place_beat(sig, r_at, pr_ms=pr_ms, r_amp=r_a,
                       s_frac=s_a/max(r_a,0.01), t_amp=max(0.12, 0.26*r_a))
        leads[lead] = sig
    return leads


def mobitz_ii(base_hr=75, ratio=3):
    """Mobitz II: fixed PR, sudden dropped beats at N:1 ratio."""
    p_times = np.arange(0.30, DUR, 60.0 / base_hr)
    r_times = [p_t + 0.160 for i, p_t in enumerate(p_times) if i % ratio == 0]

    leads = {}
    for lead in FRONTAL:
        c = _proj(60, lead)
        sig = np.zeros(N)
        for p_t in p_times:
            p_c = p_t + 0.040
            sig += gauss(p_c, 45, (-1 if lead == "aVR" else 1) * 0.15)
        for r_at in r_times:
            if 0.08 < r_at < DUR - 0.12:
                if lead == "aVR":
                    place_beat(sig, r_at, no_p=True, r_amp=0.78, qs=True,
                               t_inv=True, t_amp=0.20)
                else:
                    r_a = max(c, 0.28) if c > 0.05 else 0.22
                    place_beat(sig, r_at, no_p=True, r_amp=r_a, t_amp=0.22)
        leads[lead] = sig

    for v_num, lead in enumerate(PRECORDIAL, start=1):
        r_a = _precordial_r(v_num)
        s_a = _precordial_s(v_num)
        sig = np.zeros(N)
        for p_t in p_times:
            sig += gauss(p_t + 0.040, 45, 0.12)
        for r_at in r_times:
            if 0.08 < r_at < DUR - 0.12:
                place_beat(sig, r_at, no_p=True, r_amp=r_a,
                           s_frac=s_a/max(r_a,0.01), t_amp=max(0.12, 0.25*r_a))
        leads[lead] = sig
    return leads


def complete_avb():
    """3rd degree: P and QRS are independent, slow wide ventricular escape."""
    p_times = np.arange(0.25, DUR, 60.0 / 72)      # atrial rate ~72
    v_times = list(np.arange(0.55, DUR, 60.0 / 33)) # ventricular escape ~33

    leads = {}
    for lead in FRONTAL:
        c = _proj(60, lead)
        sig = np.zeros(N)
        for p_t in p_times:
            sig += gauss(p_t + 0.040, 45, (-1 if lead == "aVR" else 1) * 0.14)
        for r_at in v_times:
            if 0.08 < r_at < DUR - 0.12:
                # Wide ventricular escape: bizarre wide complex
                if lead in ("II", "III", "aVF"):
                    place_beat(sig, r_at, no_p=True, qrs_ms=140, qt_ms=440,
                               r_amp=0.12, s_frac=7.0, t_amp=0.30)
                elif lead == "aVR":
                    place_beat(sig, r_at, no_p=True, qrs_ms=140, qt_ms=440,
                               r_amp=0.85, qs=False, s_frac=0.10, t_inv=True, t_amp=0.25)
                else:
                    place_beat(sig, r_at, no_p=True, qrs_ms=140, qt_ms=440,
                               r_amp=max(abs(c), 0.30), s_frac=0.35, t_inv=True, t_amp=0.22)
        leads[lead] = sig

    for v_num, lead in enumerate(PRECORDIAL, start=1):
        sig = np.zeros(N)
        for p_t in p_times:
            sig += gauss(p_t + 0.040, 45, 0.10)
        for r_at in v_times:
            if 0.08 < r_at < DUR - 0.12:
                if v_num <= 3:
                    place_beat(sig, r_at, no_p=True, qrs_ms=140, qt_ms=440,
                               r_amp=1.1, s_frac=0.10, t_inv=True, t_amp=0.28)
                else:
                    place_beat(sig, r_at, no_p=True, qrs_ms=140, qt_ms=440,
                               r_amp=0.15, s_frac=5.0, t_amp=0.32)
        leads[lead] = sig
    return leads


# ─────────────────────────────────────────────────────────────────────────────
# Bundle Branch Blocks
# ─────────────────────────────────────────────────────────────────────────────

def lbbb(hr=72):
    """LBBB: broad R in lateral leads, QS in V1-V3, discordant ST-T."""
    r_t = rr(hr)
    leads = {}
    for lead in FRONTAL:
        # Lateral limb leads (I, aVL): broad R
        # Inferior (II, III, aVF): variable, often QS or broad R
        # aVR: positive (broad positive, discordant T)
        if lead in ("I", "aVL"):
            sig = build_lead(r_t, pr_ms=160, qrs_ms=140, qt_ms=440,
                             p_amp=0.14, r_amp=1.00, broad_r=True,
                             t_inv=True, t_amp=0.22, st=-0.10)
        elif lead == "aVR":
            sig = build_lead(r_t, pr_ms=160, qrs_ms=140, qt_ms=440,
                             p_amp=0.14, p_inv=True, r_amp=0.80, qs=True,
                             t_inv=False, t_amp=0.22, st=0.10)
        elif lead in ("II", "III"):
            sig = build_lead(r_t, pr_ms=160, qrs_ms=140, qt_ms=440,
                             p_amp=0.14, r_amp=0.55, broad_r=True,
                             t_inv=True, t_amp=0.18, st=-0.08)
        else:  # aVF
            sig = build_lead(r_t, pr_ms=160, qrs_ms=140, qt_ms=440,
                             p_amp=0.14, r_amp=0.65, broad_r=True,
                             t_inv=True, t_amp=0.18, st=-0.08)
        leads[lead] = sig

    for v_num, lead in enumerate(PRECORDIAL, start=1):
        if v_num <= 3:  # V1-V3: QS pattern, ST elevation (discordant)
            sig = build_lead(r_t, pr_ms=160, qrs_ms=140, qt_ms=440,
                             p_amp=0.12, r_amp=0.65, wide_neg=True,
                             t_amp=0.28, t_inv=False, st=0.18)
        elif v_num == 4:  # V4: transition
            sig = build_lead(r_t, pr_ms=160, qrs_ms=140, qt_ms=440,
                             p_amp=0.12, r_amp=0.40, broad_r=True,
                             t_inv=True, t_amp=0.20, st=-0.08)
        else:  # V5-V6: broad positive R, ST depression, T inversion (discordant)
            r_a = _precordial_r(v_num, transition=3.5)
            sig = build_lead(r_t, pr_ms=160, qrs_ms=140, qt_ms=440,
                             p_amp=0.12, r_amp=r_a * 1.1, broad_r=True,
                             t_inv=True, t_amp=0.22, st=-0.12)
        leads[lead] = sig
    return leads


def rbbb(hr=75):
    """RBBB: RSR' in V1-V2, wide slurred S in I, V5-V6, T inversion V1-V3."""
    r_t = rr(hr)
    leads = {}
    for lead in FRONTAL:
        c = _proj(60, lead)
        # Wide slurred S in I, aVL
        if lead in ("I", "aVL"):
            sig = build_lead(r_t, pr_ms=160, qrs_ms=130, qt_ms=420,
                             p_amp=0.15, r_amp=max(c, 0.45),
                             q_frac=0.06, s_frac=0.55,
                             t_amp=0.22)
        elif lead == "aVR":
            sig = build_lead(r_t, pr_ms=160, qrs_ms=130, qt_ms=420,
                             p_amp=0.15, p_inv=True, r_amp=0.78, qs=True,
                             t_inv=True, t_amp=0.18)
        else:
            r_a = max(c, 0.30) if c > 0.05 else 0.22
            sig = build_lead(r_t, pr_ms=160, qrs_ms=130, qt_ms=420,
                             p_amp=0.15, r_amp=r_a, s_frac=0.18, t_amp=0.22)
        leads[lead] = sig

    for v_num, lead in enumerate(PRECORDIAL, start=1):
        if v_num <= 2:  # V1-V2: RSR', T inversion
            sig = build_lead(r_t, pr_ms=160, qrs_ms=130, qt_ms=420,
                             p_amp=0.10, r_amp=1.0, rsrp=True,
                             t_inv=True, t_amp=0.25)
        elif v_num == 3:  # V3: partial RSR', T inverted
            sig = build_lead(r_t, pr_ms=160, qrs_ms=130, qt_ms=420,
                             p_amp=0.11, r_amp=0.80, rsrp=True,
                             t_inv=True, t_amp=0.20)
        else:  # V4-V6: wide slurred S, normal T
            r_a = _precordial_r(v_num)
            sig = build_lead(r_t, pr_ms=160, qrs_ms=130, qt_ms=420,
                             p_amp=0.12, r_amp=r_a, s_frac=0.55,
                             t_amp=max(0.14, 0.26 * r_a))
        leads[lead] = sig
    return leads


# ─────────────────────────────────────────────────────────────────────────────
# Junctional / Escape rhythms
# ─────────────────────────────────────────────────────────────────────────────

def junctional(hr=50):
    return _normal_base(rr(hr), p_amp=0.11, p_inv_inferior=True,
                        extra={"II": {"pr_ms": 100}, "III": {"pr_ms": 100},
                               "aVF": {"pr_ms": 100}})


def idioventricular(hr=33):
    """Wide bizarre ventricular escape — same approach as 3rd degree escape."""
    r_t = rr(hr)
    leads = {}
    for lead in FRONTAL:
        c = _proj(60, lead)
        if lead in ("II", "III", "aVF"):
            leads[lead] = build_lead(r_t, no_p=True, qrs_ms=140, qt_ms=440,
                                     r_amp=0.10, s_frac=7.0, t_amp=0.30)
        elif lead == "aVR":
            leads[lead] = build_lead(r_t, no_p=True, qrs_ms=140, qt_ms=440,
                                     r_amp=0.85, qs=False, s_frac=0.10,
                                     t_inv=True, t_amp=0.24)
        else:
            leads[lead] = build_lead(r_t, no_p=True, qrs_ms=140, qt_ms=440,
                                     r_amp=max(abs(c), 0.28), s_frac=0.40,
                                     t_inv=True, t_amp=0.20)
    for v_num, lead in enumerate(PRECORDIAL, start=1):
        if v_num <= 3:
            leads[lead] = build_lead(r_t, no_p=True, qrs_ms=140, qt_ms=440,
                                     r_amp=1.10, s_frac=0.10, t_inv=True, t_amp=0.28)
        else:
            leads[lead] = build_lead(r_t, no_p=True, qrs_ms=140, qt_ms=440,
                                     r_amp=0.12, s_frac=6.0, t_amp=0.30)
    return leads


# ─────────────────────────────────────────────────────────────────────────────
# Ventricular arrhythmias
# ─────────────────────────────────────────────────────────────────────────────

def vtach(hr=175):
    return idioventricular(hr)   # same wide-complex morphology, faster rate


def vfib():
    leads = {}
    for lead in ALL_LEADS:
        sig = np.zeros(N)
        for f in np.concatenate([np.random.uniform(200, 400, 18),
                                  np.random.uniform(50, 200, 8)]):
            amp = np.random.exponential(0.12)
            sig += amp * np.sin(2 * math.pi * (f / 60) * T
                                + np.random.uniform(0, 2 * math.pi))
        envelope = np.clip(0.5 + 0.5 * np.cos(2 * math.pi * T / (DUR * 2)), 0.3, 1.0)
        leads[lead] = sig * envelope
    return leads


def asystole():
    return {lead: np.random.normal(0, 0.014, N) for lead in ALL_LEADS}


# ─────────────────────────────────────────────────────────────────────────────
# STEMI patterns
# ─────────────────────────────────────────────────────────────────────────────

def anterior_stemi(hr=80):
    """LAD territory: ST elevation V1-V4, reciprocal in aVL and inferior leads."""
    return _normal_base(rr(hr), extra={
        "V1": {"st": +0.18, "t_amp": 0.40},
        "V2": {"st": +0.38, "t_amp": 0.55, "q_frac": 0.06},
        "V3": {"st": +0.30, "t_amp": 0.48, "q_frac": 0.06},
        "V4": {"st": +0.18, "t_amp": 0.38},
        "V5": {"st": +0.08, "t_amp": 0.30},
        "aVL": {"st": -0.14, "t_inv": True, "t_amp": 0.18},
        "III": {"st": -0.10, "t_inv": True, "t_amp": 0.15},
        "aVF": {"st": -0.08},
    })


def inferior_stemi(hr=78):
    """RCA territory: ST elevation II, III, aVF; reciprocal in I, aVL."""
    return _normal_base(rr(hr), extra={
        "II":  {"st": +0.28, "t_amp": 0.50, "big_q": True},
        "III": {"st": +0.35, "t_amp": 0.55, "big_q": True},
        "aVF": {"st": +0.25, "t_amp": 0.42, "big_q": True},
        "I":   {"st": -0.14, "t_inv": True, "t_amp": 0.16},
        "aVL": {"st": -0.18, "t_inv": True, "t_amp": 0.14},
        "V5":  {"st": -0.06},
        "V6":  {"st": -0.05},
    })


def lateral_stemi(hr=82):
    """LCx territory: ST elevation I, aVL, V5-V6; reciprocal in III, aVF."""
    return _normal_base(rr(hr), extra={
        "I":   {"st": +0.28, "t_amp": 0.45},
        "aVL": {"st": +0.30, "t_amp": 0.48},
        "V5":  {"st": +0.25, "t_amp": 0.42},
        "V6":  {"st": +0.20, "t_amp": 0.38},
        "III": {"st": -0.18, "t_inv": True, "t_amp": 0.16},
        "aVF": {"st": -0.12, "t_inv": True, "t_amp": 0.14},
    })


def posterior_stemi(hr=76):
    """Posterior: mirror image in V1-V3 — ST depression + tall R (no standard elevation)."""
    return _normal_base(rr(hr), extra={
        # V1-V3: tall R (mirror of posterior Q), horizontal ST depression, upright T (mirror of T inversion)
        "V1": {"r_amp": 0.65, "s_frac": 0.05, "st": -0.28, "t_inv": False, "t_amp": 0.55},
        "V2": {"r_amp": 0.80, "s_frac": 0.06, "st": -0.22, "t_inv": False, "t_amp": 0.48},
        "V3": {"r_amp": 0.90, "s_frac": 0.08, "st": -0.14, "t_inv": False, "t_amp": 0.38},
    })


# ─────────────────────────────────────────────────────────────────────────────
# NSTEMI / ACS
# ─────────────────────────────────────────────────────────────────────────────

def nstemi_st_depression(hr=88):
    """Diffuse ST depression, T wave flattening/inversion."""
    return _normal_base(rr(hr), extra={
        "V4": {"st": -0.18, "t_inv": True, "t_amp": 0.18},
        "V5": {"st": -0.20, "t_inv": True, "t_amp": 0.16},
        "V6": {"st": -0.14, "t_inv": True, "t_amp": 0.14},
        "I":  {"st": -0.10, "t_amp": 0.18},
        "II": {"st": -0.12, "t_amp": 0.20},
        "aVL": {"st": -0.08},
    })


def wellens_a(hr=72):
    """Type A: biphasic T in V2-V3 (positive then negative)."""
    r_t = rr(hr)
    base = _normal_base(r_t)

    def biphasic_t_signal(r_times):
        sig = build_lead(r_times, pr_ms=160, qrs_ms=80, qt_ms=380,
                         p_amp=0.15, r_amp=0.55, s_frac=0.15, t_amp=0.0)
        for r_at in r_times:
            if 0.08 < r_at < DUR - 0.12:
                t_c = r_at + 0.240
                sig += gauss(t_c - 0.025, 35,  0.18)  # initial positive
                sig += gauss(t_c + 0.048, 48, -0.22)  # terminal negative
        return sig

    base["V2"] = biphasic_t_signal(r_t)
    base["V3"] = biphasic_t_signal(r_t)
    # V1: may also show biphasic
    base["V1"] = build_lead(r_t, pr_ms=160, qrs_ms=80, qt_ms=380,
                             p_amp=0.10, r_amp=0.20, s_frac=3.0, t_amp=0.10)
    return base


def wellens_b(hr=68):
    """Type B: deep symmetric T inversion in V2-V3."""
    return _normal_base(rr(hr), extra={
        "V1": {"t_inv": True, "t_amp": 0.22, "st": 0.0},
        "V2": {"t_inv": True, "t_amp": 0.58, "st": 0.0},
        "V3": {"t_inv": True, "t_amp": 0.50, "st": 0.0},
        "V4": {"t_inv": True, "t_amp": 0.20, "st": 0.0},
    })


# ─────────────────────────────────────────────────────────────────────────────
# PE & Strain
# ─────────────────────────────────────────────────────────────────────────────

def pe_s1q3t3(hr=108):
    """Classic PE: sinus tach, S1, Q3T3, RV strain V1-V4."""
    return _normal_base(rr(hr), extra={
        "I":   {"s_frac": 0.65},                          # S1: prominent S
        "III": {"big_q": True, "t_inv": True, "t_amp": 0.30, "st": 0.0},  # Q3T3
        "V1":  {"rsrp": True, "t_inv": True, "t_amp": 0.28},              # partial RBBB
        "V2":  {"t_inv": True, "t_amp": 0.32},
        "V3":  {"t_inv": True, "t_amp": 0.28},
    })


def pe_rv_strain(hr=112):
    """PE RV strain: right precordial T inversions + sinus tach."""
    return _normal_base(rr(hr), extra={
        "V1": {"t_inv": True, "t_amp": 0.38},
        "V2": {"t_inv": True, "t_amp": 0.42},
        "V3": {"t_inv": True, "t_amp": 0.35},
        "V4": {"t_inv": True, "t_amp": 0.22},
    })


def lv_strain(hr=72):
    """LVH with strain: tall lateral R, asymmetric ST-T in lateral leads."""
    return _normal_base(rr(hr), extra={
        "V1": {"r_amp": 0.18, "s_frac": 6.0, "t_amp": 0.16},   # deep S (LVH)
        "V2": {"r_amp": 0.28, "s_frac": 4.0, "t_amp": 0.18},
        "V5": {"r_amp": 2.10, "s_frac": 0.04, "st": -0.18, "t_inv": True, "t_amp": 0.32},
        "V6": {"r_amp": 1.60, "s_frac": 0.06, "st": -0.14, "t_inv": True, "t_amp": 0.26},
        "I":  {"r_amp": 1.30, "st": -0.12, "t_inv": True, "t_amp": 0.22},
        "aVL": {"r_amp": 0.85, "st": -0.10, "t_inv": True, "t_amp": 0.18},
    })


def rv_strain(hr=90):
    """RV strain: right precordial T inversions, right axis deviation."""
    return _normal_base(rr(hr), qrs_axis=110,  # right axis
                        extra={
                            "V1": {"t_inv": True, "t_amp": 0.40, "s_frac": 0.30},
                            "V2": {"t_inv": True, "t_amp": 0.44},
                            "V3": {"t_inv": True, "t_amp": 0.30},
                        })


# ═══════════════════════════════════════════════════════════════════════════════
# Renderer
# ═══════════════════════════════════════════════════════════════════════════════

def _style_ax(ax, label, xlim, ylim=(-0.6, 1.4)):
    ax.set_facecolor(BG)
    # Minor grid: 0.04s (1mm at 25mm/s) × 0.1mV
    ax.set_xticks(np.arange(0, xlim[1] + 0.04, 0.04), minor=True)
    ax.set_yticks(np.arange(ylim[0], ylim[1] + 0.10, 0.10), minor=True)
    # Major grid: 0.20s × 0.50mV
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


def render_12lead(leads, out_path):
    """
    Standard 12-lead layout:
      Row 0-2: 4 columns × 3 rows (2.5s each)
      Row 3:   Lead II rhythm strip (full 10s)
    No diagnosis title in the image — kept anonymized for quiz use.
    """
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
            ax = fig.add_subplot(gs[row_i, col_i])
            t0 = col_i * COL_W
            t1 = t0 + COL_W
            mask = (T >= t0) & (T < t1)
            ax_t = T[mask] - t0
            ax_sig = leads[lead][mask]
            _style_ax(ax, lead, xlim=(0, COL_W))
            ax.plot(ax_t, ax_sig, color=TRACE, lw=1.05, zorder=3, antialiased=True)

    # Rhythm strip — Lead II full width
    ax_strip = fig.add_subplot(gs[3, :])
    _style_ax(ax_strip, "II (rhythm strip)", xlim=(0, DUR))
    ax_strip.plot(T, leads["II"], color=TRACE, lw=1.05, zorder=3, antialiased=True)

    # Calibration label only (no diagnosis title — anonymized)
    fig.text(0.985, 0.985, '25 mm/s  ·  10 mm/mV', fontsize=6.5,
             ha='right', va='top', color='#888888')

    plt.savefig(out_path, dpi=150, bbox_inches='tight', facecolor=BG)
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════════════════════
# Case manifest — matches cases.json
# ═══════════════════════════════════════════════════════════════════════════════

CASES = [
    # id                  display title                                      generator
    ("nsr_01",           "Normal Sinus Rhythm (75 bpm)",                    lambda: nsr(75)),
    ("nsr_02",           "Normal Sinus Rhythm (88 bpm)",                    lambda: nsr(88)),
    ("brady_01",         "Sinus Bradycardia (45 bpm)",                      lambda: nsr(45)),
    ("brady_02",         "Sinus Bradycardia (38 bpm)",                      lambda: nsr(38)),
    ("tachy_01",         "Sinus Tachycardia (115 bpm)",                     lambda: nsr(115)),
    ("tachy_02",         "Sinus Tachycardia (140 bpm)",                     lambda: nsr(140)),
    ("sarr_01",          "Sinus Arrhythmia",                                lambda: sinus_arrhythmia(68)),
    ("pac_01",           "PACs (Premature Atrial Contractions)",            lambda: with_pacs(70)),
    ("pvc_01",           "PVCs (Premature Ventricular Contractions)",       lambda: with_pvcs(70)),
    ("svt_01",           "SVT (Supraventricular Tachycardia, 190 bpm)",     lambda: svt(190)),
    ("afib_01",          "Atrial Fibrillation (80 bpm)",                    lambda: atrial_fibrillation(80)),
    ("afib_02",          "Atrial Fibrillation with RVR (130 bpm)",          lambda: atrial_fibrillation(130)),
    ("aflut_01",         "Atrial Flutter 4:1 (75 bpm ventricular)",         lambda: atrial_flutter(300, 4)),
    ("avb1_01",          "1st Degree AV Block (PR 280 ms)",                 lambda: first_degree_avb(70, 280)),
    ("avb2m1_01",        "2nd Degree AV Block — Mobitz I (Wenckebach)",     lambda: mobitz_i(75)),
    ("avb2m2_01",        "2nd Degree AV Block — Mobitz II (3:1)",           lambda: mobitz_ii(75, 3)),
    ("avb3_01",          "3rd Degree (Complete) AV Block",                  lambda: complete_avb()),
    ("lbbb_01",          "Left Bundle Branch Block (LBBB)",                 lambda: lbbb(72)),
    ("rbbb_01",          "Right Bundle Branch Block (RBBB)",                lambda: rbbb(75)),
    ("junct_01",         "Junctional Rhythm (48 bpm)",                      lambda: junctional(48)),
    ("junct_02",         "Accelerated Junctional Rhythm (85 bpm)",          lambda: junctional(85)),
    ("idio_01",          "Idioventricular Rhythm (33 bpm)",                 lambda: idioventricular(33)),
    ("vtach_01",         "Ventricular Tachycardia (175 bpm)",               lambda: vtach(175)),
    ("vtach_02",         "Ventricular Tachycardia (200 bpm)",               lambda: vtach(200)),
    ("vfib_01",          "Ventricular Fibrillation",                        lambda: vfib()),
    ("asys_01",          "Asystole",                                        lambda: asystole()),
    ("stemi_ant_01",     "Anterior STEMI (LAD territory)",                  lambda: anterior_stemi(80)),
    ("stemi_inf_01",     "Inferior STEMI (RCA territory)",                  lambda: inferior_stemi(78)),
    ("stemi_lat_01",     "Lateral STEMI (LCx territory)",                   lambda: lateral_stemi(82)),
    ("stemi_post_01",    "Posterior STEMI (mirror image V1–V3)",            lambda: posterior_stemi(76)),
    ("nstemi_01",        "NSTEMI — ST Depression",                          lambda: nstemi_st_depression(88)),
    ("wellens_a_01",     "Wellens Syndrome Type A (biphasic T V2–V3)",      lambda: wellens_a(72)),
    ("wellens_b_01",     "Wellens Syndrome Type B (deep T inversion V2–V3)",lambda: wellens_b(68)),
    ("pe_s1q3t3_01",     "Pulmonary Embolism — S1Q3T3 Pattern",             lambda: pe_s1q3t3(108)),
    ("pe_rv_strain_01",  "Pulmonary Embolism — RV Strain",                  lambda: pe_rv_strain(112)),
    ("lv_strain_01",     "LVH with LV Strain Pattern",                      lambda: lv_strain(72)),
    ("rv_strain_01",     "RV Strain Pattern",                               lambda: rv_strain(90)),
]


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    np.random.seed(42)
    print(f"\nGenerating {len(CASES)} full 12-lead EKG PNGs → {OUT_DIR}\n")
    for case_id, _title, gen_fn in CASES:
        out_path = OUT_DIR / f"{case_id}_12lead.png"
        leads = gen_fn()
        render_12lead(leads, out_path)
        print(f"  ✓  {out_path.name}")
    print(f"\nDone — {len(CASES)} files written.\n")


if __name__ == "__main__":
    main()
