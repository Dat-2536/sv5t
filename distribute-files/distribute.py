"""Phân phối file đã đổi tên (renamer/output) vào folder từng sinh viên: <mssv>_<họ tên>/."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
DEFAULT_INPUT = REPO_ROOT / "renamer" / "output"
DEFAULT_OUTPUT = HERE / "output"
DEFAULT_LOG = HERE / "distribute.log"

MSSV_RE = re.compile(r"^\d+$")


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


def parse_renamed_basename(name: str) -> tuple[str, str, str] | None:
    """Đọc tên file dạng <mssv>_<loại>_<họ tên>.<ext> (output của renamer)."""
    path = Path(name)
    stem = path.stem
    ext = path.suffix
    if not stem or not ext:
        return None
    parts = stem.split("_")
    if len(parts) < 3:
        return None
    mssv, full_name = parts[0], parts[-1].strip()
    if not MSSV_RE.match(mssv) or not full_name:
        return None
    return mssv, full_name, ext


def student_dir_name(mssv: str, full_name: str) -> str:
    return f"{mssv}_{full_name}"


def collect_files(
    input_root: Path,
    *,
    only_folders: set[str] | None,
    no_recursive: bool,
) -> list[tuple[Path, str]]:
    """Trả về (đường dẫn file, tên folder loại trực tiếp dưới input)."""
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

    ok = skip = fail = 0

    for src, _folder_name in files:
        rel_src = str(src.relative_to(input_root))
        parsed = parse_renamed_basename(src.name)
        if not parsed:
            skip += 1
            log_line(
                cfg,
                "skip",
                rel_src,
                "tên file không khớp mẫu mssv_<loại>_<họ tên>",
            )
            continue

        mssv, full_name, _ext = parsed
        dest_dir = output_root / student_dir_name(mssv, full_name)
        dest = dest_dir / src.name

        if skip_existing and dest.exists() and not dry_run:
            skip += 1
            log_line(cfg, "skip", rel_src, f"đã có {dest.relative_to(output_root)}")
            continue

        try:
            if dry_run:
                log_line(cfg, "dry-run", rel_src, str(dest.relative_to(output_root)))
                ok += 1
                continue

            dest_dir.mkdir(parents=True, exist_ok=True)
            if move:
                shutil.move(str(src), str(dest))
            else:
                shutil.copy2(src, dest)
            ok += 1
            log_line(cfg, "ok", rel_src, str(dest.relative_to(output_root)))
        except OSError as exc:
            fail += 1
            log_line(cfg, "error", rel_src, str(exc))

    summary = f"Xong: {ok} ok, {fail} lỗi, {skip} bỏ qua, tổng {len(files)} file"
    print(summary)
    log_line(cfg, "summary", "-", summary, echo=False)
    return 1 if fail else 0


def main() -> None:
    configure_stdout()
    parser = argparse.ArgumentParser(
        description=(
            "Phân phối file từ renamer/output (mẫu <mssv>_<loại>_<họ tên>.<ext>) "
            "vào distribute-files/output/<mssv>_<họ tên>/"
        )
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Thư mục nguồn (mặc định: renamer/output)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Thư mục đích (mặc định: distribute-files/output)",
    )
    parser.add_argument(
        "--only",
        action="append",
        metavar="FOLDER",
        help='Chỉ xử lý folder loại FOLDER (vd. --only "Giải thưởng")',
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Chỉ xử lý N file đầu (0 = tất cả)",
    )
    parser.add_argument(
        "--move",
        action="store_true",
        help="Di chuyển file thay vì copy (mặc định: copy)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chỉ in/log đích, không ghi file",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Bỏ qua nếu file đích đã tồn tại",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Chỉ lấy file ngay trong từng folder loại",
    )
    parser.add_argument(
        "--clean-output",
        action="store_true",
        help="Xóa toàn bộ output trước khi chạy (không áp dụng khi --dry-run)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Không in từng dòng (vẫn tổng kết + log)",
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
        help="Đường dẫn log (mặc định: distribute-files/distribute.log)",
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
