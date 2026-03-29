#!/usr/bin/env python3
"""
EKG Teaching Case Generator
Generates synthetic rhythm strip PNG images + cases.json metadata
for the EKGTrainer teaching library.

Run from the repository root:
    python3 scripts/generate_cases.py
"""

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


# ═══════════════════════════════════════════════════════════════════════════════
# Waveform Primitives
# ═══════════════════════════════════════════════════════════════════════════════

def gauss(t, center, fwhm_ms, amp):
    """Gaussian bump for P/Q/R/S/T wave approximation."""
    sigma = (fwhm_ms / 1000.0) / 2.3548
    return amp * np.exp(-0.5 * ((t - center) / sigma) ** 2)


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
    pac_indices = {3, 7} if len(r_times) > 8 else {3}
    skip_next = set()
    for i, r in enumerate(r_times):
        if i in pac_indices:
            pac_r = r + rr * 0.65
            place_normal_beat(sig, T, pac_r, pr_ms=120, p_amp=0.22)
            skip_next.add(i + 1)
        elif i not in skip_next:
            place_normal_beat(sig, T, r)
    return sig


def with_pvcs(heart_rate=70):
    sig = np.zeros(N)
    r_times = list(regular_r_times(heart_rate))
    pvc_indices = {3, 7} if len(r_times) > 8 else {3}
    skip_next = set()
    for i, r in enumerate(r_times):
        if i in pvc_indices:
            place_wide_beat(sig, T, r, style="pvc")
            skip_next.add(i + 1)
        elif i not in skip_next:
            place_normal_beat(sig, T, r)
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
    for r in regular_r_times(heart_rate):
        place_wide_beat(sig, T, r, style="pvc", r_amp=1.0)
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
# Rendering
# ═══════════════════════════════════════════════════════════════════════════════

def render(signal, rhythm_label, out_path, rate_label=None):
    fig, ax = plt.subplots(figsize=(12, 2.4), dpi=150)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    ax.set_xticks(np.arange(0, DUR + 0.04, 0.04), minor=True)
    ax.set_yticks(np.arange(-0.6, 1.7, 0.1), minor=True)
    ax.set_xticks(np.arange(0, DUR + 0.2, 0.2))
    ax.set_yticks(np.arange(-0.5, 1.6, 0.5))
    ax.grid(True, which='minor', color=MINOR, linewidth=0.3, zorder=1)
    ax.grid(True, which='major', color=MAJOR, linewidth=0.7, zorder=2)

    ax.set_xlim(0, DUR)
    ax.set_ylim(-0.5, 1.5)
    ax.tick_params(which='both', bottom=False, left=False,
                   labelbottom=False, labelleft=False)
    for s in ax.spines.values():
        s.set_visible(False)

    ax.plot(T, signal, color=TRACE, linewidth=1.2, zorder=3, antialiased=True)

    ax.text(0.01, 0.97, rhythm_label, transform=ax.transAxes,
            fontsize=8, fontweight='bold', va='top', color='#222222')
    ax.text(0.99, 0.97, '25 mm/s  |  10 mm/mV  |  Lead II',
            transform=ax.transAxes, fontsize=6.5, ha='right',
            va='top', color='#888888')
    if rate_label:
        ax.text(0.01, 0.04, rate_label, transform=ax.transAxes,
                fontsize=6.5, va='bottom', color='#555555', style='italic')

    plt.tight_layout(pad=0.2)
    plt.savefig(out_path, bbox_inches='tight', facecolor=BG)
    plt.close(fig)
    print(f"  ✓  {out_path.name}")


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

    dict(id="aflut_01", rhythm="Atrial Flutter (2:1)", category="atrial", difficulty=3,
         generator=lambda: atrial_flutter(300, 2), rate=150, regularity="regular",
         key_features=["Atrial rate ~300 bpm", "Sawtooth flutter waves (best in II, III, aVF)",
                       "Regular ventricular rate ~150 bpm", "2:1 conduction"],
         teaching="Classic sawtooth pattern at 300 bpm. With 2:1 conduction the ventricular "
                  "rate is exactly 150 — a rate of 150 should always raise suspicion for flutter."),

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
]


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    np.random.seed(0)
    metadata = []

    print(f"\nGenerating {len(CASES)} EKG cases → {CASES_DIR}\n")

    for case in CASES:
        out_path = CASES_DIR / f"{case['id']}.png"
        signal = case["generator"]()
        rate_label = f"Rate: {case['rate']} bpm" if case["rate"] else None
        render(signal, case["rhythm"], out_path, rate_label)

        metadata.append({
            "id":          case["id"],
            "rhythm":      case["rhythm"],
            "category":    case["category"],
            "difficulty":  case["difficulty"],
            "imagePath":   f"/cases/{case['id']}.png",
            "rate":        case["rate"],
            "regularity":  case["regularity"],
            "keyFeatures": case["key_features"],
            "teaching":    case["teaching"],
        })

    out = DATA_DIR / "cases.json"
    out.write_text(json.dumps(metadata, indent=2))
    print(f"\n✓  Wrote {len(metadata)} entries to {out}")
    print("Done.\n")


if __name__ == "__main__":
    main()
