# EKG Rhythm Analysis Steps

Use this as the canonical step order for EKG rhythm analysis, content creation, and app page generation. If a tracing deviates from a step, record the deviation and update the differential diagnosis accordingly.

## Curriculum spine

This checklist, **[EKG waveform components](EKG_WAVEFORM_COMPONENTS.md)**, and **[AHA/ACC rhythm definitions](AHA_ACC_RHYTHM_DEFINITIONS.md)** are **shared across beginner, intermediate, and advanced** teaching. Tier is set by **which steps** you emphasize and **which heading-level sections** you pull from each file—not by dedicating whole documents to a single level.

- **Beginner** might pair early steps (e.g. 1–5) with introductory waveform sections (grid, P, rate basics) and corresponding rhythm definitions (e.g. NSR, sinus tach/brady).
- **Intermediate** deepens intervals, axis, precordial/ST/T/Q morphology (steps ~6–12) and broader rhythm categories from the definitions catalog.
- **Advanced** runs the full sequence including syndromic integration (**13–17**) and guideline-framed nuances, still citing only the waveform/rhythm subsections each objective needs.

Keep **this step numbering** as the canonical order for lessons, cases, and app generation at every level.

**EKG Academy (web app):** Step **10** (ST segments, J-point anchoring) maps to beginner lesson **ST Segment & J-Point** — route `/learn/beginner/07-st-segment-and-j-point`, source [`07-st-segment-and-j-point.mdx`](../web/content/learn/beginner/07-st-segment-and-j-point.mdx). Related J-point teaching: [`12-bundle-branch-blocks.mdx`](../web/content/learn/intermediate/12-bundle-branch-blocks.mdx), [`04-stemi-localization.mdx`](../web/content/learn/advanced/04-stemi-localization.mdx), [`05-nstemi-ischemia.mdx`](../web/content/learn/advanced/05-nstemi-ischemia.mdx).

The **full 17-step checklist** (interactive `SystematicChecklist`) lives in beginner **A Systematic Approach to Reading an EKG** — route `/learn/beginner/15-systematic-approach`, source [`15-systematic-approach.mdx`](../web/content/learn/beginner/15-systematic-approach.mdx).

## Steps

### 1. Confirm correct patient

- Wrong patient = invalid interpretation.

### 2. Check prior EKGs

- New change = acute.
- Stable change = baseline/chronic.

### 3. Assess rate

- Fast: tachycardia, SVT, flutter, AF, VT, or physiologic stress.
- Slow: sinus bradycardia, meds, AV block, hypothyroid, hypothermia, vagal tone.

### 4. Assess rhythm

- Regularly irregular = AV block, flutter with block, PACs/PVCs, sinus arrhythmia.
- Irregularly irregular = AF, MAT, ectopy.

### 5. Check P before each QRS

- Missing P = AF, junctional rhythm, sinus arrest, AV dissociation.
- Extra P = AV block or flutter.
- Disconnected P/QRS = 3° AV block.

### 6. Measure intervals

- PR long = 1° AV block.
- PR short = pre-excitation/junctional.
- QRS wide = BBB, VT, pre-excitation, hyperK.
- QT long = torsades risk, drugs, electrolytes, LQTS.

### 7. Evaluate P waves

- Abnormal P = atrial enlargement or ectopic atrial rhythm.
- Inverted inferior P = junctional/low atrial.

### 8. Evaluate axis

- LAD: LAFB, LVH, inferior MI.
- RAD: RVH, RV strain, lung disease.
- Extreme: lead reversal, ventricular rhythm, severe conduction disease.

### 9. Check precordial progression

- Poor progression = anterior MI, lead misplacement, LBBB, RVH, COPD, normal variant.

### 10. Check ST segments

- **Anchor ST elevation and depression at the J-point** (QRS–ST junction): universal STEMI/NSTEMI thresholds and algorithms (e.g. Sgarbossa, modified Sgarbossa **|ST/S|**) use deviation **measured at the J-point**, not mid–ST segment unless your protocol specifies otherwise.
- Slurred or notched QRS–ST takeoff (early repol, Brugada, post-conduction delay): identify the J-point precisely before judging ST contour.
- ST elevation = ischemic injury pattern, STEMI, pericarditis, early repol, LVH, Brugada.
- ST depression = ischemia, reciprocal change, digoxin, strain.

### 11. Check T waves

- Inversion = ischemia, strain, BBB, RVH, PE, CNS event, normal variant.
- Peaked = hyperK.
- Flat/biphasic = ischemia, electrolytes, meds.

### 12. Check Q waves

- Pathologic Q = prior MI/scar, cardiomyopathy, lead misplacement.

### 13. Ischemia/ACS

- **Wellens** (biphasic/deep T in V2–V3)
- **de Winter** (ST↓ + tall upright T precordially)
- **Hyperacute MI** (symmetric STE with bulky T waves)
- **Modified Sgarbossa** (**primary** morphologic approach for suspected occlusion with **LBBB** or paced wide QRS; Smith ST/S ratio): concordant STE ≥1 mm; concordant STD ≥1 mm in V1–V3; discordant STE with **|ST/S| ≥0.25** at J-point with meaningful STE (typically ≥1 mm)
- **Sgarbossa criteria** (original rule set; low sensitivity—still referenced historically): concordant STE ≥1 mm; concordant STD ≥1 mm in V1–V3; classically discordant STE ≥5 mm (third limb largely superseded by modified criteria)
- **Barcelona criteria** (**LBBB**; Di Marco algorithm — alternative / newer single-hit rule; external adoption varies): positive if **any** — concordant STE ≥1 mm; concordant STD ≥1 mm **in any lead**; discordant ST deviation ≥1 mm when dominant QRS deflection **≤6 mm (0.6 mV)**
- **Guidelines (ESC/AHA ACS frameworks):** Symptoms, serial ECGs, troponin, and cath-lab activation criteria drive care; isolated **new LBBB** is not a dependable STEMI surrogate by itself. Classic / modified / Barcelona morphologic patterns are adjuncts—not substitutes—for guideline-directed escalation.

### 14. Strain

- **LVH strain** (ST/T discordant to QRS direction)
- **Lateral ischemia** (ST↓ concordant with QRS)

### 15. Pulmonary disease pattern

- **PE** (**S1Q3T3**, sinus tach, new RBBB/right-axis shift)
- **Chronic lung disease pattern** (RAD, P pulmonale, low QRS voltage, poor R progression)

### 16. Pericarditis vs mimic

- **Pericarditis** (diffuse STE + **Spodick sign**: downsloping TP segment with apparent PR depression)
- **Early repolarization** (concave J-point STE, **notched/fishhook J**)

### 17. Channelopathy/structural

- **Brugada pattern** (**type 1 coved** ST elevation V1–V2)
- **ARVC** (arrhythmogenic right ventricular cardiomyopathy; **epsilon wave** with terminal notch, often V1–V3)
