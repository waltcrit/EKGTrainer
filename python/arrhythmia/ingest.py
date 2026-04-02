"""
WFDB record ingestion.

Public API
----------
load_record(record_path, channel)
    -> (signal: np.ndarray, fs: int, annotations: wfdb.Annotation | None)

load_numpy(signal, fs, ann_symbols, ann_samples)
    -> (signal, fs, annotations)  — wrap a raw NumPy signal as a pseudo-record

Raises
------
ImportError  if wfdb is not installed
FileNotFoundError  if the requested record does not exist
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np


# ---------------------------------------------------------------------------
# Optional wfdb import — graceful degradation so the rest of the app still
# runs if wfdb is not installed.
# ---------------------------------------------------------------------------
try:
    import wfdb  # type: ignore
    _WFDB_AVAILABLE = True
except ImportError:
    wfdb = None  # type: ignore
    _WFDB_AVAILABLE = False


def _require_wfdb() -> None:
    if not _WFDB_AVAILABLE:
        raise ImportError(
            "wfdb is required for WFDB record ingestion. "
            "Install it with: pip install wfdb"
        )


def load_record(
    record_path: str | Path,
    channel: int = 0,
    sampfrom: int = 0,
    sampto: Optional[int] = None,
) -> tuple[np.ndarray, int, object]:
    """
    Load a WFDB record from disk.

    Parameters
    ----------
    record_path : path to the record (no extension, e.g. '/data/mitdb/100')
    channel     : which signal channel to return (0-indexed)
    sampfrom    : start sample (inclusive)
    sampto      : end sample (exclusive); None = entire record

    Returns
    -------
    signal       : 1-D float64 array (physical units, e.g. mV)
    fs           : sampling frequency in Hz
    annotations  : wfdb.Annotation object or None if no annotation file exists
    """
    _require_wfdb()

    record_path = Path(record_path)
    kwargs: dict = {"sampfrom": sampfrom}
    if sampto is not None:
        kwargs["sampto"] = sampto

    record = wfdb.rdrecord(str(record_path), channels=[channel], **kwargs)
    signal: np.ndarray = record.p_signal[:, 0].astype(np.float64)
    fs: int = int(record.fs)

    ann = None
    ann_path = record_path.parent / (record_path.name + ".atr")
    if ann_path.exists():
        try:
            ann = wfdb.rdann(str(record_path), "atr", sampfrom=sampfrom, sampto=sampto)
        except Exception:
            ann = None

    return signal, fs, ann


def load_numpy(
    signal: np.ndarray,
    fs: int,
    ann_symbols: Optional[list[str]] = None,
    ann_samples: Optional[list[int]] = None,
) -> tuple[np.ndarray, int, object]:
    """
    Wrap a raw NumPy signal as a pipeline-compatible record.

    Useful for signals that were digitised from images or loaded from CSV/NPZ
    files rather than WFDB format.

    Returns
    -------
    signal       : 1-D float64 array (physical units)
    fs           : sampling frequency in Hz
    annotations  : SimpleNamespace with .symbol and .sample, or None
    """
    from types import SimpleNamespace

    signal = np.asarray(signal, dtype=np.float64).ravel()
    ann = None
    if ann_symbols is not None and ann_samples is not None:
        ann = SimpleNamespace(
            symbol=list(ann_symbols),
            sample=np.asarray(ann_samples, dtype=np.int64),
        )
    return signal, int(fs), ann


def annotation_to_labels(
    ann: object,
    signal_length: int,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Extract beat positions and symbol strings from an annotation object.

    Handles both wfdb.Annotation objects and SimpleNamespace objects
    returned by load_numpy().

    Returns
    -------
    samples : int64 array of sample indices
    symbols : str array of annotation symbols (e.g. 'N', 'V', 'A', '/')
    """
    if ann is None:
        return np.array([], dtype=np.int64), np.array([], dtype=str)

    samples = np.asarray(ann.sample, dtype=np.int64)
    symbols = np.asarray(ann.symbol, dtype=str)

    # Clip to signal bounds
    mask = (samples >= 0) & (samples < signal_length)
    return samples[mask], symbols[mask]
