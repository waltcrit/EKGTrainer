import sys
from pathlib import Path


def test_afib_not_ectopy_false_positive() -> None:
    """
    Regression test for a common generalization failure:
    patterned irregularity (bigeminy/trigeminy) being mislabeled as AF.
    """
    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root / "python"))

    from ecg import digitize_image  # type: ignore
    from arrhythmia.inference import classify_ecg  # type: ignore
    from arrhythmia.constants import ArrhythmiaClass  # type: ignore

    def _pred(case_id: str) -> str:
        img = repo_root / "web" / "public" / "cases" / f"{case_id}.png"
        d = digitize_image(str(img))
        lead = "II" if "II" in d["signals"] else next(iter(d["signals"]))
        res = classify_ecg(d["signals"][lead], int(d["sampling_rate"]))
        raw = getattr(res.primary_rhythm, "value", res.primary_rhythm)
        return str(raw)

    assert _pred("afib_01") == ArrhythmiaClass.AF
    assert _pred("bigu_01") != ArrhythmiaClass.AF
    assert _pred("trigu_01") != ArrhythmiaClass.AF

