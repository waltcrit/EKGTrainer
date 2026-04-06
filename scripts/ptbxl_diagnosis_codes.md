# PTB-XL Diagnosis Codes & EKGTrainer Coverage

**Last Updated:** April 5, 2026  
**Data Source:** PhysioNet PTB-XL v1.0.3 (21,799 records)  
**Teaching Cases:** 43 total (29 from PTB-XL real data, 14 synthetic-only)

## Usage Status

Total PTB-XL records: **21,799**  
Diagnosis codes available: **71**  
EKGTrainer cases using PTB-XL: **29/43**  
Synthetic-only (no PTB-XL match): **14/43**  

---

## Cases Currently In Use

### Sinus Rhythms (5 cases)
- ✓ **NORM** (Normal) — nsr_01, nsr_02 — 9,514 records
- ✓ **SBRAD** (Sinus Bradycardia) — brady_01, brady_02 — 637 records [SYNTHETIC]
- ✓ **SARRH** (Sinus Arrhythmia) — sarr_01 — 772 records [SYNTHETIC]
- ✓ **STACH** (Sinus Tachycardia) — tachy_01, tachy_02 — 826 records

### Atrial Arrhythmias (6 cases)
- ✓ **AFIB** (Atrial Fibrillation) — afib_01, afib_02 — 1,514 records
- ✓ **AFLT** (Atrial Flutter) — aflut_01 — 73 records
- ✓ **PSVT** (Paroxysmal SVT) — svt_01 — 24 records
- ✓ **PAC** (Premature Atrial Contractions) — pac_01 — 398 records [SYNTHETIC]

### Ventricular Arrhythmias & Escape Rhythms (7 cases)
- ✓ **3AVB** (Third-degree AV Block / Escape) — idio_01 — 16 records [ESCAPE PROXY]
- ✓ **VT** (Ventricular Tachycardia) — vtach_01, vtach_02 — 0 records [SYNTHETIC ONLY]
- ✓ **VF** (Ventricular Fibrillation) — vfib_01 — 0 records [SYNTHETIC ONLY]
- ✓ **ASYS** (Asystole) — asys_01 — 0 records [SYNTHETIC ONLY]

### Conduction Abnormalities (7 cases)
- ✓ **1AVB** (First-degree AV Block) — avb1_01 — 793 records
- ✓ **2AVB** (Second-degree AV Block) — avb2m1_01, avb2m2_01 — 14 records
- ✓ **3AVB** (Third-degree AV Block) — avb3_01 — 16 records
- ✓ **LBBB** (Left Bundle Branch Block) — lbbb_01 — 536 records [SYNTHETIC]
- ✓ **RBBB** (Right Bundle Branch Block) — rbbb_01 — 1,118 records [SYNTHETIC]
- ✓ **WPW** (Wolff-Parkinson-White) — wpw_01 — 79 records
- ✗ **Junctional Rhythms** — junct_01, junct_02 — [SYNTHETIC ONLY]

### Ventricular Hypertrophy (2 cases)
- ✓ **LVH** (Left Ventricular Hypertrophy) — lv_strain_01 — 2,132 records
- ✓ **RVH** (Right Ventricular Hypertrophy) — rv_strain_01 — 126 records

### Ischemia/Infarction (5 cases)
- ✓ **AMI** (Anterior MI) — stemi_ant_01 — 353 records
- ✓ **ILMI** (Inferolateral MI) — stemi_inf_01 — 478 records
- ✓ **ISCAL** (Lateral Ischemia) — stemi_lat_01 — 659 records
- ✓ **IPMI** (Posterior MI) — stemi_post_01 — 33 records
- ✓ **NST_** (Non-specific ST changes) — nstemi_01 — 767 records

### T-Wave Patterns (2 cases)
- ✓ **NDT** (Non-Diagnostic T-wave) — wellens_a_01, wellens_b_01 — 1,825 records

### PE Patterns (2 cases)
- ✓ **RVH** (Right Ventricular Hypertrophy proxy for PE) — pe_s1q3t3_01, pe_rv_strain_01 — 126 records

### Long QT & Brugada (2 cases)
- ✓ **LNGQT** (Long QT Syndrome) — lngqt_01 — 117 records
- ✓ **BRGADA** (Brugada Syndrome) — brugada_01 — not in PTB-XL [SYNTHETIC ONLY]

### Pacing (3 cases)
- ✓ **PACE** (Pacemaker) — pace_atrial_01, pace_ventricular_01, pace_av_01 — 294 records

---

## Available Codes NOT Currently Used

### Atrial
- SVARR (Supraventricular Arrhythmia) — 157 records

### Ventricular
- **PVC** (Premature Ventricular Contractions) — 1,143 records ← high priority candidate
- BIGU (Bigeminy) — 82 records
- TRIGU (Trigeminy) — 20 records

### Conduction
- **LAFB** (Left Anterior Fascicular Block) — 1,623 records ← high priority candidate
- LPFB (Left Posterior Fascicular Block) — 177 records
- ILBBB (Incomplete LBBB) — 77 records
- IRBBB (Incomplete RBBB) — 1,118 records
- VCLVH (Voltage Criteria LVH) — 875 records

### Ischemia (non-STEMI)
- ISC_ (General Ischemia) — 1,272 records
- ISCIN (Inferior Ischemia) — 218 records
- ISCAS (Anterior Septal Ischemia) — 169 records
- ISCLA (Lateral Ischemia) — 140 records
- ISCIL (Inferior/Lateral Ischemia) — 179 records
- LPR (Low precordial R) — 340 records

### Voltage/QRS
- ABQRS (Abnormal QRS) — 3,327 records
- IVCD (Incomplete Ventricular Conduction Delay) — 787 records
- LOWT (Low Voltage T-wave) — 438 records
- LVOLT (Low Voltage) — 182 records
- HVOLT (High Voltage) — 62 records

### Other
- QWAVE (Q Wave) — 548 records
- INVT (Inverted T-wave) — 294 records
- ANEUR (Aneurysm) — 104 records
- EL (Electrolyte abnormality) — 96 records
- DIG (Digoxin effect) — 181 records
- SEHYP (Secondary Hypertrophy) — 29 records
- TAB_ (T-wave Abnormality) — 35 records
- LAO/LAE (Left Atrial Overload/Enlargement) — 426 records
- RAO/RAE (Right Atrial Overload/Enlargement) — 99 records
- STE_ (ST Elevation) — 28 records
- STD_ (ST Depression) — 1,009 records
- PRC(S) (Pacing-related Changes) — 10 records

---

## Synthetic-Only Cases (no PTB-XL equivalent)

| Case | Reason |
|------|--------|
| brady_01, brady_02 | SBRAD records exist but are excluded by query filters |
| sarr_01 | SARRH records exist but are excluded |
| pac_01 | SVPB code absent from PTB-XL |
| pvc_01 | PVC records exist but are excluded |
| lbbb_01, rbbb_01 | LBBB/RBBB records exist but are excluded |
| junct_01, junct_02 | No junctional rhythm code in PTB-XL |
| vtach_01, vtach_02 | **VT code does not exist in PTB-XL** |
| vfib_01 | **VF code does not exist in PTB-XL** |
| asys_01 | **ASYS code does not exist in PTB-XL** |
| brugada_01 | **BRGADA code does not exist in PTB-XL** |

---

## Rendering

**Current style:** physionet (white background, gray grid)  
Supports `--render-style {house,physionet}` on all three generator scripts.

### Commands to regenerate all cases

```bash
# Rhythm strips
python3 scripts/generate_cases.py --render-style physionet

# 12-lead synthetic
python3 scripts/generate_12lead_ekgs.py --render-style physionet

# Replace with real PTB-XL data where available
python3 scripts/generate_ptbxl_ekgs.py --render-style physionet --remote
```

---

## Citation

Teaching cases derived from PTB-XL dataset (CC BY 4.0):
> Wagner et al. (2020). PTB-XL: A Large Publicly Available Electrocardiography Dataset.  
> Scientific Data 7:154. https://doi.org/10.1038/s41597-020-0495-6
