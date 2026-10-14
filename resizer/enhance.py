"""Làm nét / tăng độ phân giải ảnh bằng Real-ESRGAN (realesr-general-x4v3, ONNX, chạy CPU)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
MODEL_FILE = HERE / "models" / "realesr-general-x4v3.onnx"
MODEL_URL = "https://huggingface.co/CoderViking/realesr-general-x4v3-onnx/resolve/main/realesr-general-x4v3.onnx"
MODEL_SCALE = 4
TILE = 256
TILE_OVERLAP = 16


@dataclass(frozen=True)
class EnhanceConfig:
    enabled: bool = True
    scale: float = 2.0
    blend: float = 0.8
    max_side: int = 1200


def config_from_env(env: dict[str, str]) -> EnhanceConfig:
    enabled = env.get("ENHANCE", "1").lower() not in {"0", "false", "no", "off"}
    scale = min(4.0, max(1.0, float(env.get("ENHANCE_SCALE", "2"))))
    blend = min(1.0, max(0.0, float(env.get("ENHANCE_BLEND", "0.8"))))
    max_side = max(64, int(env.get("ENHANCE_MAX_SIDE", "1200")))
    return EnhanceConfig(enabled=enabled, scale=scale, blend=blend, max_side=max_side)


def model_available() -> bool:
    if not MODEL_FILE.exists():
        return False
    try:
        import onnxruntime  # noqa: F401
    except ImportError:
        return False
    return True


def maybe_enhance(img: Image.Image, cfg: EnhanceConfig) -> tuple[Image.Image, bool]:
    """Chỉ làm nét ảnh nhỏ (ảnh thẻ, ảnh chụp màn hình); ảnh đã đủ lớn giữ nguyên."""
    if not cfg.enabled or max(img.size) > cfg.max_side or not model_available():
        return img, False
    return enhance(img, cfg), True


_session = None


def _get_session():
    global _session
    if _session is None:
        if not MODEL_FILE.exists():
            raise FileNotFoundError(f"Thiếu model {MODEL_FILE.name}; tải tại {MODEL_URL} vào {MODEL_FILE.parent}")
        import onnxruntime as ort

        _session = ort.InferenceSession(str(MODEL_FILE), providers=["CPUExecutionProvider"])
    return _session


def _run(tile: np.ndarray) -> np.ndarray:
    session = _get_session()
    x = np.ascontiguousarray(tile.transpose(2, 0, 1)[None], dtype=np.float32) / 255.0
    y = session.run(None, {session.get_inputs()[0].name: x})[0][0]
    return np.clip(y.transpose(1, 2, 0) * 255.0, 0, 255)


def super_resolve(rgb: np.ndarray) -> np.ndarray:
    """Phóng ×4; chia ô để giới hạn bộ nhớ với ảnh lớn."""
    h, w = rgb.shape[:2]
    if h <= TILE and w <= TILE:
        return _run(rgb)
    out = np.zeros((h * MODEL_SCALE, w * MODEL_SCALE, 3), np.float32)
    for y0 in range(0, h, TILE):
        for x0 in range(0, w, TILE):
            ya, xa = max(0, y0 - TILE_OVERLAP), max(0, x0 - TILE_OVERLAP)
            yb, xb = min(h, y0 + TILE + TILE_OVERLAP), min(w, x0 + TILE + TILE_OVERLAP)
            result = _run(rgb[ya:yb, xa:xb])
            oy, ox = (y0 - ya) * MODEL_SCALE, (x0 - xa) * MODEL_SCALE
            th = (min(h, y0 + TILE) - y0) * MODEL_SCALE
            tw = (min(w, x0 + TILE) - x0) * MODEL_SCALE
            out[y0 * MODEL_SCALE : y0 * MODEL_SCALE + th, x0 * MODEL_SCALE : x0 * MODEL_SCALE + tw] = result[
                oy : oy + th, ox : ox + tw
            ]
    return out


def enhance(img: Image.Image, cfg: EnhanceConfig) -> Image.Image:
    rgb = np.array(img.convert("RGB"))
    h, w = rgb.shape[:2]
    target = (int(round(w * cfg.scale)), int(round(h * cfg.scale)))
    sharp = cv2.resize(super_resolve(rgb), target, interpolation=cv2.INTER_AREA)
    if cfg.blend < 1.0:
        # trộn một phần ảnh phóng thường để giữ kết cấu da tự nhiên, tránh vẻ "vẽ"
        plain = cv2.resize(rgb, target, interpolation=cv2.INTER_LANCZOS4).astype(np.float32)
        sharp = sharp * cfg.blend + plain * (1.0 - cfg.blend)
    return Image.fromarray(np.clip(sharp, 0, 255).astype(np.uint8))
