/**
 * AHA/ACC rhythm criteria registry.
 * Keyed by the exact `rhythm` string values used in cases.json.
 * All content transcribed from docs/AHA_ACC_RHYTHM_DEFINITIONS.md.
 */

export interface RhythmCriteria {
  definition: string;
  diagnosticCriteria: string[];
  source: string;
  clinicalNotes?: string;
}

// ---------------------------------------------------------------------------
// Shared entries (reused under multiple rhythm-name keys)
// ---------------------------------------------------------------------------

const NSR: RhythmCriteria = {
  definition: "Rhythm originating from the sinoatrial (SA) node with regular rate and normal conduction.",
  diagnosticCriteria: [
    "Rate: 60–100 bpm",
    "Regular rhythm",
    "Upright P wave in lead II before each QRS",
    "PR interval: 120–200 ms",
    "QRS duration: <120 ms",
    "1:1 P:QRS ratio",
  ],
  source: "AHA/ACC Diagnostic Criteria",
};

const SINUS_BRADY: RhythmCriteria = {
  definition: "Regular sinus rhythm with rate < 60 bpm.",
  diagnosticCriteria: [
    "Rate: < 60 bpm",
    "Regular rhythm",
    "Normal P wave morphology (upright in II)",
    "Normal PR interval (120–200 ms)",
    "Narrow QRS (<120 ms)",
    "All other features of NSR preserved",
  ],
  source: "2018 ACC/AHA/HRS Guideline on Bradycardia and Conduction Delay",
  clinicalNotes: "Common in athletes and during sleep. Treat only if symptomatic (hypotension, altered mental status, hemodynamic instability).",
};

const SINUS_TACHY: RhythmCriteria = {
  definition: "Regular sinus rhythm with rate > 100 bpm.",
  diagnosticCriteria: [
    "Rate: > 100 bpm (often 100–160 bpm)",
    "Regular rhythm",
    "Upright P wave in lead II",
    "Normal PR interval (may appear short relative to RP interval at faster rates)",
    "Narrow QRS (<120 ms)",
    "1:1 P:QRS ratio",
  ],
  source: "AHA/ACC Diagnostic Criteria",
  clinicalNotes: "Always identify underlying cause: pain, fever, hypovolemia, anxiety, infection, PE, thyrotoxicosis, or anemia.",
};

const SINUS_ARRHYTHMIA: RhythmCriteria = {
  definition: "Sinus rhythm with physiologic variation in heart rate related to respiration (most common) or other cyclic variations.",
  diagnosticCriteria: [
    "Regular P waves (sinus origin, upright in II)",
    "Variation in PP intervals (and therefore RR intervals) > 120 ms",
    "Variation cyclically related to respiration",
    "Normal PR interval and QRS duration",
    "No ectopic beats",
  ],
  source: "AHA/ACC Diagnostic Criteria",
  clinicalNotes: "Normal finding, especially in young people and athletes. No treatment required.",
};

const AF: RhythmCriteria = {
  definition: "Rapid, irregular atrial arrhythmia characterized by uncoordinated atrial activation and loss of effective atrial mechanical function.",
  diagnosticCriteria: [
    "Replacement of P waves with rapid oscillations or fibrillatory waves",
    "Fibrillatory waves vary in amplitude, shape, and timing",
    "Irregular, rapid ventricular response (when AV conduction intact)",
    "RR intervals are irregularly irregular",
    "Baseline undulation without discrete P waves",
    "No isoelectric line between deflections",
  ],
  source: "2023 ACC/AHA/ACCP/HRS Guideline for Atrial Fibrillation",
};

const AF_RVR: RhythmCriteria = {
  definition: "Atrial fibrillation with rapid ventricular response — ventricular rate exceeds 100–120 bpm due to fast conduction through the AV node.",
  diagnosticCriteria: [
    "Replacement of P waves with fibrillatory waves",
    "Irregularly irregular RR intervals",
    "Ventricular rate typically > 100–120 bpm (rapid ventricular response)",
    "Baseline undulation without discrete P waves",
    "No isoelectric line between deflections",
  ],
  source: "2023 ACC/AHA/ACCP/HRS Guideline for Atrial Fibrillation",
  clinicalNotes: "Rate control target < 110 bpm at rest (lenient) or < 80 bpm (strict). Common precipitants: infection, thyrotoxicosis, electrolyte disturbance.",
};

const AFL: RhythmCriteria = {
  definition: "Rapid, regular atrial arrhythmia usually arising from the right atrium with regular ventricular response due to fixed AV block.",
  diagnosticCriteria: [
    "Sawtooth or flutter waves (F waves) at regular rate typically 250–350 bpm",
    "Regular RR intervals",
    "Fixed AV block ratio (commonly 2:1, 3:1, or 4:1)",
    "QRS complexes narrow unless aberrant conduction",
    "F waves best seen in inferior leads (II, III, aVF) and V1",
    "Atrial rate and degree of AV block determine ventricular rate",
  ],
  source: "AHA/ACC Diagnostic Criteria",
};

const PAC: RhythmCriteria = {
  definition: "Ectopic atrial depolarization occurring earlier than expected sinus beat, originating outside the SA node.",
  diagnosticCriteria: [
    "P wave morphology different from sinus P waves",
    "Occurs prematurely relative to sinus rhythm",
    "Usually followed by a QRS complex (unless blocked)",
    "Pause after PAC is non-compensatory (less than fully compensatory)",
    "PR interval may be different from sinus beats",
  ],
  source: "AHA/ACC Diagnostic Criteria",
  clinicalNotes: "Blocked PACs: P wave occurs within or soon after preceding T wave with no QRS following. Frequent PACs can trigger SVT or AF.",
};

const SVT: RhythmCriteria = {
  definition: "Tachycardia originating above the ventricular level, most commonly AVNRT (~50%), AVRT (~30%), or atrial tachycardia (~20%).",
  diagnosticCriteria: [
    "Heart rate typically 140–250 bpm",
    "Regular narrow-complex tachycardia (QRS < 120 ms unless aberrant conduction)",
    "Abrupt onset and termination",
    "P waves may be buried in QRS, T wave, or visible on baseline",
    "1:1 AV conduction",
    "Adenosine-responsive (diagnostic and therapeutic)",
  ],
  source: "ACC/AHA/ESC Guidelines for Management of SVA",
};

const JUNCTIONAL: RhythmCriteria = {
  definition: "Abnormal rhythm originating from the AV node or junction, typically at an escape rate of 40–60 bpm.",
  diagnosticCriteria: [
    "Rate: 40–60 bpm (junctional escape rhythm)",
    "Regular rhythm with constant intervals",
    "Narrow QRS complexes (<120 ms) — impulse travels via bundle of His",
    "P waves absent or inverted",
    "If P visible: retrograde conduction (P may appear before, during, or after QRS)",
    "AV dissociation possible",
  ],
  source: "AHA/ACC Diagnostic Criteria",
  clinicalNotes: "Rate spectrum: junctional bradycardia <40 bpm; escape rhythm 40–60 bpm; accelerated junctional 60–100 bpm; junctional tachycardia >100 bpm.",
};

const ACCEL_JUNCTIONAL: RhythmCriteria = {
  definition: "Junctional rhythm with rate 60–100 bpm, faster than the typical escape rate, representing enhanced AV nodal automaticity.",
  diagnosticCriteria: [
    "Rate: 60–100 bpm",
    "Regular rhythm",
    "Narrow QRS (<120 ms)",
    "P waves absent or inverted",
    "May represent enhanced automaticity of AV node",
    "Generally benign, often seen post-MI",
  ],
  source: "AHA/ACC Diagnostic Criteria",
};

const IDIOVENTRICULAR: RhythmCriteria = {
  definition: "Automatic escape rhythm originating in the ventricular myocardium, typically when higher pacemakers fail.",
  diagnosticCriteria: [
    "Rate: 20–40 bpm",
    "Regular rhythm",
    "Wide QRS complexes (≥120 ms, often 140–180 ms)",
    "Absence of preceding P waves or AV dissociation",
    "Last-resort escape mechanism when junctional pacemakers fail",
    "Often seen in ischemia, hyperkalemia, or severe conduction block",
  ],
  source: "2018 ACC/AHA/HRS Guideline on Bradycardia and Conduction Delay",
};

const AVB1: RhythmCriteria = {
  definition: "Delayed AV conduction with all atrial impulses reaching the ventricles, but with prolongation of conduction time.",
  diagnosticCriteria: [
    "PR interval > 200 ms (0.20 s) in adults",
    "All P waves followed by QRS complexes",
    "QRS, P wave, and baseline morphology normal",
    "1:1 AV conduction maintained",
    "Regular rhythm",
    "May be normal variant or indicate structural disease/medication effect",
  ],
  source: "2018 ACC/AHA/HRS Guideline on Bradycardia and Conduction Delay",
};

const MOBITZ1: RhythmCriteria = {
  definition: "Progressive prolongation of PR interval until one atrial impulse is not conducted, then cycle resets (Wenckebach phenomenon).",
  diagnosticCriteria: [
    "PR interval progressively lengthens beat-to-beat",
    "Dropped QRS after the longest PR interval",
    "After dropped beat, PR interval resets to shorter interval",
    "Pattern repeats cyclically",
    "RR intervals progressively shorten; longest RR is after the dropped beat",
    "Narrow QRS unless aberrant conduction",
    "Usually benign; often at rest or with increased vagal tone",
  ],
  source: "2018 ACC/AHA/HRS Guideline on Bradycardia and Conduction Delay",
};

const MOBITZ2: RhythmCriteria = {
  definition: "Sudden, unpredictable loss of AV conduction without prior PR prolongation, indicating infranodal (His-Purkinje) block.",
  diagnosticCriteria: [
    "PR interval constant (no progressive prolongation)",
    "Periodic dropped QRS complexes without warning",
    "Block occurs suddenly",
    "QRS often wide (≥120 ms) due to infranodal location",
    "High risk of progression to 3rd degree block",
    "More serious than Mobitz I; often requires pacing",
  ],
  source: "2018 ACC/AHA/HRS Guideline on Bradycardia and Conduction Delay",
  clinicalNotes: "Key distinction from Mobitz I: constant PR interval with sudden block (vs. lengthening PR then eventual block). Pacemaker often indicated.",
};

const AVB3: RhythmCriteria = {
  definition: "Complete loss of AV conduction; no atrial impulses reach the ventricles. Atrial and ventricular rhythms are fully independent.",
  diagnosticCriteria: [
    "Regular P waves at atrial rate (typically 60–100 bpm)",
    "Regular QRS complexes at slower ventricular escape rate",
    "No fixed relationship between P waves and QRS complexes (AV dissociation)",
    "P waves march through QRS complexes and T waves",
    "Ventricular rate determined by escape pacemaker: junctional escape 40–60 bpm (narrow QRS), ventricular escape 20–40 bpm (wide QRS)",
    "Atrial rate significantly faster than ventricular rate (>1.3× difference)",
    "Both P-P and R-R intervals are regular",
  ],
  source: "2018 ACC/AHA/HRS Guideline on Bradycardia and Conduction Delay",
  clinicalNotes: "Wide-QRS escape suggests infranodal block with ventricular pacemaker — less stable, higher mortality. Urgent pacing evaluation required.",
};

const PVC: RhythmCriteria = {
  definition: "Ectopic ventricular depolarization occurring prematurely, bypassing the normal His-Purkinje conduction system.",
  diagnosticCriteria: [
    "Wide QRS complexes (≥120 ms)",
    "Occurs prematurely relative to expected sinus beat",
    "Often followed by a full compensatory pause",
    "T wave opposite in polarity to QRS (discordant T wave)",
    "No P wave preceding PVC, or retrograde P wave after QRS",
    "Morphology may be monomorphic or polymorphic",
  ],
  source: "2017 AHA/ACC/HRS Guideline for Ventricular Arrhythmias",
};

const BIGEMINY: RhythmCriteria = {
  definition: "Pattern of alternating sinus beat and PVC, repeating in a 1:1 cycle.",
  diagnosticCriteria: [
    "Repeating pattern: sinus beat, PVC, sinus beat, PVC",
    "Regular overall sequence",
    "Wide QRS for each ectopic beat (≥120 ms)",
    "Usually uniform PVC morphology (monomorphic)",
    "Compensatory pause after each PVC",
  ],
  source: "2017 AHA/ACC/HRS Guideline for Ventricular Arrhythmias",
};

const TRIGEMINY: RhythmCriteria = {
  definition: "Pattern of two consecutive sinus beats followed by a PVC, repeating regularly.",
  diagnosticCriteria: [
    "Pattern: sinus beat, sinus beat, PVC — repeating",
    "Regular overall sequence",
    "Wide QRS for each ectopic beat (≥120 ms)",
    "Usually monomorphic PVC morphology",
    "Compensatory pause after each PVC",
  ],
  source: "2017 AHA/ACC/HRS Guideline for Ventricular Arrhythmias",
};

const VT: RhythmCriteria = {
  definition: "Rapid ventricular arrhythmia originating from ventricular myocardium, defined as ≥3 consecutive PVCs at rate ≥100 bpm.",
  diagnosticCriteria: [
    "Heart rate typically 100–250 bpm",
    "Wide QRS complexes (≥120 ms, often ≥140 ms)",
    "Regular or slightly irregular rhythm",
    "AV dissociation: P waves visible at a different rate from QRS (pathognomonic)",
    "Fusion beats: narrow QRS from collision of atrial and ventricular impulses",
    "Capture beats: narrow QRS from sinus conduction interrupting VT",
    "Brugada criterion: no RS complex in any precordial lead, or RS interval > 100 ms",
    "Concordance (all positive or all negative) in precordial leads supports VT",
  ],
  source: "2017 AHA/ACC/HRS Guideline for Ventricular Arrhythmias",
  clinicalNotes: "Sustained VT: >30 seconds or requiring termination. NSVT: <30 seconds, self-terminating. AV dissociation is pathognomonic for VT.",
};

const VFIB: RhythmCriteria = {
  definition: "Chaotic, disorganized ventricular electrical activity resulting in no organized contraction and absent perfusion.",
  diagnosticCriteria: [
    "Rapid, chaotic baseline oscillations",
    "No organized QRS complexes identifiable",
    "No identifiable P waves",
    "Amplitude varies (coarse VFib >200 µV; fine VFib <200 µV)",
    "Incompatible with life — requires immediate defibrillation",
  ],
  source: "2017 AHA/ACC/HRS Guideline for Ventricular Arrhythmias",
};

const ASYSTOLE: RhythmCriteria = {
  definition: "Complete absence of electrical and mechanical cardiac activity.",
  diagnosticCriteria: [
    "Flat baseline",
    "No P waves, QRS complexes, or T waves",
    "May have occasional artifact from electrode movement or chest compressions",
    "Most severe form of cardiac arrest",
  ],
  source: "AHA/ACC Cardiac Arrest Guidelines",
};

const LBBB: RhythmCriteria = {
  definition: "Conduction delay or block in the left bundle, delaying left ventricular depolarization with characteristic ECG pattern.",
  diagnosticCriteria: [
    "QRS duration ≥120 ms",
    "Broad, notched R wave (or RR') in lateral leads (I, aVL, V5–V6)",
    "Deep S wave in right precordial leads (V1–V3)",
    "Absent Q wave in lateral leads (I, aVL, V5–V6)",
    "ST-segment and T-wave changes opposite to QRS direction (secondary changes)",
    "Delayed intrinsicoid deflection in V5–V6 (>60 ms from QRS onset to peak)",
  ],
  source: "AHA/ACCF/HRS ECG Standardization 2009",
  clinicalNotes: "Morphological diagnosis, not a rhythm. Indicates significant conduction delay. May mask STEMI — requires modified criteria (Sgarbossa).",
};

const RBBB: RhythmCriteria = {
  definition: "Conduction delay or block in the right bundle, delaying right ventricular depolarization.",
  diagnosticCriteria: [
    "QRS duration ≥120 ms",
    "RSR' pattern (M-shaped, 'rabbit ears') in V1–V2",
    "Wide S wave in lateral leads (I, V5–V6)",
    "T wave inversion in V1–V2 (secondary change)",
  ],
  source: "AHA/ACCF/HRS ECG Standardization 2009",
  clinicalNotes: "Common in PE, chronic lung disease, atrial septal defect. Can be chronic or new (acute RBBB suggests RV strain or ischemia).",
};

const LAFB: RhythmCriteria = {
  definition: "Conduction block in the anterior branch of the left bundle, altering QRS axis without significant QRS widening.",
  diagnosticCriteria: [
    "Marked left axis deviation (QRS axis −45° to −90°)",
    "Small r wave then deep S wave in lead III (rS pattern)",
    "Small q wave then tall R wave in lead aVL (qR pattern)",
    "QRS duration 100–120 ms (narrower than complete LBBB)",
    "Delayed intrinsicoid deflection in aVL",
  ],
  source: "AHA/ACCF/HRS ECG Standardization 2009",
  clinicalNotes: "Most common fascicular block. Often associated with inferior MI. May be a normal variant in thin-chested individuals.",
};

const ANTERIOR_STEMI: RhythmCriteria = {
  definition: "ST-segment elevation MI of the anterior wall from LAD (left anterior descending) coronary artery occlusion.",
  diagnosticCriteria: [
    "ST elevation ≥1 mm in two contiguous precordial leads (V1–V4)",
    "Loss of R wave progression or r/R ratio <1/3 in V2–V3 (may develop Q waves)",
    "Reciprocal ST depression in II, III, aVF",
    "Elevated cardiac biomarkers (troponin, CK-MB)",
  ],
  source: "2025 ACC/AHA/ACEP/NAEMSP/SCAI Guideline for Acute Coronary Syndromes",
  clinicalNotes: "May have right ventricular involvement from proximal RV branch occlusion. T-wave inversions develop after the ST elevation phase.",
};

const INFERIOR_STEMI: RhythmCriteria = {
  definition: "ST-segment elevation MI of the inferior wall from RCA or left circumflex (LCx) coronary artery occlusion.",
  diagnosticCriteria: [
    "ST elevation ≥1 mm in two contiguous inferior leads (II, III, aVF)",
    "Reciprocal ST depression in I, aVL, V1–V2",
    "May develop Q waves",
    "Elevated cardiac biomarkers",
  ],
  source: "2025 ACC/AHA/ACEP/NAEMSP/SCAI Guideline for Acute Coronary Syndromes",
  clinicalNotes: "May include right ventricular MI or posterior extension. Often associated with vagal bradycardia or AV block. Avoid nitrates if RV involvement suspected.",
};

const LATERAL_STEMI: RhythmCriteria = {
  definition: "ST-segment elevation MI of the lateral wall from left circumflex (LCx) or diagonal branch occlusion.",
  diagnosticCriteria: [
    "ST elevation ≥1 mm in lateral leads (I, aVL, V5–V6)",
    "May have reciprocal changes in inferior or precordial leads",
    "Elevated cardiac biomarkers",
    "Q waves may develop",
  ],
  source: "2025 ACC/AHA/ACEP/NAEMSP/SCAI Guideline for Acute Coronary Syndromes",
};

const POSTERIOR_STEMI: RhythmCriteria = {
  definition: "ST-segment elevation MI of the posterior wall, often from RCA or LCx occlusion — a STEMI equivalent requiring urgent intervention.",
  diagnosticCriteria: [
    "ST depression in V1–V2 (mirror image of posterior ST elevation)",
    "Tall, broad R wave in V1 (mirror of posterior Q wave)",
    "ST elevation in posterior leads (V7–V9 if obtained)",
    "Often associated with inferior STEMI",
    "Elevated cardiac biomarkers",
  ],
  source: "2025 ACC/AHA/ACEP/NAEMSP/SCAI Guideline for Acute Coronary Syndromes",
  clinicalNotes: "Often missed without posterior leads. ST depression in V1–V2 with upright T waves should prompt posterior lead placement.",
};

const NSTEMI: RhythmCriteria = {
  definition: "Myocardial infarction without ST elevation, presenting with ischemic ST changes and elevated biomarkers; typically subendocardial.",
  diagnosticCriteria: [
    "ST depression ≥1 mm in two contiguous leads",
    "Elevated troponin or CK-MB",
    "Symptoms consistent with chest pain or anginal equivalent",
    "T-wave inversion may be present",
    "No STEMI criteria met",
  ],
  source: "2025 ACC/AHA/ACEP/NAEMSP/SCAI Guideline for Acute Coronary Syndromes",
};

const WELLENS_A: RhythmCriteria = {
  definition: "Reperfusion pattern after partial LAD occlusion indicating critical proximal LAD stenosis — a STEMI equivalent requiring urgent angiography.",
  diagnosticCriteria: [
    "Biphasic T waves in V2–V3 (positive then negative terminal portion) — Type A",
    "ST segment usually <1 mm elevation or normal",
    "No loss of R wave (differentiates from acute MI with Q wave)",
    "History of recent chest pain with interval since symptom onset",
    "Pattern specific to LAD ischemia/reperfusion",
  ],
  source: "JACC Case Reports: Wellens Pattern",
  clinicalNotes: "Type A (biphasic T waves) represents partial reperfusion pattern. High-risk for reinfarction if not revascularized. Requires urgent angiography.",
};

const WELLENS_B: RhythmCriteria = {
  definition: "Reperfusion pattern after partial LAD occlusion indicating critical proximal LAD stenosis — a STEMI equivalent requiring urgent angiography.",
  diagnosticCriteria: [
    "Deep, symmetric, inverted T waves in V2–V3 (may extend to V4–V5) — Type B",
    "ST segment usually <1 mm elevation or normal",
    "No loss of R wave",
    "History of recent chest pain with interval since symptom onset",
    "Pattern specific to LAD ischemia/reperfusion",
  ],
  source: "JACC Case Reports: Wellens Pattern",
  clinicalNotes: "Type B (deep symmetric inversion) is the more recognized pattern. Critical proximal LAD stenosis — risk of massive anterior MI if untreated.",
};

const PERICARDITIS: RhythmCriteria = {
  definition: "Inflammation of the pericardium producing characteristic evolving ECG changes across four stages.",
  diagnosticCriteria: [
    "Stage 1: Diffuse ST elevation (concave up) with PR depression (except aVR/V1 where PR elevation)",
    "Stage 2: ST normalization with persistent PR depression",
    "Stage 3: Diffuse T-wave inversion",
    "Stage 4: Return to baseline (may take weeks to months)",
    "ST elevation affects multiple territories (not one coronary distribution)",
    "PR depression is key differentiator from STEMI",
  ],
  source: "AHA/ACC Diagnostic Criteria",
  clinicalNotes: "Chest pain typically pleuritic, worse supine, relieved by leaning forward. Pericardial friction rub on exam. Elevated CRP/ESR.",
};

const PE_RV_STRAIN: RhythmCriteria = {
  definition: "Right ventricular strain from acute pulmonary hypertension due to pulmonary embolism.",
  diagnosticCriteria: [
    "T-wave inversion in right precordial leads (V1–V4)",
    "May have ST depression in V1–V2",
    "Sinus tachycardia (most common ECG finding in PE)",
    "May have new RBBB or RSR' pattern in V1",
    "Right axis deviation",
  ],
  source: "AHA/ACC Diagnostic Criteria",
  clinicalNotes: "T-wave inversion in V1–V4 is the most common PE-associated finding. Pattern indicates acute RV strain and correlates with hemodynamic severity.",
};

const PE_S1Q3T3: RhythmCriteria = {
  definition: "Classic but uncommon ECG pattern of acute RV overload from pulmonary embolism.",
  diagnosticCriteria: [
    "S wave in lead I (deep negative terminal deflection)",
    "Q wave in lead III",
    "T-wave inversion in lead III",
    "May also have T-wave inversion in V1–V2",
    "Pattern indicates acute RV dilation and right axis shift",
  ],
  source: "AHA/ACC Diagnostic Criteria",
  clinicalNotes: "S1Q3T3 is present in only ~10–25% of PE cases but is highly specific. Absence does not exclude PE. Sinus tachycardia is more common.",
};

const LVH_STRAIN: RhythmCriteria = {
  definition: "Ventricular remodeling from chronic pressure overload with ischemic secondary repolarization changes (strain pattern).",
  diagnosticCriteria: [
    "Increased QRS voltage: Sokolow-Lyon (SV1 + RV5/V6 ≥35 mm) or Cornell criteria",
    "ST-segment depression in lateral leads (I, aVL, V5–V6)",
    "Symmetric T-wave inversion in lateral leads (strain pattern)",
    "Left axis deviation (optional)",
    "Delayed intrinsicoid deflection in V5–V6 (>60 ms)",
  ],
  source: "AHA/ACC Diagnostic Criteria",
  clinicalNotes: "Strain pattern indicates chronic pressure overload (hypertension, aortic stenosis). Associated with increased cardiovascular risk.",
};

const RV_STRAIN: RhythmCriteria = {
  definition: "Right ventricular pressure overload producing T-wave inversions in right precordial leads.",
  diagnosticCriteria: [
    "T-wave inversion in V1–V4 (right precordial leads)",
    "Right axis deviation",
    "May have S wave in I, Q wave in III (partial S1Q3 pattern)",
    "Elevated P waves (P pulmonale)",
  ],
  source: "AHA/ACC Diagnostic Criteria",
  clinicalNotes: "Seen in PE, pulmonary hypertension, chronic lung disease, acute RV infarction. Distinguish from anterior ischemia by clinical context.",
};

const LAE: RhythmCriteria = {
  definition: "Increased left atrial mass from prolonged volume or pressure overload, producing characteristic P wave changes.",
  diagnosticCriteria: [
    "Broad, bifid (notched) P wave in lead II (duration ≥120 ms)",
    "Deep, wide negative deflection in the terminal portion of P in V1",
    "P wave axis may shift leftward",
    "Often associated with prolonged PR interval",
  ],
  source: "AHA/ACCF/HRS ECG Standardization 2009",
  clinicalNotes: "Seen in hypertension, mitral valve disease, dilated cardiomyopathy. Predisposes to atrial fibrillation.",
};

const RAE: RhythmCriteria = {
  definition: "Increased right atrial mass from chronic lung disease or RV overload, producing tall peaked P waves.",
  diagnosticCriteria: [
    "Tall, peaked P waves in inferior leads (II, III, aVF) ≥2.5 mm (P pulmonale)",
    "Tall P in aVR",
    "Right axis deviation (QRS axis >90°)",
  ],
  source: "AHA/ACCF/HRS ECG Standardization 2009",
  clinicalNotes: "Seen in COPD, pulmonary hypertension, chronic RV overload. P pulmonale in V1 is tall biphasic P (positive initial, negative terminal).",
};

const LQTS: RhythmCriteria = {
  definition: "Genetic or acquired prolongation of cardiac repolarization increasing risk of Torsades de Pointes and sudden cardiac death.",
  diagnosticCriteria: [
    "QTc ≥500 ms — diagnostic in absence of secondary causes",
    "QTc 480–499 ms with unexplained syncope and no secondary cause",
    "Risk of Torsades de Pointes (polymorphic VT with axis rotation)",
    "Family history of sudden unexplained cardiac death",
    "Multiple genetic subtypes (LQT1, LQT2, LQT3 most common)",
  ],
  source: "2017 AHA/ACC/HRS Guideline for Ventricular Arrhythmias",
  clinicalNotes: "QTc = QT / √(RR in seconds). Avoid QT-prolonging medications. Beta-blockers first-line for LQT1 and LQT2. ICD for high-risk patients.",
};

const BRUGADA: RhythmCriteria = {
  definition: "Genetic sodium channelopathy predisposing to VF and sudden cardiac death, especially during sleep or febrile illness.",
  diagnosticCriteria: [
    "Type 1 (diagnostic): Coved ST-segment elevation ≥2 mm in V1–V2",
    "Type 1: Downsloping ST segment with inverted T wave (coved appearance)",
    "J point elevation at junction of QRS and ST segment",
    "Type 2 and 3 patterns are saddleback — not diagnostic without provocation",
    "Type 1 pattern may be unmasked by fever, sodium channel blockers (ajmaline, flecainide)",
  ],
  source: "Proposed Diagnostic Criteria for the Brugada Syndrome, Circulation 2002",
  clinicalNotes: "More common in Southeast Asian populations. ICD indicated for symptomatic patients. Type 1 ECG is diagnostic; other types require provocation testing.",
};

const AAI_PACING: RhythmCriteria = {
  definition: "Atrial demand pacemaker: paces the atrium when intrinsic atrial rate falls below threshold; ventricle conducts normally.",
  diagnosticCriteria: [
    "Pacing spike immediately before each P wave (atrial spike)",
    "Normal QRS complexes following each P wave",
    "1:1 AV conduction maintained",
    "No ventricular pacing spikes visible",
    "PR interval conducted normally",
  ],
  source: "2018 ACC/AHA/HRS Guideline on Bradycardia and Conduction Delay",
  clinicalNotes: "Used for sinus node dysfunction without AV block. Not suitable if AV block is present or suspected.",
};

const DDD_PACING: RhythmCriteria = {
  definition: "Dual-chamber pacemaker sensing and pacing both atria and ventricles with physiologic AV delay; most closely mimics normal conduction.",
  diagnosticCriteria: [
    "Atrial pacing spike followed by P wave",
    "Appropriate AV delay (typically 100–200 ms, shorter than sinus PR)",
    "Ventricular pacing spike followed by QRS complex at end of AV delay",
    "Both chambers show 100% capture",
    "Wide QRS for paced ventricular beats",
  ],
  source: "2018 ACC/AHA/HRS Guideline on Bradycardia and Conduction Delay",
  clinicalNotes: "Most physiologic pacing mode — maintains AV synchrony. Pacemaker syndrome less common than with VVI. Programmed AV delay shorter than intrinsic PR.",
};

const VVI_PACING: RhythmCriteria = {
  definition: "Ventricular demand pacemaker: paces ventricle when intrinsic ventricular rate falls below threshold; no atrial sensing or pacing.",
  diagnosticCriteria: [
    "Pacing spike before each paced QRS complex",
    "Wide QRS complexes (≥120 ms) for all paced beats",
    "Intrinsic beats above rate threshold have no spike (demand mode)",
    "No atrial pacing spikes visible",
    "Loss of AV synchrony (P waves march independently of QRS)",
  ],
  source: "2018 ACC/AHA/HRS Guideline on Bradycardia and Conduction Delay",
  clinicalNotes: "Used when AV block is present or AV synchrony is not achievable. Risk of pacemaker syndrome from loss of AV synchrony.",
};

const ELECTRICAL_ALTERNANS: RhythmCriteria = {
  definition: "Beat-to-beat alternation in QRS-complex (or T-wave) amplitude, most commonly indicating large pericardial effusion with cardiac swinging.",
  diagnosticCriteria: [
    "Alternating tall and short QRS complexes on successive beats",
    "Regular rhythm",
    "May involve P waves, T waves, or entire PQRST complex",
    "Classic finding in large pericardial effusion / tamponade",
    "High clinical urgency — indicates potential hemodynamic compromise",
  ],
  source: "AHA/ACC Diagnostic Criteria",
  clinicalNotes: "Cardiac tamponade triad (Beck's): hypotension, JVD, muffled heart sounds. Electrical alternans + sinus tachycardia = tamponade until proven otherwise.",
};

const HYPERKALEMIA: RhythmCriteria = {
  definition: "Elevated serum potassium producing a spectrum of ECG changes from peaked T waves to sine-wave pattern as level rises.",
  diagnosticCriteria: [
    "Peaked, narrow, tent-shaped T waves in precordial leads",
    "Widened QRS (>120 ms) as level rises",
    "Prolonged PR interval",
    "Flattened or absent P waves at higher levels",
    "Sine-wave pattern at very high levels (severe hyperkalemia)",
    "ST depression may be present",
  ],
  source: "AHA/ACC Diagnostic Criteria",
  clinicalNotes: "ECG changes typically appear at K+ >6.0–6.5 mEq/L. Requires urgent treatment: calcium gluconate stabilizes membrane; insulin + glucose shifts K+ intracellularly.",
};

const PATH_Q_WAVES: RhythmCriteria = {
  definition: "Permanent Q waves from prior transmural myocardial infarction reflecting fibrotic scar tissue, without acute ST changes.",
  diagnosticCriteria: [
    "Q wave width ≥0.04 seconds (≥1 small square) in any lead",
    "Q wave depth ≥25% of R-wave height in the same lead",
    "Territory-specific: anterior (V1–V4), inferior (II, III, aVF), or lateral (I, aVL, V5–V6)",
    "Normal ST segment and T waves (unless concurrent acute change)",
    "Indicates fibrotic scar from prior transmural infarction",
  ],
  source: "2022 ACC/AHA Key Data Elements and Definitions for Chest Pain and AMI",
  clinicalNotes: "Does not indicate active ischemia. Important marker of prior infarction for risk stratification. Differentiate from septal q waves (normal, narrow <0.04 s).",
};

const WPW: RhythmCriteria = {
  definition: "Accessory pathway (bypass tract) conducts atrial impulses directly to ventricles, bypassing the AV node, predisposing to reentrant SVT.",
  diagnosticCriteria: [
    "Short PR interval (<120 ms) — accessory pathway conduction faster than AV node",
    "Delta wave — slurred initial portion of QRS from accessory pathway pre-excitation",
    "Wide QRS (≥120 ms) — fusion of accessory pathway and AV node conduction",
    "Accessory pathway location determines QRS axis and morphology",
    "Prone to orthodromic (narrow-complex) and antidromic (wide-complex) reentrant tachycardias",
  ],
  source: "ACC/AHA/ESC Guidelines for Management of SVA",
  clinicalNotes: "Avoid AV nodal blocking agents (adenosine, verapamil, digoxin) during AF/flutter in WPW — may accelerate conduction via accessory pathway. Risk of VF.",
};

// ---------------------------------------------------------------------------
// Registry
// ---------------------------------------------------------------------------

const REGISTRY = new Map<string, RhythmCriteria>([
  ["Normal Sinus Rhythm", NSR],
  ["Sinus Bradycardia", SINUS_BRADY],
  ["Sinus Tachycardia", SINUS_TACHY],
  ["Sinus Arrhythmia", SINUS_ARRHYTHMIA],
  ["Atrial Fibrillation", AF],
  ["Atrial Fibrillation (RVR)", AF_RVR],
  ["Atrial Flutter (4:1)", AFL],
  ["Premature Atrial Contractions (PACs)", PAC],
  ["SVT (Supraventricular Tachycardia)", SVT],
  ["Junctional Rhythm", JUNCTIONAL],
  ["Accelerated Junctional Rhythm", ACCEL_JUNCTIONAL],
  ["Idioventricular Rhythm", IDIOVENTRICULAR],
  ["1st Degree AV Block", AVB1],
  ["2nd Degree AV Block \u2014 Mobitz I (Wenckebach)", MOBITZ1],
  ["2nd Degree AV Block \u2014 Mobitz II", MOBITZ2],
  ["3rd Degree (Complete) AV Block", AVB3],
  ["Premature Ventricular Contractions (PVCs)", PVC],
  ["Ventricular Bigeminy", BIGEMINY],
  ["Ventricular Trigeminy", TRIGEMINY],
  ["Ventricular Tachycardia (VTach)", VT],
  ["Ventricular Fibrillation (VFib)", VFIB],
  ["Asystole", ASYSTOLE],
  ["Left Bundle Branch Block (LBBB)", LBBB],
  ["Right Bundle Branch Block (RBBB)", RBBB],
  ["Left Anterior Fascicular Block (LAFB)", LAFB],
  ["Anterior STEMI", ANTERIOR_STEMI],
  ["Inferior STEMI", INFERIOR_STEMI],
  ["Lateral STEMI", LATERAL_STEMI],
  ["Posterior STEMI", POSTERIOR_STEMI],
  ["NSTEMI \u2014 ST Depression", NSTEMI],
  ["Wellens Syndrome \u2014 Type A", WELLENS_A],
  ["Wellens Syndrome \u2014 Type B", WELLENS_B],
  ["Pericarditis", PERICARDITIS],
  ["Pulmonary Embolism \u2014 RV Strain", PE_RV_STRAIN],
  ["Pulmonary Embolism \u2014 S1Q3T3", PE_S1Q3T3],
  ["LVH with Strain Pattern", LVH_STRAIN],
  ["RV Strain Pattern", RV_STRAIN],
  ["Left Atrial Enlargement (LAE)", LAE],
  ["Right Atrial Enlargement (RAE)", RAE],
  ["Long QT Syndrome", LQTS],
  ["Brugada Syndrome \u2014 Type 1", BRUGADA],
  ["Atrial Pacing (AAI)", AAI_PACING],
  ["AV Sequential Pacing (DDD)", DDD_PACING],
  ["Ventricular Pacing (VVI)", VVI_PACING],
  ["Electrical Alternans", ELECTRICAL_ALTERNANS],
  ["Hyperkalemia", HYPERKALEMIA],
  ["Pathological Q Waves (Old MI Pattern)", PATH_Q_WAVES],
  ["Wolff-Parkinson-White (WPW)", WPW],
]);

export function getRhythmCriteria(rhythmName: string): RhythmCriteria | null {
  return REGISTRY.get(rhythmName) ?? null;
}

export function getRegisteredRhythms(): string[] {
  return Array.from(REGISTRY.keys());
}
