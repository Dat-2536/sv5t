"""Chuẩn hoá dung lượng ảnh minh chứng theo MIN/MAX (MB) trong .env."""

from __future__ import annotations

import argparse
import io
import re
import struct
import sys
import zlib
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps

import enhance
from enhance import EnhanceConfig, maybe_enhance
from watermark import (
    GLYPH_FILE,
    WatermarkConfig,
    build_model,
    config_from_env,
    load_glyph,
    maybe_remove_watermark,
    save_model,
)

HERE = Path(__file__).resolve().parent
ENV_FILE = HERE / ".env"
DEFAULT_INPUT = HERE / "input"
DEFAULT_OUTPUT = HERE / "output"
LOG_FILE = HERE / "resize.log"

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


@dataclass
class SizeConfig:
    min_bytes: int
    max_bytes: int
    sharpen: bool
    allow_upscale: bool
    max_upscale_ratio: float
    jpeg_subsampling: int


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def parse_size_bytes(raw: str) -> int:
    text = raw.strip().upper().replace(" ", "")
    if not text:
        raise ValueError("Giá trị size rỗng")
    match = re.fullmatch(r"(\d+(?:\.\d+)?)(B|KB|MB|GB)?", text)
    if not match:
        raise ValueError(f"Không parse được size: {raw!r}")
    value = float(match.group(1))
    unit = match.group(2) or "MB"
    mult = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}[unit]
    size = int(value * mult)
    if size <= 0:
        raise ValueError("Size phải > 0")
    return size


def log_line(status: str, name: str, message: str, *, echo: bool = True) -> None:
    text = " ".join(str(message).split())
    stamp = datetime.now().isoformat(timespec="seconds")
    line = f"{stamp}\t{status}\t{name}\t{text}"
    if echo:
        print(line, flush=True)
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def load_config(env: dict[str, str]) -> SizeConfig:
    min_raw = env.get("MIN_SIZE_MB") or env.get("MIN_MB") or env.get("MIN") or "1MB"
    max_raw = env.get("MAX_SIZE_MB") or env.get("MAX_MB") or env.get("MAX") or "5MB"
    min_bytes = parse_size_bytes(min_raw)
    max_bytes = parse_size_bytes(max_raw)
    if min_bytes > max_bytes:
        raise ValueError("MIN phải <= MAX")

    sharpen = (env.get("SHARPEN", "1").lower() not in {"0", "false", "no", "off"})
    allow_upscale = env.get("ALLOW_UPSCALE", "1").lower() not in {"0", "false", "no", "off"}
    max_upscale_ratio = float(env.get("MAX_UPSCALE_RATIO", "1.15"))
    if max_upscale_ratio < 1.0:
        max_upscale_ratio = 1.0
    subsampling_raw = env.get("JPEG_SUBSAMPLING", "0")
    jpeg_subsampling = int(subsampling_raw)
    if jpeg_subsampling not in {0, 1, 2}:
        jpeg_subsampling = 0

    return SizeConfig(
        min_bytes=min_bytes,
        max_bytes=max_bytes,
        sharpen=sharpen,
        allow_upscale=allow_upscale,
        max_upscale_ratio=max_upscale_ratio,
        jpeg_subsampling=jpeg_subsampling,
    )


def open_image(path: Path) -> Image.Image:
    img = Image.open(path)
    img.load()
    if img.mode in {"RGBA", "LA"}:
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        return background
    if img.mode != "RGB":
        return ImageOps.exif_transpose(img).convert("RGB")
    return ImageOps.exif_transpose(img)


def sharpen_image(img: Image.Image) -> Image.Image:
    return img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=140, threshold=2))


def encode_jpeg(img: Image.Image, quality: int, cfg: SizeConfig) -> bytes:
    buf = io.BytesIO()
    img.save(
        buf,
        format="JPEG",
        quality=quality,
        optimize=False,
        progressive=True,
        subsampling=cfg.jpeg_subsampling,
    )
    return buf.getvalue()


def encode_png(img: Image.Image, compress_level: int = 6) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG", compress_level=compress_level, optimize=False)
    return buf.getvalue()


def pad_jpeg(data: bytes, target_size: int) -> bytes:
    if len(data) >= target_size:
        return data
    eoi = data.rfind(b"\xff\xd9")
    if eoi < 0:
        return data
    prefix = data[:eoi]
    suffix = data[eoi:]
    parts: list[bytes] = []
    remaining = target_size - len(data)
    while remaining > 0:
        payload = min(65533, remaining + 4)
        if payload < 2:
            break
        seg_len = payload + 2
        if seg_len > 65535:
            payload = 65533
            seg_len = payload + 2
        chunk = b"\xff\xfe" + struct.pack(">H", seg_len) + (b"\x00" * payload)
        parts.append(chunk)
        remaining -= len(chunk)
    return prefix + b"".join(parts) + suffix


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(chunk_type)
    crc = zlib.crc32(data, crc) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", crc)


def pad_png(data: bytes, target_size: int) -> bytes:
    if len(data) >= target_size:
        return data
    marker = b"IEND"
    idx = data.rfind(marker)
    if idx < 4:
        return data
    insert_at = idx - 4
    parts: list[bytes] = []
    remaining = target_size - len(data)
    seq = 0
    while remaining > 0:
        payload_len = min(65535, remaining + 12)
        text = b"pad" + bytes([seq % 256]) + b"\x00" + (b"x" * max(1, payload_len - 20))
        chunk = _png_chunk(b"tEXt", text)
        parts.append(chunk)
        remaining -= len(chunk)
        seq += 1
        if seq > 5000:
            break
    return data[:insert_at] + b"".join(parts) + data[insert_at:]


def compress_image(img: Image.Image, cfg: SizeConfig, prefer_jpeg: bool) -> tuple[bytes, str]:
    work = img
    if prefer_jpeg:
        lo, hi = 35, 95
        best = encode_jpeg(work, lo, cfg)
        if len(best) <= cfg.max_bytes:
            while lo < hi:
                mid = (lo + hi + 1) // 2
                candidate = encode_jpeg(work, mid, cfg)
                if len(candidate) <= cfg.max_bytes:
                    best = candidate
                    lo = mid
                else:
                    hi = mid - 1
            return best, ".jpg"

        scale = 0.92
        for _ in range(12):
            new_w = max(64, int(work.width * scale))
            new_h = max(64, int(work.height * scale))
            if new_w == work.width and new_h == work.height:
                break
            work = work.resize((new_w, new_h), Image.Resampling.LANCZOS)
            lo, hi = 35, 95
            best = encode_jpeg(work, lo, cfg)
            while lo < hi:
                mid = (lo + hi + 1) // 2
                candidate = encode_jpeg(work, mid, cfg)
                if len(candidate) <= cfg.max_bytes:
                    best = candidate
                    lo = mid
                else:
                    hi = mid - 1
            if len(best) <= cfg.max_bytes:
                return best, ".jpg"
            scale *= 0.9
        return best, ".jpg"

    lo, hi = 0, 9
    best = encode_png(work, compress_level=hi)
    while lo < hi:
        mid = (lo + hi) // 2
        candidate = encode_png(work, compress_level=mid)
        if len(candidate) <= cfg.max_bytes:
            best = candidate
            hi = mid
        else:
            lo = mid + 1
    if len(best) <= cfg.max_bytes:
        return best, ".png"

    scale = 0.92
    for _ in range(12):
        new_w = max(64, int(work.width * scale))
        new_h = max(64, int(work.height * scale))
        work = work.resize((new_w, new_h), Image.Resampling.LANCZOS)
        best = encode_png(work, compress_level=9)
        if len(best) <= cfg.max_bytes:
            return best, ".png"
        scale *= 0.9
    return best, ".png"


def expand_image(
    img: Image.Image,
    cfg: SizeConfig,
    prefer_jpeg: bool,
    *,
    skip_sharpen: bool = False,
) -> tuple[bytes, str]:
    work = img
    if cfg.sharpen and not skip_sharpen:
        work = sharpen_image(work)

    if prefer_jpeg:
        for quality in (98, 95, 92, 88):
            data = encode_jpeg(work, quality, cfg)
            if len(data) >= cfg.min_bytes:
                return data, ".jpg"

        if cfg.allow_upscale:
            ratio = 1.05
            cap_w = int(img.width * cfg.max_upscale_ratio)
            cap_h = int(img.height * cfg.max_upscale_ratio)
            while ratio <= cfg.max_upscale_ratio + 1e-9:
                w = min(int(img.width * ratio), cap_w)
                h = min(int(img.height * ratio), cap_h)
                if w <= work.width and h <= work.height:
                    ratio += 0.03
                    continue
                scaled = work.resize((w, h), Image.Resampling.LANCZOS)
                data = encode_jpeg(scaled, 98, cfg)
                if len(data) >= cfg.min_bytes:
                    return data, ".jpg"
                ratio += 0.03

        data = encode_jpeg(work, 100, cfg)
        data = pad_jpeg(data, cfg.min_bytes)
        return data, ".jpg"

    for level in (3, 1, 0):
        data = encode_png(work, compress_level=level)
        if len(data) >= cfg.min_bytes:
            return data, ".png"

    if cfg.allow_upscale:
        ratio = 1.05
        cap_w = int(img.width * cfg.max_upscale_ratio)
        cap_h = int(img.height * cfg.max_upscale_ratio)
        while ratio <= cfg.max_upscale_ratio + 1e-9:
            w = min(int(img.width * ratio), cap_w)
            h = min(int(img.height * ratio), cap_h)
            if w <= work.width and h <= work.height:
                ratio += 0.03
                continue
            scaled = work.resize((w, h), Image.Resampling.LANCZOS)
            data = encode_png(scaled, compress_level=1)
            if len(data) >= cfg.min_bytes:
                return data, ".png"
            ratio += 0.03

    data = encode_png(work, compress_level=0)
    data = pad_png(data, cfg.min_bytes)
    return data, ".png"


def output_path_for(src: Path, out_root: Path, input_root: Path, new_ext: str | None) -> Path:
    rel = src.relative_to(input_root)
    if new_ext:
        rel = rel.with_suffix(new_ext)
    return out_root / rel


def process_file(
    src: Path,
    dest: Path,
    cfg: SizeConfig,
    wm_cfg: WatermarkConfig,
    en_cfg: EnhanceConfig,
    *,
    dry_run: bool,
) -> str:
    size = src.stat().st_size
    img = open_image(src)
    img, wm_removed, wm_score = maybe_remove_watermark(img, wm_cfg)
    img, enhanced = maybe_enhance(img, en_cfg)
    changed = wm_removed or enhanced

    in_size_range = cfg.min_bytes <= size <= cfg.max_bytes
    if in_size_range and not changed:
        return "skip"

    prefer_jpeg = src.suffix.lower() in {".jpg", ".jpeg"} or size > cfg.max_bytes
    if wm_removed:
        prefer_jpeg = True

    retouch = "watermark" if wm_removed else "enhance"
    if size > cfg.max_bytes or (changed and in_size_range):
        data, ext = compress_image(img, cfg, prefer_jpeg=prefer_jpeg)
        action = "compress" if size > cfg.max_bytes else retouch
    elif not in_size_range:
        data, ext = expand_image(img, cfg, prefer_jpeg=prefer_jpeg, skip_sharpen=changed)
        action = "expand"
    else:
        data, ext = encode_jpeg(img, 92, cfg), ".jpg"
        action = retouch

    if not (cfg.min_bytes <= len(data) <= cfg.max_bytes):
        if len(data) > cfg.max_bytes and prefer_jpeg:
            data, ext = compress_image(img, cfg, prefer_jpeg=True)
            action = "compress"
        elif len(data) < cfg.min_bytes:
            if ext == ".jpg":
                data = pad_jpeg(data, cfg.min_bytes)
            else:
                data = pad_png(data, cfg.min_bytes)

    final_dest = dest.with_suffix(ext) if ext else dest
    detail = f"{size} -> {len(data)} bytes -> {final_dest.name}"
    if enhanced:
        detail = f"enhanced {img.width}x{img.height}; {detail}"
    if wm_removed:
        detail = f"watermark hits={wm_score:.0f}; {detail}"
    if dry_run:
        log_line(action, src.name, f"dry-run {detail}")
        return action

    final_dest.parent.mkdir(parents=True, exist_ok=True)
    final_dest.write_bytes(data)
    log_line(action, src.name, detail)
    return action


def collect_images(root: Path, *, recursive: bool) -> list[Path]:
    if not root.is_dir():
        return []
    if recursive:
        files = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES]
    else:
        files = [p for p in root.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES]
    return sorted(files)


def run(
    input_dir: Path,
    output_dir: Path,
    *,
    limit: int,
    recursive: bool,
    dry_run: bool,
    skip_existing: bool,
    no_watermark: bool = False,
    no_enhance: bool = False,
) -> int:
    env = load_env(ENV_FILE)
    try:
        cfg = load_config(env)
    except ValueError as exc:
        print(f"Cấu hình .env không hợp lệ: {exc}", file=sys.stderr)
        return 2
    wm_cfg = config_from_env(env)
    if no_watermark:
        wm_cfg = replace(wm_cfg, enabled=False)
    elif wm_cfg.enabled and load_glyph() is None:
        print(
            f"Chưa có mẫu watermark ({GLYPH_FILE.name}); chạy --build-watermark-template trước.",
            file=sys.stderr,
        )
    en_cfg = enhance.config_from_env(env)
    if no_enhance:
        en_cfg = replace(en_cfg, enabled=False)
    elif en_cfg.enabled and not enhance.model_available():
        print(
            f"Không làm nét được: cần onnxruntime và model {enhance.MODEL_FILE} (tải tại {enhance.MODEL_URL}).",
            file=sys.stderr,
        )

    files = collect_images(input_dir, recursive=recursive)
    if limit > 0:
        files = files[:limit]
    if not files:
        print(f"Không có ảnh trong {input_dir}", file=sys.stderr)
        return 2

    ok = skip = fail = 0
    total = len(files)
    for index, src in enumerate(files, start=1):
        dest = output_path_for(src, output_dir, input_dir, None)
        if skip_existing and dest.exists() and dest.stat().st_size > 0:
            skip += 1
            log_line("skip", src.name, "đã có file đích")
            print(f"\r[{index}/{total}] skip {src.name}", end="", flush=True)
            continue
        try:
            action = process_file(src, dest, cfg, wm_cfg, en_cfg, dry_run=dry_run)
            if action == "skip":
                skip += 1
            else:
                ok += 1
            print(f"\r[{index}/{total}] {action:8} {src.name}", end="", flush=True)
        except Exception as exc:
            fail += 1
            log_line("error", src.name, str(exc))
            print(f"\r[{index}/{total}] fail     {src.name}: {exc}", end="", flush=True)

    print()
    summary = (
        f"MIN={cfg.min_bytes} MAX={cfg.max_bytes} bytes | "
        f"{ok} xử lý, {skip} bỏ qua, {fail} lỗi, tổng {total}"
    )
    print(summary)
    log_line("summary", "-", summary, echo=False)
    return 1 if fail else 0


def build_template_cmd(source: Path) -> int:
    files = collect_images(source, recursive=True)
    if len(files) < 20:
        print(f"Cần ít nhất 20 ảnh thẻ trong {source} (đang có {len(files)})", file=sys.stderr)
        return 2
    print(f"Dựng mẫu chữ + thư viện bố cục watermark từ {len(files)} ảnh...")
    glyph, layouts = build_model(files)
    save_model(glyph, layouts)
    count = len(np.unique(layouts[:, 0])) if len(layouts) else 0
    print(f"Đã lưu {GLYPH_FILE} ({count} bố cục, {len(layouts)} vị trí chữ)")
    return 0


def main() -> None:
    configure_stdout()
    parser = argparse.ArgumentParser(description="Chuẩn hoá dung lượng ảnh minh chứng theo MIN/MAX trong .env")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Thư mục ảnh nguồn")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Thư mục ảnh đích")
    parser.add_argument("--limit", type=int, default=0, help="Chỉ xử lý N file đầu (0 = tất cả)")
    parser.add_argument("--recursive", action="store_true", help="Quét cả thư mục con của input")
    parser.add_argument("--dry-run", action="store_true", help="Chỉ log, không ghi file")
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Bỏ qua nếu file đích đã tồn tại",
    )
    parser.add_argument(
        "--no-watermark",
        action="store_true",
        help="Tắt xoá watermark myBk",
    )
    parser.add_argument(
        "--no-enhance",
        action="store_true",
        help="Tắt làm nét bằng Real-ESRGAN",
    )
    parser.add_argument(
        "--build-watermark-template",
        type=Path,
        metavar="DIR",
        help="Dựng lại khuôn watermark từ thư mục ảnh thẻ myBk (càng nhiều ảnh càng chuẩn)",
    )
    args = parser.parse_args()
    if args.build_watermark_template:
        raise SystemExit(build_template_cmd(args.build_watermark_template.resolve()))
    raise SystemExit(
        run(
            args.input.resolve(),
            args.output.resolve(),
            limit=args.limit,
            recursive=args.recursive,
            dry_run=args.dry_run,
            skip_existing=args.skip_existing,
            no_watermark=args.no_watermark,
            no_enhance=args.no_enhance,
        )
    )


if __name__ == "__main__":
    main()
