"""Nhận diện và xoá watermark ảnh thẻ myBk (chuỗi www.hcmut.edu.vn lặp chéo).

Mọi ảnh dùng cùng một mẫu chữ, chỉ khác cỡ chữ và vị trí (bố cục không phải
lưới đều). Với mỗi ảnh: dò từng chữ bằng template matching nhiều tỉ lệ, vẽ lại
độ tối watermark tại các chữ đó, rồi lấp nét chữ bằng nền cục bộ của chính ảnh.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
GLYPH_FILE = HERE / "mybk_watermark.npz"
CANONICAL_SIZE = (400, 600)
GLYPH_SIZE_RANGE = (0.07, 0.28)
MATCH_THRESHOLD = 0.45
WEAK_THRESHOLD = 0.2
MIN_HITS = 8
CONFIDENT_SCORE = 0.5
LAYOUT_TOLERANCE = 0.02


@dataclass(frozen=True)
class WatermarkConfig:
    enabled: bool = True
    min_hits: int = MIN_HITS
    strength: float = 1.3
    passes: int = 4


@dataclass(frozen=True)
class Instance:
    x: int
    y: int
    size: int
    score: float


def config_from_env(env: dict[str, str]) -> WatermarkConfig:
    enabled = env.get("REMOVE_WATERMARK", "1").lower() not in {"0", "false", "no", "off"}
    min_hits = int(env.get("WATERMARK_MIN_HITS", str(MIN_HITS)))
    strength = max(0.5, float(env.get("WATERMARK_STRENGTH", "1.3")))
    passes = max(1, int(env.get("WATERMARK_PASSES", "4")))
    return WatermarkConfig(enabled=enabled, min_hits=min_hits, strength=strength, passes=passes)


def _ellipse(size: int) -> np.ndarray:
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (size, size))


def _log_tophat(gray: np.ndarray) -> np.ndarray:
    """Độ tối của nét mảnh so với nền cục bộ, miền log (watermark làm tối dạng nhân)."""
    lg = np.log(np.clip(gray, 0, 255) + 1.0)
    return (lg - cv2.morphologyEx(lg, cv2.MORPH_CLOSE, _ellipse(5))).astype(np.float32)


def _strokes(rgb: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float32)
    return np.clip(-_log_tophat(gray), 0, 0.2)


# ---------- dựng mẫu chữ ----------


def _median_template(paths: list[Path]) -> np.ndarray:
    stack = []
    for path in paths:
        gray = np.array(Image.open(path).convert("L")).astype(np.float32)
        gray = cv2.resize(gray, CANONICAL_SIZE, interpolation=cv2.INTER_CUBIC)
        stack.append(_log_tophat(gray))
    return np.clip(-np.median(np.stack(stack), axis=0), 0, None).astype(np.float32)


def _extract_glyph(strokes: np.ndarray) -> np.ndarray:
    h, w = strokes.shape
    blob = cv2.dilate((strokes > 0.012).astype(np.uint8), np.ones((9, 9), np.uint8))
    count, _, stats, _ = cv2.connectedComponentsWithStats(blob, 8)
    boxes = [
        stats[i, :4]
        for i in range(1, count)
        if stats[i, 0] > 2 and stats[i, 1] > 2 and stats[i, 0] + stats[i, 2] < w - 2 and stats[i, 1] + stats[i, 3] < h - 2
    ]
    if len(boxes) < 5:
        raise RuntimeError("Không tách được mẫu chữ watermark (quá ít ảnh cùng bố cục?)")
    bw = float(np.median([b[2] for b in boxes]))
    bh = float(np.median([b[3] for b in boxes]))
    side = int(max(bw, bh)) + 12
    crops = []
    for x, y, bx, by in boxes:
        if abs(bx - bw) > 4 or abs(by - bh) > 4:
            continue
        x0 = int(round(x + bx / 2 - side / 2))
        y0 = int(round(y + by / 2 - side / 2))
        if x0 >= 0 and y0 >= 0 and x0 + side <= w and y0 + side <= h:
            crops.append(strokes[y0 : y0 + side, x0 : x0 + side])
    ref = crops[0]
    for _ in range(2):
        aligned = []
        for crop in crops:
            (dx, dy), _ = cv2.phaseCorrelate(ref, crop)
            shift = np.float32([[1, 0, -dx], [0, 1, -dy]])
            aligned.append(cv2.warpAffine(crop, shift, (side, side), flags=cv2.INTER_LINEAR))
        ref = np.median(np.stack(aligned), axis=0).astype(np.float32)
    return ref


def build_glyph(paths: list[Path]) -> np.ndarray:
    return _extract_glyph(_median_template(paths))


def build_model(paths: list[Path]) -> tuple[np.ndarray, np.ndarray]:
    glyph = build_glyph(paths)
    return glyph, build_layouts(paths, glyph)


def _normalized_points(instances: list[Instance], w: int, min_score: float) -> np.ndarray:
    """(tâm x, tâm y, cỡ chữ) chia cho chiều rộng ảnh."""
    rows = [
        ((i.x + i.size / 2) / w, (i.y + i.size / 2) / w, i.size / w)
        for i in instances
        if i.score >= min_score
    ]
    return np.array(rows, dtype=np.float64).reshape(-1, 3)


def _match_fraction(points: np.ndarray, layout: np.ndarray) -> float:
    if len(points) == 0 or len(layout) == 0:
        return 0.0
    dist = np.linalg.norm(points[:, None, :2] - layout[None, :, :2], axis=2)
    return float((dist.min(axis=1) < LAYOUT_TOLERANCE).mean())


def build_layouts(paths: list[Path], glyph: np.ndarray) -> np.ndarray:
    """Gộp vị trí chữ của các ảnh cùng bố cục: chữ bị mặt che ở ảnh này thường lộ ra ở ảnh khác.

    Trả về mảng N×5: (mã bố cục, tâm x/w, tâm y/w, cỡ/w, h/w).
    """
    samples = []
    for path in paths:
        rgb = np.array(Image.open(path).convert("RGB")).astype(np.float32)
        h, w = rgb.shape[:2]
        instances = find_instances(rgb, glyph)
        samples.append((h / w, _normalized_points(instances, w, CONFIDENT_SCORE)))

    groups: list[list[int]] = []
    for index, (aspect, points) in enumerate(samples):
        if len(points) < MIN_HITS:
            continue
        for group in groups:
            ref_aspect, ref_points = samples[group[0]]
            if (
                abs(aspect - ref_aspect) < 0.01
                and _match_fraction(points, ref_points) >= 0.6
                and _match_fraction(ref_points, points) >= 0.6
            ):
                group.append(index)
                break
        else:
            groups.append([index])

    rows = []
    for layout_id, group in enumerate(g for g in groups if len(g) >= 2):
        merged: list[list[np.ndarray]] = []
        for index in group:
            for point in samples[index][1]:
                for bucket in merged:
                    if np.linalg.norm(bucket[0][:2] - point[:2]) < LAYOUT_TOLERANCE:
                        bucket.append(point)
                        break
                else:
                    merged.append([point])
        aspect = float(np.median([samples[i][0] for i in group]))
        for bucket in merged:
            cx, cy, size = np.median(np.stack(bucket), axis=0)
            rows.append((layout_id, cx, cy, size, aspect))
    return np.array(rows, dtype=np.float64).reshape(-1, 5)


def save_model(glyph: np.ndarray, layouts: np.ndarray, path: Path = GLYPH_FILE) -> None:
    np.savez_compressed(path, glyph=glyph, layouts=layouts)


_model_cache: tuple[np.ndarray, np.ndarray] | None = None


def load_model() -> tuple[np.ndarray, np.ndarray] | None:
    global _model_cache
    if _model_cache is None and GLYPH_FILE.exists():
        data = np.load(GLYPH_FILE)
        if "glyph" in data:
            layouts = data["layouts"] if "layouts" in data else np.zeros((0, 5))
            _model_cache = (data["glyph"].astype(np.float32), layouts)
    return _model_cache


def load_glyph() -> np.ndarray | None:
    model = load_model()
    return model[0] if model else None


# ---------- dò chữ ----------


def _peaks(resp: np.ndarray, thr: float, min_dist: int) -> list[tuple[float, int, int]]:
    local_max = cv2.dilate(resp, _ellipse(max(3, min_dist)))
    ys, xs = np.where((resp == local_max) & (resp > thr))
    return sorted(zip(resp[ys, xs].tolist(), xs.tolist(), ys.tolist()), reverse=True)


def _match(strokes: np.ndarray, glyph: np.ndarray, size: int) -> np.ndarray:
    kernel = cv2.resize(glyph, (size, size), interpolation=cv2.INTER_AREA)
    padded = cv2.copyMakeBorder(strokes, size, size, size, size, cv2.BORDER_CONSTANT, value=0)
    return cv2.matchTemplate(padded, kernel, cv2.TM_CCOEFF_NORMED)


def _size_score(strokes: np.ndarray, glyph: np.ndarray, size: int) -> float:
    top = _peaks(_match(strokes, glyph, size), 0.0, size // 2)[:12]
    return float(np.mean([v for v, _, _ in top])) if top else -1.0


def _best_size(strokes: np.ndarray, glyph: np.ndarray) -> int:
    w = strokes.shape[1]
    lo = max(8, int(w * GLYPH_SIZE_RANGE[0]))
    hi = int(w * GLYPH_SIZE_RANGE[1])
    coarse = max(range(lo, hi + 1, 3), key=lambda s: _size_score(strokes, glyph, s))
    fine = range(max(lo, coarse - 2), min(hi, coarse + 2) + 1)
    return max(fine, key=lambda s: _size_score(strokes, glyph, s))


def find_instances(rgb: np.ndarray, glyph: np.ndarray, base: int | None = None) -> list[Instance]:
    h, w = rgb.shape[:2]
    if not 0.6 <= w / h <= 0.8:
        return []
    strokes = _strokes(rgb)
    if base is None:
        base = _best_size(strokes, glyph)
    responses = {s: _match(strokes, glyph, s) for s in range(max(8, base - 2), base + 3)}
    instances = []
    for score, x, y in _peaks(responses[base], MATCH_THRESHOLD, base // 2):
        # tinh chỉnh cỡ chữ và vị trí riêng cho từng chữ
        best = (score, base, x, y)
        for size, resp in responses.items():
            x0, y0 = max(0, x - 4), max(0, y - 4)
            window = resp[y0 : y + 5, x0 : x + 5]
            if window.size == 0:
                continue
            dy, dx = np.unravel_index(int(np.argmax(window)), window.shape)
            if window[dy, dx] > best[0]:
                best = (float(window[dy, dx]), size, x0 + dx, y0 + dy)
        score, size, bx, by = best
        instances.append(Instance(x=bx - size, y=by - size, size=size, score=score))
    return instances


def complete_from_layout(
    rgb: np.ndarray, instances: list[Instance], glyph: np.ndarray, layouts: np.ndarray
) -> list[Instance]:
    """Nếu ảnh khớp một bố cục đã biết, bổ sung các chữ bị bỏ sót (thường nằm trên mặt/áo)."""
    if len(layouts) == 0 or not instances:
        return instances
    h, w = rgb.shape[:2]
    points = _normalized_points(instances, w, CONFIDENT_SCORE)
    if len(points) < MIN_HITS:
        return instances
    best_id, best_fraction = None, 0.0
    for layout_id in np.unique(layouts[:, 0]):
        layout = layouts[layouts[:, 0] == layout_id]
        if abs(layout[0, 4] - h / w) > 0.01:
            continue
        fraction = _match_fraction(points, layout[:, 1:4])
        if fraction > best_fraction:
            best_id, best_fraction = layout_id, fraction
    if best_id is None or best_fraction < 0.7:
        return instances

    known = _normalized_points(instances, w, 0.0)
    strokes = _strokes(rgb)
    responses: dict[int, np.ndarray] = {}
    added = list(instances)
    for _, cx, cy, size_n, _ in layouts[layouts[:, 0] == best_id]:
        if len(known) and np.linalg.norm(known[:, :2] - (cx, cy), axis=1).min() < LAYOUT_TOLERANCE:
            continue
        size = int(round(size_n * w))
        x, y = int(round(cx * w - size / 2)), int(round(cy * w - size / 2))
        radius = max(3, int(round(size * 0.1)))
        best = (-1.0, size, x, y)
        for s in range(size - 1, size + 2):
            resp = responses.get(s)
            if resp is None:
                resp = responses[s] = _match(strokes, glyph, s)
            # toạ độ trong resp lệch +s do padding
            x0, y0 = max(0, x + s - radius), max(0, y + s - radius)
            window = resp[y0 : y + s + radius + 1, x0 : x + s + radius + 1]
            if window.size == 0:
                continue
            dy, dx = np.unravel_index(int(np.argmax(window)), window.shape)
            if window[dy, dx] > best[0]:
                best = (float(window[dy, dx]), s, x0 + dx - s, y0 + dy - s)
        score, s, bx, by = best
        added.append(Instance(x=int(bx), y=int(by), size=int(s), score=max(score, 0.0)))
    return added


# ---------- xoá ----------


def _text_direction_kernel(size: int) -> np.ndarray:
    length = max(3, int(round(size * 0.18)) | 1)
    return np.fliplr(np.eye(length, dtype=np.uint8))


def _darkness(y: np.ndarray) -> np.ndarray:
    log_y = np.log(y + 1.0)
    closed = cv2.morphologyEx(log_y, cv2.MORPH_CLOSE, _ellipse(7))
    # closing bám theo quầng sáng JPEG quanh chữ; lấy thêm trung vị để nền tham chiếu không sáng hơn nền thật
    median = np.log(cv2.medianBlur(np.clip(y, 0, 255).astype(np.uint8), 9).astype(np.float32) + 1.0)
    return np.maximum(np.minimum(closed, median) - log_y, 0)


def _luma(rgb: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(np.clip(rgb, 0, 255).astype(np.uint8), cv2.COLOR_RGB2YCrCb)[..., 0].astype(np.float32)


@dataclass
class _Footprint:
    window: tuple[slice, slice]
    region: np.ndarray
    core_vals: np.ndarray


def _footprint(inst: Instance, glyph: np.ndarray, darkness: np.ndarray) -> _Footprint | None:
    h, w = darkness.shape
    kernel = cv2.resize(glyph, (inst.size, inst.size), interpolation=cv2.INTER_AREA)
    peak = float(kernel.max()) + 1e-6
    pad = max(4, int(round(inst.size * 0.2)))
    kernel = cv2.copyMakeBorder(kernel, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
    reach = max(3, int(round(inst.size * 0.12)) | 1)
    region = cv2.dilate((kernel > 0.1 * peak).astype(np.uint8), _ellipse(reach))
    # vị trí dò có thể trượt dọc theo dòng chữ, nên nới vùng xoá theo hướng chữ
    region = cv2.dilate(region, _text_direction_kernel(inst.size)).astype(bool)
    core = kernel > 0.35 * peak
    bx, by, side = inst.x - pad, inst.y - pad, kernel.shape[0]
    x0, y0 = max(0, bx), max(0, by)
    x1, y1 = min(w, bx + side), min(h, by + side)
    if x1 <= x0 or y1 <= y0:
        return None
    ks = (slice(y0 - by, y1 - by), slice(x0 - bx, x1 - bx))
    window = (slice(y0, y1), slice(x0, x1))
    core_vals = darkness[window][core[ks]]
    if core_vals.size < 4:
        return None
    return _Footprint(window=window, region=region[ks], core_vals=core_vals)


def _instance_darkness(fp: _Footprint) -> float:
    # bỏ điểm quá tối (chi tiết thật như lông mày cắt qua chữ) khi đo độ đậm watermark
    vals = fp.core_vals[fp.core_vals <= 3 * np.median(fp.core_vals) + 1e-3]
    return float(np.percentile(vals, 85))


def typical_darkness(rgb: np.ndarray, instances: list[Instance], glyph: np.ndarray) -> float:
    darkness = _darkness(_luma(rgb))
    values = []
    for inst in instances:
        if inst.score < CONFIDENT_SCORE:
            continue
        fp = _footprint(inst, glyph, darkness)
        if fp is not None:
            values.append(_instance_darkness(fp))
    return float(np.median(values)) if values else 0.0


def find_weak_instances(
    rgb: np.ndarray, instances: list[Instance], glyph: np.ndarray, base: int, typical: float
) -> list[Instance]:
    """Chữ nằm trên vùng có chi tiết (mặt, tóc, áo) khớp mẫu kém; nhận thêm nếu độ đậm nét giống watermark thật."""
    if typical <= 0:
        return []
    strokes = _strokes(rgb)
    darkness = _darkness(_luma(rgb))
    kernel = cv2.resize(glyph, (base, base), interpolation=cv2.INTER_AREA)
    core = (kernel > 0.35 * kernel.max()).astype(np.float32)
    # coverage[y, x]: tỉ lệ điểm lõi của chữ đặt tại (x, y) rơi vào nét tối
    coverage = cv2.filter2D(
        (darkness >= 0.4 * typical).astype(np.float32), -1, core / core.sum(),
        anchor=(0, 0), borderType=cv2.BORDER_CONSTANT,
    )
    radius = max(3, int(round(base * 0.15)))
    h, w = darkness.shape
    known = np.array([(i.x + i.size / 2, i.y + i.size / 2) for i in instances]).reshape(-1, 2)
    added = []
    for score, x, y in _peaks(_match(strokes, glyph, base), WEAK_THRESHOLD, base // 2):
        if score >= MATCH_THRESHOLD:
            continue
        x, y = x - base, y - base
        x0, y0 = min(max(0, x - radius), w - 1), min(max(0, y - radius), h - 1)
        window = coverage[y0 : max(y0 + 1, y + radius + 1), x0 : max(x0 + 1, x + radius + 1)]
        dy, dx = np.unravel_index(int(np.argmax(window)), window.shape)
        inst = Instance(x=x0 + int(dx), y=y0 + int(dy), size=base, score=score)
        center = np.array([inst.x + base / 2, inst.y + base / 2])
        if len(known) and np.linalg.norm(known - center, axis=1).min() < base * 0.3:
            continue
        fp = _footprint(inst, glyph, darkness)
        if fp is None:
            continue
        covered = float((fp.core_vals >= 0.4 * typical).mean())
        level = float(np.median(fp.core_vals))
        if covered >= 0.45 and level <= 2.5 * typical:
            added.append(inst)
            known = np.vstack([known, center])
    return added


def remove_watermark(
    rgb: np.ndarray, instances: list[Instance], glyph: np.ndarray, strength: float, typical: float = 0.0
) -> np.ndarray:
    """Làm sáng lại nét chữ trên kênh sáng; mức làm sáng mỗi chữ không vượt độ đậm đo được của chính chữ đó."""
    h, w = rgb.shape[:2]
    ycc = cv2.cvtColor(np.clip(rgb, 0, 255).astype(np.uint8), cv2.COLOR_RGB2YCrCb).astype(np.float32)
    darkness = _darkness(ycc[..., 0])

    lift = np.zeros((h, w), np.float32)
    for inst in instances:
        fp = _footprint(inst, glyph, darkness)
        if fp is None:
            continue
        level = _instance_darkness(fp)
        if typical > 0:
            # watermark được in đều tay: không chữ nào được làm sáng quá mức đậm điển hình
            level = min(level, 1.5 * typical)
        cap = level * strength
        local = darkness[fp.window]
        patch = np.where(fp.region, np.minimum(local, cap), 0)
        np.maximum(lift[fp.window], patch, out=lift[fp.window])

    lift = cv2.GaussianBlur(lift, (0, 0), 0.5)
    ycc[..., 0] = np.clip((ycc[..., 0] + 1.0) * np.exp(lift) - 1.0, 0, 255)
    return cv2.cvtColor(ycc.astype(np.uint8), cv2.COLOR_YCrCb2RGB).astype(np.float32)


def maybe_remove_watermark(img: Image.Image, cfg: WatermarkConfig) -> tuple[Image.Image, bool, float]:
    """Trả về (ảnh, đã_xoá, số chữ watermark khớp chắc chắn)."""
    if not cfg.enabled:
        return img, False, 0.0
    model = load_model()
    if model is None:
        return img, False, 0.0
    glyph, layouts = model
    rgb = np.array(img.convert("RGB")).astype(np.float32)
    instances = find_instances(rgb, glyph)
    hits = sum(inst.score >= CONFIDENT_SCORE for inst in instances)
    if hits < cfg.min_hits:
        return img, False, float(hits)
    instances = complete_from_layout(rgb, instances, glyph, layouts)
    base = int(np.median([inst.size for inst in instances]))
    typical = typical_darkness(rgb, instances, glyph)
    instances = instances + find_weak_instances(rgb, instances, glyph, base, typical)
    count = len(instances)
    cleaned = rgb
    for index in range(cfg.passes):
        if index > 0:
            # lượt sau xử lý tiếp nét còn sót tại các chữ đã biết và chữ mới dò ra
            instances = instances + find_instances(cleaned, glyph, base)
        cleaned = remove_watermark(cleaned, instances, glyph, cfg.strength, typical)
    return Image.fromarray(cleaned.astype(np.uint8)), True, float(count)
