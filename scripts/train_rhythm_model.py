#!/usr/bin/env python3
# pyright: basic
"""
Train a strip-level multi-class rhythm model on the teaching-case image cache.

This is intended as a *repeatable baseline* to improve generalization over time:
  - digitize cached PNGs -> lead II signal
  - preprocess + resample to 250 Hz
  - train RhythmCNN on 10-second windows
  - (optional) temperature-scale logits on validation set

Requirements
------------
  pip install torch

Usage
-----
  python scripts/train_rhythm_model.py --epochs 50

Outputs
-------
  python/arrhythmia/models/checkpoints/rhythm_cnn.pt
  python/arrhythmia/models/checkpoints/rhythm_cnn.temperature.json  (if calibrated)
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).parent.parent
CASES_JSON = ROOT / "web" / "src" / "data" / "cases.json"
PUBLIC_CASES = ROOT / "web" / "public" / "cases"
OUT_DIR = ROOT / "python" / "arrhythmia" / "models" / "checkpoints"


STRIP_LABELS: list[str] = ["NSR", "SB", "ST", "AF", "AFL", "SVT", "VT", "VF", "ASYS"]


def canonical_strip_label(rhythm: str) -> str | None:
    r = " ".join(rhythm.lower().strip().split())
    if "normal sinus rhythm" in r:
        return "NSR"
    if "sinus bradycardia" in r:
        return "SB"
    if "sinus tachycardia" in r:
        return "ST"
    if "atrial fibrillation" in r or "afib" in r:
        return "AF"
    if "atrial flutter" in r:
        return "AFL"
    if "svt" in r or "supraventricular" in r:
        return "SVT"
    if "ventricular tachycardia" in r or "vtach" in r:
        return "VT"
    if "ventricular fibrillation" in r or "vfib" in r:
        return "VF"
    if "asystole" in r:
        return "ASYS"
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=50)
    ap.add_argument("--lr", type=float, default=2e-3)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--val-frac", type=float, default=0.2)
    ap.add_argument("--no-calibrate", action="store_true")
    args = ap.parse_args()

    # Local imports (repo code)
    sys.path.insert(0, str(ROOT / "python"))
    from ecg import digitize_image  # type: ignore
    from arrhythmia.preprocess import preprocess  # type: ignore
    from arrhythmia.models.rhythm_model import RhythmCNN  # type: ignore

    try:
        import torch
        import torch.nn as nn
    except Exception as exc:
        raise SystemExit(f"PyTorch not available: {exc}\nInstall with: pip install torch") from exc

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    cases = json.loads(CASES_JSON.read_text(encoding="utf-8"))
    rows: list[tuple[str, Path, str]] = []
    for c in cases:
        cid = c.get("id")
        rh = c.get("rhythm")
        if not isinstance(cid, str) or not isinstance(rh, str):
            continue
        lbl = canonical_strip_label(rh)
        if lbl is None:
            continue
        img = PUBLIC_CASES / f"{cid}.png"
        if img.exists():
            rows.append((cid, img, lbl))

    if len(rows) < 10:
        raise SystemExit(f"Not enough labeled strip images found (got {len(rows)})")

    # Shuffle and split
    random.shuffle(rows)
    n_val = max(1, int(len(rows) * args.val_frac))
    val_rows = rows[:n_val]
    train_rows = rows[n_val:]

    label_to_idx = {l: i for i, l in enumerate(STRIP_LABELS)}

    def _make_xy(sample_rows: list[tuple[str, Path, str]]) -> tuple[np.ndarray, np.ndarray]:
        xs: list[np.ndarray] = []
        ys: list[int] = []
        for _, img, lbl in sample_rows:
            d = digitize_image(str(img))
            lead = "II" if "II" in d["signals"] else next(iter(d["signals"]))
            sig = np.asarray(d["signals"][lead], dtype=np.float64)
            fs = int(d["sampling_rate"])
            proc, eff_fs = preprocess(sig, fs, target_fs=250)
            # Take a 10s window from the start; pad/truncate to 2500 samples
            x = proc[: 2500] if len(proc) >= 2500 else np.pad(proc, (0, 2500 - len(proc)))
            xs.append(x.astype(np.float32))
            ys.append(label_to_idx[lbl])
        X = np.stack(xs, axis=0)  # (N, 2500)
        y = np.asarray(ys, dtype=np.int64)
        return X, y

    X_tr, y_tr = _make_xy(train_rows)
    X_va, y_va = _make_xy(val_rows)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = RhythmCNN(num_classes=len(STRIP_LABELS), input_len=2500).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    loss_fn = nn.CrossEntropyLoss()

    def _batch_iter(X: np.ndarray, y: np.ndarray, batch_size: int = 8):
        idx = np.arange(len(X))
        np.random.shuffle(idx)
        for i in range(0, len(X), batch_size):
            b = idx[i : i + batch_size]
            xb = torch.tensor(X[b]).unsqueeze(1).to(device)  # (B,1,L)
            yb = torch.tensor(y[b]).to(device)
            yield xb, yb

    def _eval_acc(X: np.ndarray, y: np.ndarray) -> float:
        model.eval()
        correct = 0
        with torch.no_grad():
            xb = torch.tensor(X).unsqueeze(1).to(device)
            logits = model(xb)
            pred = torch.argmax(logits, dim=-1).cpu().numpy()
            correct = int(np.sum(pred == y))
        return correct / len(X)

    best_val = -1.0
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ckpt_path = OUT_DIR / "rhythm_cnn.pt"

    for epoch in range(1, args.epochs + 1):
        model.train()
        losses: list[float] = []
        for xb, yb in _batch_iter(X_tr, y_tr):
            opt.zero_grad()
            logits = model(xb)
            loss = loss_fn(logits, yb)
            loss.backward()
            opt.step()
            losses.append(float(loss.item()))

        val_acc = _eval_acc(X_va, y_va)
        tr_acc = _eval_acc(X_tr, y_tr)
        avg_loss = float(np.mean(losses)) if losses else 0.0
        print(f"epoch {epoch:03d} loss={avg_loss:.4f} train_acc={tr_acc:.3f} val_acc={val_acc:.3f}")

        if val_acc > best_val:
            best_val = val_acc
            torch.save(model.state_dict(), ckpt_path)

    print(f"\nSaved best checkpoint: {ckpt_path} (val_acc={best_val:.3f}, device={device})")

    if args.no_calibrate:
        return

    # Temperature scaling on validation set (simple NLL minimization)
    model.load_state_dict(torch.load(ckpt_path, map_location=device))
    model.eval()
    T = torch.nn.Parameter(torch.ones((), device=device) * 1.0)
    optT = torch.optim.LBFGS([T], lr=0.1, max_iter=50)

    xb = torch.tensor(X_va).unsqueeze(1).to(device)
    yb = torch.tensor(y_va).to(device)

    def _closure():
        optT.zero_grad()
        with torch.no_grad():
            logits = model(xb)
        loss = loss_fn(logits / torch.clamp(T, 1e-3, 100.0), yb)
        loss.backward()
        return loss

    optT.step(_closure)
    temp = float(T.detach().cpu().item())
    out_temp = OUT_DIR / "rhythm_cnn.temperature.json"
    out_temp.write_text(json.dumps({"temperature": temp}, indent=2), encoding="utf-8")
    print(f"Saved temperature scaling: {out_temp} (T={temp:.3f})")


if __name__ == "__main__":
    main()

