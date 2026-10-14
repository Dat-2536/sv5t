# Phân phối minh chứng theo sinh viên

## Mô tả

Tool quét thư mục output của **renamer** (mặc định `renamer/output/`), đọc file đã đổi tên theo mẫu **`<mssv>_<loại>_<họ tên sinh viên>.<extension>`**, rồi copy hoặc di chuyển vào folder từng người:

```text
distribute-files/output/<mssv>_<họ tên sinh viên>/<tên file giữ nguyên>
```

### Ví dụ

| Nguồn (renamer) | Đích (distribute-files) |
|-----------------|-------------------------|
| `renamer/output/Giải thưởng/2352410_Giải thưởng_Trần Minh Huy.png` | `distribute-files/output/2352410_Trần Minh Huy/2352410_Giải thưởng_Trần Minh Huy.png` |

Một sinh viên có thể có nhiều file (nhiều loại minh chứng) trong cùng folder `<mssv>_<họ tên>/`.

File không khớp mẫu tên (MSSV phải là dãy số ở đầu, họ tên ở segment cuối trước phần mở rộng) được **bỏ qua** và ghi log.

## Cấu trúc thư mục

```text
distribute-files/
  data.xlsx          ← danh sách SV (không bắt buộc cho tool)
  output/            ← tạo khi chạy
  distribute.py
  distribute.log
renamer/
  output/
    Giải thưởng/
      2352410_Giải thưởng_Trần Minh Huy.png
```

Mặc định quét **mọi file** trong từng folder loại (kể cả thư mục lồng nhau). Dùng `--no-recursive` nếu chỉ muốn file nằm trực tiếp trong folder loại.

## Chạy tool

Ở **thư mục gốc repo**:

```text
.\distribute-files.ps1
```

Hoặc:

```text
.\.venv\Scripts\python.exe distribute-files\distribute.py
```

### Luồng gợi ý

1. Chạy renamer: `.\renamer.ps1`
2. Thử phân phối: `.\distribute-files.ps1 -DryRun`
3. Chạy thật: `.\distribute-files.ps1`
4. Dọn output cũ: `.\distribute-files.ps1 -CleanOutput`
5. Nếu muốn dọn luôn bản trong renamer sau khi copy: thêm `-Move`

## Tuỳ chọn (PowerShell)

```text
.\distribute-files.ps1 -DryRun
.\distribute-files.ps1 -Only "Giải thưởng","Ảnh thẻ"
.\distribute-files.ps1 -Limit 10
.\distribute-files.ps1 -SkipExisting
.\distribute-files.ps1 -Move
.\distribute-files.ps1 -NoRecursive
.\distribute-files.ps1 -CleanOutput
.\distribute-files.ps1 -Quiet
.\distribute-files.ps1 -InputDir "D:\renamer\out" -OutputDir "D:\dist\out"
.\distribute-files.ps1 -Log "D:\logs\distribute.log"
.\distribute-files.ps1 -NoLog
```

| Tham số | Python | Ý nghĩa |
|---------|--------|---------|
| `-InputDir` | `--input` | Nguồn (mặc định `renamer/output`) |
| `-OutputDir` | `--output` | Đích (mặc định `distribute-files/output`) |
| `-Only` | `--only` | Chỉ các folder loại khớp tên |
| `-Limit N` | `--limit N` | Chỉ N file đầu |
| `-DryRun` | `--dry-run` | Không ghi disk |
| `-Move` | `--move` | Di chuyển thay vì copy |
| `-SkipExisting` | `--skip-existing` | Bỏ qua file đích đã có |
| `-NoRecursive` | `--no-recursive` | Không quét folder lồng nhau |
| `-CleanOutput` | `--clean-output` | Xóa sạch output trước khi chạy |
| `-Quiet` | `--quiet` | Không in từng dòng |
| `-Log` / `-NoLog` | `--log` / `--no-log` | File log |

Mặc định: **copy** (giữ nguyên `renamer/output`), **ghi đè** file trùng tên ở đích.

## Log

Mặc định: `distribute-files/distribute.log`

| Status | Ý nghĩa |
|--------|---------|
| `ok` | Copy/di chuyển thành công |
| `dry-run` | Mô phỏng |
| `skip` | Tên không khớp hoặc đã có file (khi `-SkipExisting`) |
| `error` | Lỗi OS |
| `summary` | Tổng kết |

Mã thoát: `0` thành công; `1` có lỗi; `2` không có file / thư mục nguồn không tồn tại.
