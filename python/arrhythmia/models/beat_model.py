"""
Beat-level CNN for classifying individual ECG beats.

Classes: NSR (background), PAC, PVC
Input  : fixed-length 1-D signal window (default 150 samples at 250 Hz ≈ 600 ms)

Usage
-----
    model = BeatCNN(num_classes=3, input_len=150)
    logits = model(x)          # x: (batch, 1, input_len) tensor
    probs  = torch.softmax(logits, dim=-1)

Training hooks
--------------
    loss_fn = torch.nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

Model loading
-------------
    model = BeatCNN.from_checkpoint("beat_model.pt")

Requires
--------
    pip install torch
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, TypedDict, cast

import numpy as np

try:
    import torch
    import torch.nn as nn
    _torch_available = True
except ImportError:
    torch = None  # type: ignore
    nn = None  # type: ignore
    _torch_available = False


class BeatPrediction(TypedDict):
    label: str
    confidence: float
    probabilities: dict[str, float]


def _require_torch() -> None:
    if not _torch_available:
        raise ImportError(
            "PyTorch is required for deep learning models. "
            "Install with: pip install torch"
        )


class BeatCNN(nn.Module if _torch_available else object):  # type: ignore
    """
    1-D Convolutional Neural Network for beat-level ECG classification.

    Architecture
    ------------
    Input: (batch, 1, input_len)

    Conv block 1 : Conv1d(1, 32, k=7) → BN → ReLU → MaxPool(2)
    Conv block 2 : Conv1d(32, 64, k=5) → BN → ReLU → MaxPool(2)
    Conv block 3 : Conv1d(64, 128, k=3) → BN → ReLU → MaxPool(2)
    Global avg pool → Dense(128, 64) → ReLU → Dropout(0.3) → Dense(64, num_classes)

    Parameters
    ----------
    num_classes : number of output classes (default 3: NSR, PAC, PVC)
    input_len   : expected input signal length in samples (default 150)
    """

    def __init__(self, num_classes: int = 3, input_len: int = 150) -> None:
        _require_torch()
        assert nn is not None
        super().__init__()  # type: ignore[misc]
        self.num_classes = num_classes
        self.input_len = input_len

        self.conv_blocks = nn.Sequential(
            # Block 1
            nn.Conv1d(1, 32, kernel_size=7, padding=3),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.MaxPool1d(2),
            # Block 2
            nn.Conv1d(32, 64, kernel_size=5, padding=2),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.MaxPool1d(2),
            # Block 3
            nn.Conv1d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.MaxPool1d(2),
        )

        self.classifier = nn.Sequential(
            nn.AdaptiveAvgPool1d(1),  # -> (batch, 128, 1)
            nn.Flatten(),             # -> (batch, 128)
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, num_classes),
        )

    def forward(self, x):  # type: ignore
        """
        Parameters
        ----------
        x : torch.Tensor of shape (batch, 1, input_len)

        Returns
        -------
        logits : torch.Tensor of shape (batch, num_classes)
        """
        x = self.conv_blocks(x)
        return self.classifier(x)

    @classmethod
    def from_checkpoint(
        cls,
        checkpoint_path: str | Path,
        num_classes: int = 3,
        input_len: int = 150,
        device: str = "cpu",
    ) -> "BeatCNN":
        """
        Load model weights from a .pt checkpoint file.

        Parameters
        ----------
        checkpoint_path : path to saved state_dict (.pt file)
        num_classes     : must match the checkpoint
        input_len       : must match the checkpoint
        device          : 'cpu' or 'cuda'

        Returns
        -------
        model : BeatCNN instance with loaded weights, set to eval mode
        """
        _require_torch()
        assert torch is not None
        model = cast(Any, cls(num_classes=num_classes, input_len=input_len))
        state = torch.load(checkpoint_path, map_location=device)
        model.load_state_dict(state)
        model.eval()
        return cast(BeatCNN, model)

    def predict_numpy(
        self,
        windows: list[np.ndarray],
        label_map: Optional[list[str]] = None,
    ) -> list[BeatPrediction]:
        """
        Convenience method: run inference on a list of beat windows.

        Parameters
        ----------
        windows   : list of 1-D float64 beat windows
        label_map : ordered list of class names (default: ['NSR','PAC','PVC'])

        Returns
        -------
        list of dicts: [{"label": str, "probabilities": {class: float}, ...}]
        """
        _require_torch()
        assert torch is not None
        if label_map is None:
            from arrhythmia.constants import ArrhythmiaClass
            label_map = [ArrhythmiaClass.NSR, ArrhythmiaClass.PAC, ArrhythmiaClass.PVC]

        results: list[BeatPrediction] = []
        model = cast(Any, self)
        model.eval()
        with torch.no_grad():
            for w in windows:
                arr = np.asarray(w, dtype=np.float32)
                if len(arr) != self.input_len:
                    from arrhythmia.segments import pad_or_truncate
                    arr = pad_or_truncate(arr, self.input_len).astype(np.float32)
                tensor = torch.tensor(arr).unsqueeze(0).unsqueeze(0)  # (1,1,L)
                logits = model(tensor)
                probs = torch.softmax(logits, dim=-1).squeeze().cpu().numpy()
                pred_idx = int(np.argmax(probs))
                results.append({
                    "label": label_map[pred_idx],
                    "confidence": float(probs[pred_idx]),
                    "probabilities": {label_map[i]: float(p) for i, p in enumerate(probs)},
                })
        return results
