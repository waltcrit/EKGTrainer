"""Claude prompt builder from ECG measurements."""
from __future__ import annotations

import json

from ecg.types import PipelineClassification, SignalMeasurements


def build_claude_prompt(
    measurements: SignalMeasurements,
    digitizer_method: str,
    pipeline_classification: PipelineClassification | None = None,
) -> str:
    """
    Build the Claude prompt from signal measurements.
    Includes calibration caveats, AFib hints, and pipeline pre-classification.
    """
    rr = measurements["rr_intervals_ms"]
    rr_str = ", ".join(f"{x:.0f}" for x in rr[:6]) if rr else "unavailable"

    st_lines: list[str] = []
    for lead, v in measurements["st"].items():
        if v["elevation"]:
            st_lines.append(f"  {lead}: elevated ({v['mean_mv']:+.2f} mV)")
        elif v["depression"]:
            st_lines.append(f"  {lead}: depressed ({v['mean_mv']:+.2f} mV)")
    st_summary = "\n".join(st_lines) if st_lines else "  No significant ST deviation detected"

    if pipeline_classification and "error" not in pipeline_classification:
        pc = pipeline_classification
        hint_lines: list[str] = [
            "",
            "SIGNAL PIPELINE PRE-CLASSIFICATION (PhysioNet-compatible detector):",
            f"- Primary rhythm: {pc.get('display_name', pc.get('primary_rhythm', 'unknown'))} ({pc.get('primary_rhythm', '?')})",
            f"- Confidence: {pc.get('confidence', 0.0):.0%}",
        ]
        notes = pc.get("notes")
        if notes:
            hint_lines.append(f"- Notes: {'; '.join(notes)}")
        hint_lines += [
            "You may confirm or override this classification based on morphology and context.",
            "",
        ]
        pipeline_hint = "\n".join(hint_lines)
    else:
        pipeline_hint = ""

    amp_calibrated = measurements.get("amplitude_calibrated", False)
    calibration_note = "" if amp_calibrated else "\nNOTE: Amplitude calibration unavailable (grid not detected). ST mV values are relative, not absolute."

    afib_note = ""
    if measurements.get("afib_hint"):
        afib_note = "\nSIGNAL HINT: Irregularly irregular rhythm with absent P-waves — strongly consider atrial fibrillation."

    p_morph = measurements.get("p_wave_morphology")
    p_morph_str = f" ({p_morph})" if p_morph else ""

    qtcf = measurements.get("qtcf_ms")
    qtc_method = measurements.get("qtc_method", "bazett")
    qtc_line = f"{measurements['qtc_ms']:.0f} ms (Bazett)" if measurements['qtc_ms'] else "not measurable"
    if qtcf is not None:
        qtc_line += f"  |  {qtcf:.0f} ms (Fridericia)"
    qtc_line += f"  [primary: {qtc_method}]"

    return f"""You are an expert cardiologist reviewing an ECG that has been digitized and algorithmically analyzed. The signal measurements below are derived from the actual waveform — treat them as accurate. Do NOT re-estimate these values visually.{calibration_note}{afib_note}{pipeline_hint}

MEASURED SIGNAL DATA (from {digitizer_method}):
- Heart rate: {measurements['heart_rate_bpm']:.0f} bpm
- RR intervals (ms): {rr_str}
- Rhythm regularity: {measurements['regularity']}
- Beats detected: {measurements['num_beats']}
- P waves present: {measurements['p_waves_present']}{p_morph_str}
- PR interval: {f"{measurements['pr_interval_ms']:.0f} ms" if measurements['pr_interval_ms'] else "not measurable"}
- QRS duration: {f"{measurements['qrs_duration_ms']:.0f} ms" if measurements['qrs_duration_ms'] else "not measurable"}
- QRS wide (≥120ms): {measurements['qrs_wide']}
- QT interval: {f"{measurements['qt_ms']:.0f} ms" if measurements['qt_ms'] else "not measurable"}
- QTc: {qtc_line}
- QTc prolonged: {measurements['qtc_prolonged']}

ST SEGMENT (per lead):
{st_summary}

Using these measurements and the ECG image for morphology context (P-wave axis, QRS shape, T-wave polarity, bundle branch patterns), provide your interpretation as valid JSON matching EXACTLY this schema — no markdown, no extra text:

{{
  "rate": {{
    "bpm": <number>,
    "rr_intervals_ms": {json.dumps(rr[:6])},
    "category": "<bradycardia|normal|tachycardia>",
    "method": "signal-derived",
    "confidence": <0.0-1.0>
  }},
  "rhythm": {{
    "regularity": "<regular|regularly_irregular|irregularly_irregular>",
    "confidence": <0.0-1.0>
  }},
  "p_waves": {{
    "present": <true|false>,
    "signal_morphology": "{measurements.get('p_wave_morphology') or 'null'}",
    "morphology": "<description or null>",
    "ratio": "<e.g. '1:1' or null>",
    "confidence": <0.0-1.0>
  }},
  "pr_interval": {{
    "ms": {measurements['pr_interval_ms'] if measurements['pr_interval_ms'] else 'null'},
    "measured_beats": [],
    "normal": <true|false|null>,
    "fixed": <true|false|null>,
    "confidence": <0.0-1.0>
  }},
  "qrs": {{
    "duration_ms": {measurements['qrs_duration_ms'] if measurements['qrs_duration_ms'] else 'null'},
    "measured_beats_ms": [],
    "wide": {str(measurements['qrs_wide']).lower()},
    "morphology": "<description or null>",
    "confidence": <0.0-1.0>
  }},
  "st_segment": {{
    "elevation": <true|false>,
    "depression": <true|false>,
    "details": "<description or null>",
    "confidence": <0.0-1.0>
  }},
  "t_waves": {{
    "morphology": "<upright|inverted|peaked|flat|biphasic or null>",
    "confidence": <0.0-1.0>
  }},
  "qtc": {{
    "ms": {measurements['qtc_ms'] if measurements['qtc_ms'] else 'null'},
    "fridericia_ms": {measurements.get('qtcf_ms') if measurements.get('qtcf_ms') else 'null'},
    "measured_qt_ms": [{measurements['qt_ms'] if measurements['qt_ms'] else 'null'}],
    "prolonged": {str(measurements['qtc_prolonged']).lower() if measurements['qtc_prolonged'] is not None else 'null'},
    "method": "{measurements.get('qtc_method', 'bazett')}",
    "confidence": <0.0-1.0>
  }},
  "primary_rhythm": "<rhythm name>",
  "overall_confidence": <0.0-1.0>,
  "differentials": ["<rhythm>", "<rhythm>"],
  "explanation": "<2-4 sentence educational explanation grounded in the measured values>",
  "image_quality": "<good|fair|poor>",
  "caveats": "<limitations or null>"
}}"""
