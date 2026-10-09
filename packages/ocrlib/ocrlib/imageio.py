"""Image input normalisation: everything inside ocrlib is a BGR uint8 ndarray."""
from __future__ import annotations

from pathlib import Path
from typing import Union

import cv2
import numpy as np

ImageLike = Union[np.ndarray, bytes, str, Path, "PIL.Image.Image"]  # noqa: F821


def load_image(src: ImageLike) -> np.ndarray:
    """Accept ndarray (gray/BGR/BGRA), encoded bytes, a path, or a PIL image -> BGR uint8."""
    if isinstance(src, np.ndarray):
        img = src
    elif isinstance(src, (bytes, bytearray)):
        img = cv2.imdecode(np.frombuffer(src, np.uint8), cv2.IMREAD_COLOR)
    elif isinstance(src, (str, Path)):
        img = cv2.imdecode(np.fromfile(str(src), np.uint8), cv2.IMREAD_COLOR)  # unicode-safe on Windows
    elif hasattr(src, "convert"):  # PIL
        img = cv2.cvtColor(np.asarray(src.convert("RGB")), cv2.COLOR_RGB2BGR)
    else:
        raise TypeError(f"unsupported image type: {type(src)!r}")
    if img is None or img.size == 0:
        raise ValueError("could not decode image")
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    elif img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
    if img.dtype != np.uint8:
        img = np.clip(img, 0, 255).astype(np.uint8)
    return img
