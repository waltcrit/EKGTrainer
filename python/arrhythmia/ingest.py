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

import importlib
from pathlib import Path
from typing import Any, cast

import numpy as np


# ---------------------------------------------------------------------------
# Optional wfdb import — graceful degradation so the rest of the app still
# runs if wfdb is not installed.
# ---------------------------------------------------------------------------
try:
    wfdb = importlib.import_module("wfdb")
    _wfdb_available = True
except ImportError:
    wfdb = None
    _wfdb_available = False


def _require_wfdb() -> None:
    if not _wfdb_available:
        raise ImportError(
            "wfdb is required for WFDB record ingestion. "
            "Install it with: pip install wfdb"
        )


def load_record(
    record_path: str | Path,
    channel: int = 0,
    sampfrom: int = 0,
    sampto: int | None = None,
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
    assert wfdb is not None
    wfdb_module = cast(Any, wfdb)

    record_path = Path(record_path)
    kwargs: dict[str, int] = {"sampfrom": sampfrom}
    if sampto is not None:
        kwargs["sampto"] = sampto

    record = wfdb_module.rdrecord(str(record_path), channels=[channel], **kwargs)
    p_signal = getattr(record, "p_signal", None)
    fs_value = getattr(record, "fs", None)
    if p_signal is None or fs_value is None:
        raise RuntimeError(f"WFDB record is missing signal data or sampling rate: {record_path}")
    signal: np.ndarray = np.asarray(p_signal[:, 0], dtype=np.float64)
    fs: int = int(fs_value)

    ann: object | None = None
    ann_path = record_path.parent / (record_path.name + ".atr")
    if ann_path.exists():
        try:
            ann = wfdb_module.rdann(str(record_path), "atr", sampfrom=sampfrom, sampto=sampto)
        except Exception:
            ann = None

    return signal, fs, ann


def load_numpy(
    signal: np.ndarray,
    fs: int,
    ann_symbols: list[str] | None = None,
    ann_samples: list[int] | None = None,
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

    sample_values = getattr(ann, "sample", None)
    symbol_values = getattr(ann, "symbol", None)
    if sample_values is None or symbol_values is None:
        return np.array([], dtype=np.int64), np.array([], dtype=str)

    samples = np.asarray(sample_values, dtype=np.int64)
    symbols = np.asarray(symbol_values, dtype=str)

    # Clip to signal bounds
    mask = (samples >= 0) & (samples < signal_length)
    return samples[mask], symbols[mask]
