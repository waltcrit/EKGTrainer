# pyright: basic

"""
Strip-level deep learning models for rhythm classification.

Classes: NSR, SB, ST, AF, AFL, SVT, VT, VF, Asystole
Input  : fixed-length 1-D rhythm window (default 2500 samples = 10 s at 250 Hz)

Three architectures are provided — choose based on available compute:
  RhythmCNN         : fast, low memory, good baseline
  RhythmRNN         : captures temporal context via bidirectional LSTM
  RhythmTransformer : best accuracy, requires more compute

Usage
-----
    model = RhythmCNN(num_classes=9, input_len=2500)
    logits = model(x)   # x: (batch, 1, input_len)

    model = RhythmRNN(num_classes=9, input_len=2500)
    logits = model(x)   # x: (batch, input_len, 1)

Requires
--------
    pip install torch
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Optional, Self, cast

import numpy as np

try:
    import torch
    import torch.nn as nn
    _TORCH_AVAILABLE = True
except ImportError:
    torch = None  # type: ignore
    nn = None  # type: ignore
    _TORCH_AVAILABLE = False


def _require_torch() -> None:
    if not _TORCH_AVAILABLE:
        raise ImportError(
            "PyTorch is required for deep learning models. "
            "Install with: pip install torch"
        )


# ---------------------------------------------------------------------------
# Shared mixin
# ---------------------------------------------------------------------------

class _RhythmModelMixin:
    """Shared inference utilities for rhythm models."""

    num_classes: int
    input_len: int

    @classmethod
    def from_checkpoint(
        cls,
        checkpoint_path: str | Path,
        num_classes: int = 9,
        input_len: int = 2500,
        device: str = "cpu",
        **kwargs,
    ) -> Self:
        _require_torch()
        assert torch is not None
        model = cast(Any, cls)(num_classes=num_classes, input_len=input_len, **kwargs)
        state = torch.load(checkpoint_path, map_location=device)
        model.load_state_dict(state)
        model.eval()
        return cast(Self, model)

    def predict_numpy(
        self,
        windows: list[np.ndarray],
        label_map: Optional[list[str]] = None,
    ) -> list[dict]:
        _require_torch()
        assert torch is not None
        if label_map is None:
            from arrhythmia.constants import ArrhythmiaClass
            label_map = [
                ArrhythmiaClass.NSR, ArrhythmiaClass.SB, ArrhythmiaClass.ST,
                ArrhythmiaClass.AF, ArrhythmiaClass.AFL, ArrhythmiaClass.SVT,
                ArrhythmiaClass.VT, ArrhythmiaClass.VF, ArrhythmiaClass.ASYS,
            ]

        from arrhythmia.segments import pad_or_truncate

        results = []
        model = cast(Any, self)
        model.eval()
        with torch.no_grad():
            for w in windows:
                arr = np.asarray(w, dtype=np.float32)
                arr = pad_or_truncate(arr, self.input_len).astype(np.float32)
                # Shape depends on model type — handled in subclasses
                tensor = model._prepare_input(arr)
                logits = model(tensor)
                probs = torch.softmax(logits, dim=-1).squeeze().cpu().numpy()
                pred_idx = int(np.argmax(probs))
                results.append({
                    "label": label_map[pred_idx],
                    "confidence": float(probs[pred_idx]),
                    "probabilities": {label_map[i]: float(p) for i, p in enumerate(probs)},
                })
        return results

    def _prepare_input(self, arr: np.ndarray):  # type: ignore
        """Override in subclasses to return the correct tensor shape."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# RhythmCNN
# ---------------------------------------------------------------------------

class RhythmCNN(_RhythmModelMixin, nn.Module if _TORCH_AVAILABLE else object):  # type: ignore
    """
    Deep 1-D CNN for 10-second rhythm strip classification.

    Architecture
    ------------
    Input: (batch, 1, input_len)

    5 convolutional blocks with increasing channels and MaxPool:
      32 → 64 → 128 → 256 → 256
    Global average pooling → FC(256, 128) → ReLU → Dropout → FC(128, num_classes)
    """

    def __init__(self, num_classes: int = 9, input_len: int = 2500) -> None:
        _require_torch()
        assert nn is not None
        super().__init__()
        nn_module = nn
        self.num_classes = num_classes
        self.input_len = input_len

        def conv_block(in_ch, out_ch, k, pool=2):
            return nn_module.Sequential(
                nn_module.Conv1d(in_ch, out_ch, kernel_size=k, padding=k // 2),
                nn_module.BatchNorm1d(out_ch),
                nn_module.ReLU(),
                nn_module.MaxPool1d(pool),
            )

        self.backbone = nn_module.Sequential(
            conv_block(1, 32, 15),
            conv_block(32, 64, 11),
            conv_block(64, 128, 7),
            conv_block(128, 256, 5),
            conv_block(256, 256, 3),
        )
        self.head = nn_module.Sequential(
            nn_module.AdaptiveAvgPool1d(1),
            nn_module.Flatten(),
            nn_module.Linear(256, 128),
            nn_module.ReLU(),
            nn_module.Dropout(0.4),
            nn_module.Linear(128, num_classes),
        )

    def forward(self, x):  # type: ignore
        return self.head(self.backbone(x))

    def _prepare_input(self, arr):  # type: ignore
        assert torch is not None
        return torch.tensor(arr).unsqueeze(0).unsqueeze(0)  # (1,1,L)


# ---------------------------------------------------------------------------
# RhythmRNN
# ---------------------------------------------------------------------------

class RhythmRNN(_RhythmModelMixin, nn.Module if _TORCH_AVAILABLE else object):  # type: ignore
    """
    Bidirectional LSTM for 10-second rhythm strip classification.

    Input : (batch, seq_len, 1)  — each time step is a single amplitude
    The signal is downsampled via a lightweight CNN front-end before the LSTM
    to keep sequence length manageable.

    Architecture
    ------------
    CNN front-end: 2 conv blocks → (batch, 64, seq/4)
    Reshape      : (batch, seq/4, 64)
    BiLSTM       : 2 layers, hidden=128 → (batch, seq/4, 256)
    Attention    : soft attention over time steps
    FC head      : Linear(256, num_classes)
    """

    def __init__(
        self,
        num_classes: int = 9,
        input_len: int = 2500,
        lstm_hidden: int = 128,
        lstm_layers: int = 2,
    ) -> None:
        _require_torch()
        assert nn is not None
        assert torch is not None
        super().__init__()
        self.num_classes = num_classes
        self.input_len = input_len

        # Lightweight CNN front-end to reduce sequence length
        self.cnn_front = nn.Sequential(
            nn.Conv1d(1, 32, kernel_size=7, padding=3),
            nn.ReLU(),
            nn.MaxPool1d(2),
            nn.Conv1d(32, 64, kernel_size=5, padding=2),
            nn.ReLU(),
            nn.MaxPool1d(2),
        )  # output: (batch, 64, input_len/4)

        self.lstm = nn.LSTM(
            input_size=64,
            hidden_size=lstm_hidden,
            num_layers=lstm_layers,
            batch_first=True,
            bidirectional=True,
            dropout=0.3 if lstm_layers > 1 else 0.0,
        )
        lstm_out_size = lstm_hidden * 2  # bidirectional

        self.attention = nn.Linear(lstm_out_size, 1)
        self.classifier = nn.Linear(lstm_out_size, num_classes)

    def forward(self, x):  # type: ignore
        assert torch is not None
        # x: (batch, 1, L) or (batch, L, 1)
        if x.dim() == 3 and x.shape[1] != 1:
            x = x.permute(0, 2, 1)  # -> (batch, 1, L)

        cnn_out = self.cnn_front(x)          # (batch, 64, L/4)
        seq = cnn_out.permute(0, 2, 1)       # (batch, L/4, 64)
        lstm_out, _ = self.lstm(seq)         # (batch, L/4, 256)

        # Soft attention
        attn_weights = torch.softmax(self.attention(lstm_out), dim=1)  # (batch, L/4, 1)
        context = (lstm_out * attn_weights).sum(dim=1)                 # (batch, 256)

        return self.classifier(context)

    def _prepare_input(self, arr):  # type: ignore
        assert torch is not None
        return torch.tensor(arr).unsqueeze(0).unsqueeze(0)  # (1,1,L)


# ---------------------------------------------------------------------------
# RhythmTransformer
# ---------------------------------------------------------------------------

class _PositionalEncoding(nn.Module if _TORCH_AVAILABLE else object):  # type: ignore
    """Sinusoidal positional encoding for Transformer input."""

    def __init__(self, d_model: int, max_len: int = 5000, dropout: float = 0.1) -> None:
        _require_torch()
        assert nn is not None
        assert torch is not None
        super().__init__()
        self.dropout = nn.Dropout(dropout)
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(
            torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model)
        )
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)  # (1, max_len, d_model)
        self.register_buffer("pe", pe)

    def forward(self, x):  # type: ignore
        x = x + self.pe[:, : x.size(1), :]
        return self.dropout(x)


class RhythmTransformer(
    _RhythmModelMixin,
    nn.Module if _TORCH_AVAILABLE else object,  # type: ignore
):
    """
    Transformer encoder for 10-second rhythm strip classification.

    Architecture
    ------------
    CNN patch embedding : 1-D conv with stride → (batch, seq_patches, d_model)
    Positional encoding
    Transformer encoder : n_layers × (self-attn + FFN)
    CLS token aggregation → Linear(d_model, num_classes)

    Parameters
    ----------
    patch_size  : samples per patch (stride of CNN embedding), default 25
    d_model     : embedding dimension, default 128
    nhead       : attention heads, default 8
    n_layers    : transformer encoder layers, default 4
    """

    def __init__(
        self,
        num_classes: int = 9,
        input_len: int = 2500,
        patch_size: int = 25,
        d_model: int = 128,
        nhead: int = 8,
        n_layers: int = 4,
        dropout: float = 0.1,
    ) -> None:
        _require_torch()
        assert nn is not None
        assert torch is not None
        super().__init__()
        self.num_classes = num_classes
        self.input_len = input_len
        self.d_model = d_model

        # Patch embedding via strided convolution
        self.patch_embed = nn.Sequential(
            nn.Conv1d(1, d_model, kernel_size=patch_size, stride=patch_size),
            nn.LayerNorm([d_model, input_len // patch_size]),  # approximate
        )

        # CLS token
        self.cls_token = nn.Parameter(torch.zeros(1, 1, d_model))

        self.pos_enc = _PositionalEncoding(d_model, max_len=input_len // patch_size + 1, dropout=dropout)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=d_model * 4,
            dropout=dropout,
            batch_first=True,
            norm_first=True,  # pre-LN for stability
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)
        self.classifier = nn.Linear(d_model, num_classes)

    def forward(self, x):  # type: ignore
        assert torch is not None
        # x: (batch, 1, L)
        patches = self.patch_embed(x).permute(0, 2, 1)  # (batch, T, d_model)
        batch_size = patches.size(0)
        cls = self.cls_token.expand(batch_size, -1, -1)  # (batch, 1, d_model)
        seq = torch.cat([cls, patches], dim=1)            # (batch, T+1, d_model)
        seq = self.pos_enc(seq)
        out = self.transformer(seq)                        # (batch, T+1, d_model)
        cls_out = out[:, 0, :]                            # (batch, d_model)
        return self.classifier(cls_out)

    def _prepare_input(self, arr):  # type: ignore
        assert torch is not None
        return torch.tensor(arr).unsqueeze(0).unsqueeze(0)  # (1,1,L)
