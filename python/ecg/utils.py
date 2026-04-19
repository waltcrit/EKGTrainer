"""JSON serialization helpers for numpy types."""
from __future__ import annotations

import json as _json_module
from typing import cast

import numpy as np


class _NumpyEncoder(_json_module.JSONEncoder):
    """Serialize numpy scalars and arrays to native Python types."""
    def default(self, o: object) -> object:
        if isinstance(o, np.integer):
            return int(cast(int, o))
        if isinstance(o, np.floating):
            return float(cast(float, o))
        if isinstance(o, np.bool_):
            return bool(cast(bool, o))
        if isinstance(o, np.ndarray):
            return o.tolist()
        return super().default(o)


NumpyEncoder = _NumpyEncoder


def _dumps(obj: object) -> str:
    return _json_module.dumps(obj, cls=_NumpyEncoder)
