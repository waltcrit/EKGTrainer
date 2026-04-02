"""
PhysioNet-compatible arrhythmia classification scoring.

Implements:
  - Per-class precision, recall, F1
  - Macro-averaged F1 (PhysioNet challenge metric)
  - Confusion matrix
  - Summary report

Public API
----------
compute_metrics(y_true, y_pred, labels)
    -> ClassificationReport

ClassificationReport
    .per_class  : dict[str, PerClassMetrics]
    .macro_f1   : float
    .macro_precision : float
    .macro_recall    : float
    .confusion_matrix : np.ndarray
    .to_dict()  -> dict
    .print_report()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from arrhythmia.constants import ALL_CLASSES


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PerClassMetrics:
    label: str
    precision: float
    recall: float
    f1: float
    support: int  # number of true instances of this class


@dataclass
class ClassificationReport:
    per_class: dict[str, PerClassMetrics]
    macro_f1: float
    macro_precision: float
    macro_recall: float
    confusion_matrix: np.ndarray
    label_order: list[str]

    def to_dict(self) -> dict:
        return {
            "per_class": {
                k: {
                    "precision": v.precision,
                    "recall": v.recall,
                    "f1": v.f1,
                    "support": v.support,
                }
                for k, v in self.per_class.items()
            },
            "macro_f1": self.macro_f1,
            "macro_precision": self.macro_precision,
            "macro_recall": self.macro_recall,
            "confusion_matrix": self.confusion_matrix.tolist(),
            "label_order": self.label_order,
        }

    def print_report(self) -> None:
        header = f"{'Class':<12} {'Precision':>10} {'Recall':>10} {'F1':>10} {'Support':>10}"
        print(header)
        print("-" * len(header))
        for m in self.per_class.values():
            print(
                f"{m.label:<12} {m.precision:>10.4f} {m.recall:>10.4f} "
                f"{m.f1:>10.4f} {m.support:>10}"
            )
        print("-" * len(header))
        print(
            f"{'Macro':<12} {self.macro_precision:>10.4f} "
            f"{self.macro_recall:>10.4f} {self.macro_f1:>10.4f}"
        )


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def compute_metrics(
    y_true: list[str],
    y_pred: list[str],
    labels: Optional[list[str]] = None,
) -> ClassificationReport:
    """
    Compute per-class and macro-averaged metrics.

    Parameters
    ----------
    y_true  : list of ground-truth arrhythmia labels
    y_pred  : list of predicted arrhythmia labels (same length)
    labels  : ordered list of class labels to include;
              defaults to ALL_CLASSES from constants

    Returns
    -------
    ClassificationReport
    """
    if len(y_true) != len(y_pred):
        raise ValueError(
            f"y_true length ({len(y_true)}) != y_pred length ({len(y_pred)})"
        )

    if labels is None:
        # Include only classes that appear in y_true or y_pred
        present = sorted(set(y_true) | set(y_pred))
        # Keep canonical order for classes that are in ALL_CLASSES
        canonical = [c for c in ALL_CLASSES if c in present]
        extras = sorted(c for c in present if c not in ALL_CLASSES)
        labels = canonical + extras

    n = len(labels)
    label_idx = {lbl: i for i, lbl in enumerate(labels)}

    # Build confusion matrix
    cm = np.zeros((n, n), dtype=np.int64)
    for t, p in zip(y_true, y_pred):
        ti = label_idx.get(t)
        pi = label_idx.get(p)
        if ti is not None and pi is not None:
            cm[ti, pi] += 1

    per_class: dict[str, PerClassMetrics] = {}
    precisions: list[float] = []
    recalls: list[float] = []
    f1s: list[float] = []

    for i, lbl in enumerate(labels):
        tp = int(cm[i, i])
        fp = int(cm[:, i].sum()) - tp
        fn = int(cm[i, :].sum()) - tp
        support = int(cm[i, :].sum())

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1        = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        per_class[lbl] = PerClassMetrics(
            label=lbl,
            precision=precision,
            recall=recall,
            f1=f1,
            support=support,
        )
        precisions.append(precision)
        recalls.append(recall)
        f1s.append(f1)

    macro_f1        = float(np.mean(f1s))
    macro_precision = float(np.mean(precisions))
    macro_recall    = float(np.mean(recalls))

    return ClassificationReport(
        per_class=per_class,
        macro_f1=macro_f1,
        macro_precision=macro_precision,
        macro_recall=macro_recall,
        confusion_matrix=cm,
        label_order=labels,
    )


# ---------------------------------------------------------------------------
# PhysioNet-style challenge scoring
# ---------------------------------------------------------------------------

def physionet_score(
    y_true: list[str],
    y_pred: list[str],
    labels: Optional[list[str]] = None,
) -> float:
    """
    Compute the PhysioNet macro-F1 challenge score.

    This is equivalent to the unweighted average of per-class F1 scores
    across all classes in `labels`, as used in PhysioNet/CinC challenges
    for arrhythmia classification.

    Parameters
    ----------
    y_true  : ground-truth labels
    y_pred  : predicted labels
    labels  : classes to score (defaults to ALL_CLASSES)

    Returns
    -------
    macro_f1 : float in [0, 1]
    """
    report = compute_metrics(y_true, y_pred, labels=labels)
    return report.macro_f1


# ---------------------------------------------------------------------------
# Confusion matrix utilities
# ---------------------------------------------------------------------------

def print_confusion_matrix(
    cm: np.ndarray,
    labels: list[str],
    max_width: int = 8,
) -> None:
    """Pretty-print a confusion matrix."""
    col_header = " " * max_width + " ".join(f"{l:>{max_width}}" for l in labels)
    print(col_header)
    for i, lbl in enumerate(labels):
        row = f"{lbl:<{max_width}}" + " ".join(f"{cm[i, j]:>{max_width}}" for j in range(len(labels)))
        print(row)
