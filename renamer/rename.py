"""Đổi tên và sao chép file sinh viên từ input/ sang output/ theo quy tắc MSSV + loại folder."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_INPUT = HERE / "input"
DEFAULT_OUTPUT = HERE / "output"
DEFAULT_LOG = HERE / "rename.log"

# <tên khoa>-<mssv>-<họ tên>.<ext>
FILE_PATTERN = re.compile(r"^(.+)-(\d+)-(.+)\.([^.]+)$", re.UNICODE)


@dataclass
class RunConfig:
    log_file: Path | None
    quiet: bool


def configure_stdout() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def log_line(cfg: RunConfig, status: str, src: str, detail: str, *, echo: bool = True) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts}\t{status}\t{src}\t{detail}\n"
    if cfg.log_file is not None:
        with cfg.log_file.open("a", encoding="utf-8") as f:
            f.write(line)
    if echo and not cfg.quiet:
        print(line.rstrip())


def parse_student_filename(name: str) -> tuple[str, str, str, str] | None:
    match = FILE_PATTERN.match(name)
    if not match:
        return None
    khoa, mssv, full_name, ext = match.groups()
    full_name = full_name.strip()
    if not full_name:
        return None
    return khoa, mssv, full_name, f".{ext}"


def output_basename(mssv: str, folder_name: str, full_name: str, ext: str, index: int) -> str:
    if index <= 1:
        middle = folder_name
    else:
        middle = f"{folder_name}-{index}"
    return f"{mssv}_{middle}_{full_name}{ext}"


def collect_files(
    input_root: Path,
    *,
    only_folders: set[str] | None,
    no_recursive: bool,
) -> list[tuple[Path, str]]:
    """Trả về (đường dẫn file, tên folder cha trực tiếp dưới input)."""
    items: list[tuple[Path, str]] = []
    if not input_root.is_dir():
        return items
    for category_dir in sorted(input_root.iterdir()):
        if not category_dir.is_dir():
            continue
        folder_name = category_dir.name
        if only_folders is not None and folder_name not in only_folders:
            continue
        if no_recursive:
            paths = sorted(p for p in category_dir.iterdir() if p.is_file())
        else:
            paths = sorted(p for p in category_dir.rglob("*") if p.is_file())
        for path in paths:
            items.append((path, folder_name))
    return items


def clean_output_dir(output_root: Path) -> None:
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)


def run(
    input_root: Path,
    output_root: Path,
    cfg: RunConfig,
    *,
    move: bool,
    dry_run: bool,
    skip_existing: bool,
    limit: int,
    only_folders: set[str] | None,
    no_recursive: bool,
    clean_output: bool,
) -> int:
    if clean_output and not dry_run:
        clean_output_dir(output_root)

    files = collect_files(input_root, only_folders=only_folders, no_recursive=no_recursive)
    if limit > 0:
        files = files[:limit]
    if not files:
        print(f"Không có file trong {input_root}", file=sys.stderr)
        return 2

    occurrence: defaultdict[tuple[str, str, str], int] = defaultdict(int)
    ok = skip = fail = 0

    for src, folder_name in files:
        parsed = parse_student_filename(src.name)
        if not parsed:
            skip += 1
            log_line(cfg, "skip", str(src.relative_to(input_root)), "tên file không khớp mẫu khoa-mssv-họ tên")
            continue

        _khoa, mssv, full_name, ext = parsed
        key = (folder_name, mssv, full_name)
        occurrence[key] += 1
        idx = occurrence[key]
        new_name = output_basename(mssv, folder_name, full_name, ext, idx)

        dest_dir = output_root / folder_name
        dest = dest_dir / new_name

        if skip_existing and dest.exists() and not dry_run:
            skip += 1
            log_line(cfg, "skip", str(src.relative_to(input_root)), f"đã có {dest.relative_to(output_root)}")
            continue

        try:
            if dry_run:
                log_line(cfg, "dry-run", str(src.relative_to(input_root)), str(dest.relative_to(output_root)))
                ok += 1
                continue

            dest_dir.mkdir(parents=True, exist_ok=True)
            if move:
                shutil.move(str(src), str(dest))
            else:
                shutil.copy2(src, dest)
            ok += 1
            log_line(cfg, "ok", str(src.relative_to(input_root)), str(dest.relative_to(output_root)))
        except OSError as exc:
            fail += 1
            log_line(cfg, "error", str(src.relative_to(input_root)), str(exc))

    summary = f"Xong: {ok} ok, {fail} lỗi, {skip} bỏ qua, tổng {len(files)} file"
    print(summary)
    log_line(cfg, "summary", "-", summary, echo=False)
    return 1 if fail else 0


def main() -> None:
    configure_stdout()
    parser = argparse.ArgumentParser(
        description=(
            "Đổi tên file dạng <khoa>-<mssv>-<họ tên>.<ext> thành "
            "<mssv>_<tên folder>_<họ tên>.<ext> trong output/"
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Thư mục nguồn (mặc định: renamer/{DEFAULT_INPUT.name}/)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Thư mục đích (mặc định: renamer/{DEFAULT_OUTPUT.name}/)",
    )
    parser.add_argument(
        "--only",
        action="append",
        metavar="FOLDER",
        help="Chỉ xử lý folder con có tên FOLDER (lặp lại được, vd. --only \"Giải thưởng\" --only \"Ảnh thẻ\")",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Chỉ xử lý N file đầu sau khi lọc (0 = tất cả, tiện thử nhanh)",
    )
    parser.add_argument(
        "--move",
        action="store_true",
        help="Di chuyển file thay vì copy (mặc định: copy, giữ nguyên input)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chỉ in/log tên đích, không ghi file",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Bỏ qua nếu file đích đã tồn tại (mặc định: ghi đè)",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Chỉ lấy file ngay trong từng folder con, không quét thư mục lồng nhau",
    )
    parser.add_argument(
        "--clean-output",
        action="store_true",
        help="Xóa toàn bộ thư mục output trước khi chạy (không áp dụng khi --dry-run)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Không in từng dòng ra console (vẫn ghi log và in dòng tổng kết)",
    )
    parser.add_argument(
        "--no-log",
        action="store_true",
        help="Không ghi file log",
    )
    parser.add_argument(
        "--log",
        type=Path,
        default=None,
        help=f"Đường dẫn log (mặc định: renamer/{DEFAULT_LOG.name})",
    )
    args = parser.parse_args()
    input_root = args.input.resolve()
    output_root = args.output.resolve()

    if not input_root.is_dir():
        print(f"Không tìm thấy thư mục input: {input_root}", file=sys.stderr)
        raise SystemExit(2)

    only_folders: set[str] | None = None
    if args.only:
        only_folders = set(args.only)

    log_path: Path | None = None
    if not args.no_log:
        log_path = (args.log or DEFAULT_LOG).resolve()

    cfg = RunConfig(log_file=log_path, quiet=args.quiet)

    raise SystemExit(
        run(
            input_root,
            output_root,
            cfg,
            move=args.move,
            dry_run=args.dry_run,
            skip_existing=args.skip_existing,
            limit=max(0, args.limit),
            only_folders=only_folders,
            no_recursive=args.no_recursive,
            clean_output=args.clean_output,
        )
    )


if __name__ == "__main__":
    main()
