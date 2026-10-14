"""Chuyển ảnh (png, jpg, webp, …) sang PDF — giữ nguyên kích thước pixel, không pad A4."""

from __future__ import annotations

import argparse
import io
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pymupdf
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
DEFAULT_LOG = HERE / "convert.log"

IMAGE_SUFFIXES = frozenset(
    {".jpg", ".jpeg", ".jfif", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif"}
)


@dataclass
class RunConfig:
    log_file: Path | None
    quiet: bool


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def log_line(cfg: RunConfig, status: str, name: str, detail: str, *, echo: bool = True) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts}\t{status}\t{name}\t{detail}\n"
    if cfg.log_file is not None:
        with cfg.log_file.open("a", encoding="utf-8") as handle:
            handle.write(line)
    if echo and not cfg.quiet:
        print(line.rstrip())


def normalize_extensions(raw: list[str] | None) -> frozenset[str] | None:
    if not raw:
        return None
    out: set[str] = set()
    for item in raw:
        text = item.strip().lower()
        if not text:
            continue
        if not text.startswith("."):
            text = f".{text}"
        out.add(text)
    return frozenset(out) if out else None


def collect_images(
    root: Path,
    *,
    allowed: frozenset[str] | None,
    recursive: bool,
) -> list[Path]:
    suffixes = allowed if allowed is not None else IMAGE_SUFFIXES
    if not root.is_dir():
        return []
    if recursive:
        paths = [p for p in root.rglob("*") if p.is_file()]
    else:
        paths = [p for p in root.iterdir() if p.is_file()]
    items = [p for p in paths if p.suffix.lower() in suffixes]
    return sorted(items, key=lambda p: str(p).lower())


def pil_prepare(path: Path) -> tuple[Image.Image, bool]:
    """Mở ảnh, chỉnh EXIF; trả về (image, cần_xuất_lại_stream)."""
    with Image.open(path) as im:
        im.load()
        transposed = ImageOps.exif_transpose(im)
        needs_reencode = transposed is not im
        if transposed.mode in ("RGBA", "LA", "P"):
            needs_reencode = True
        return transposed.copy(), needs_reencode


def image_bytes_for_pdf(im: Image.Image, src_suffix: str) -> tuple[bytes, str]:
    """Xuất bytes + đuôi gợi ý cho insert_image."""
    buf = io.BytesIO()
    suffix = src_suffix.lower()
    if suffix in {".jpg", ".jpeg", ".jfif"} and im.mode in ("RGB", "L"):
        im.save(buf, format="JPEG", quality=95, optimize=True)
        return buf.getvalue(), "jpeg"
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGBA") if "A" in im.getbands() else im.convert("RGB")
    im.save(buf, format="PNG", optimize=True)
    return buf.getvalue(), "png"


def can_embed_lossless(path: Path) -> bool:
    suffix = path.suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".jfif", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif"}:
        return False
    try:
        with Image.open(path) as im:
            im.load()
            if ImageOps.exif_transpose(im) is not im:
                return False
            if im.mode in ("RGBA", "LA", "P") and suffix in {".jpg", ".jpeg", ".jfif"}:
                return False
    except OSError:
        return False
    return True


def convert_one(src: Path, dest: Path) -> tuple[int, int]:
    """Trả về (width, height) pixel của trang PDF."""
    if can_embed_lossless(src):
        with Image.open(src) as im:
            im.load()
            im = ImageOps.exif_transpose(im)
            width, height = im.size
        doc = pymupdf.open()
        try:
            page = doc.new_page(width=width, height=height)
            page.insert_image(page.rect, filename=str(src))
            dest.parent.mkdir(parents=True, exist_ok=True)
            doc.save(dest)
        finally:
            doc.close()
        return width, height

    im, _ = pil_prepare(src)
    width, height = im.size
    stream, _ = image_bytes_for_pdf(im, src.suffix)
    im.close()
    doc = pymupdf.open()
    try:
        page = doc.new_page(width=width, height=height)
        page.insert_image(page.rect, stream=stream)
        dest.parent.mkdir(parents=True, exist_ok=True)
        doc.save(dest)
    finally:
        doc.close()
    return width, height


def run(
    input_dir: Path,
    cfg: RunConfig,
    *,
    allowed: frozenset[str] | None,
    recursive: bool,
    dry_run: bool,
    skip_existing: bool,
    delete_sources: bool,
) -> int:
    images = collect_images(input_dir, allowed=allowed, recursive=recursive)
    if not images:
        log_line(cfg, "ERROR", str(input_dir), "Không có ảnh khớp đuôi trong thư mục")
        return 2

    ok = skip = err = 0
    for src in images:
        dest = src.with_suffix(".pdf")
        rel = src.name
        if skip_existing and dest.exists():
            log_line(cfg, "skip", rel, f"đã có {dest.name}")
            skip += 1
            continue
        if dry_run:
            log_line(cfg, "dry-run", rel, f"→ {dest.name}")
            ok += 1
            continue
        try:
            w, h = convert_one(src, dest)
            log_line(cfg, "ok", rel, f"→ {dest.name} ({w}×{h} pt, không pad A4)")
            ok += 1
            if delete_sources:
                src.unlink()
                log_line(cfg, "deleted", rel, "đã xóa file ảnh gốc")
        except Exception as exc:  # noqa: BLE001 — ghi log từng file
            log_line(cfg, "error", rel, str(exc))
            err += 1

    log_line(
        cfg,
        "summary",
        str(input_dir),
        f"ok={ok} skip={skip} error={err} dry_run={dry_run}",
    )
    if err:
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Chuyển ảnh trong folder sang PDF (giữ nguyên kích thước, không pad A4).",
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=".",
        help="Thư mục chứa ảnh (mặc định: thư mục hiện tại)",
    )
    parser.add_argument(
        "--ext",
        action="append",
        dest="extensions",
        metavar="EXT",
        help="Chỉ đuôi này (vd. png, jpg). Lặp lại hoặc bỏ trống = mọi đuôi hỗ trợ",
    )
    parser.add_argument("--recursive", action="store_true", help="Quét cả folder con")
    parser.add_argument("--dry-run", action="store_true", help="Chỉ liệt kê, không ghi PDF")
    parser.add_argument("--skip-existing", action="store_true", help="Bỏ qua nếu .pdf đã tồn tại")
    parser.add_argument(
        "--delete-sources",
        action="store_true",
        help="Xóa file ảnh gốc sau khi chuyển thành công (tương đương del *.jpg …)",
    )
    parser.add_argument("--quiet", action="store_true", help="Không in từng dòng ra console")
    parser.add_argument("--log", type=Path, default=DEFAULT_LOG, help="File log")
    parser.add_argument("--no-log", action="store_true", help="Không ghi log file")
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_stdout()
    args = build_parser().parse_args(argv)
    input_dir = Path(args.input).resolve()
    if not input_dir.is_dir():
        print(f"Thư mục không tồn tại: {input_dir}", file=sys.stderr)
        return 2

    cfg = RunConfig(
        log_file=None if args.no_log else args.log,
        quiet=args.quiet,
    )
    allowed = normalize_extensions(args.extensions)
    return run(
        input_dir,
        cfg,
        allowed=allowed,
        recursive=args.recursive,
        dry_run=args.dry_run,
        skip_existing=args.skip_existing,
        delete_sources=args.delete_sources,
    )


if __name__ == "__main__":
    raise SystemExit(main())
