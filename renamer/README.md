# Đổi tên file hồ sơ sinh viên

## Mô tả

Tool quét `input/`, đọc file theo mẫu **`<tên khoa>-<mssv>-<họ tên sinh viên>.<extension>`** trong từng folder loại (vd. `Giải thưởng`, `Ảnh thẻ`), rồi copy hoặc di chuyển sang `output/` với tên mới:

**`<mssv>_<tên folder>_<họ tên sinh viên>.<extension>`**

Folder con trong `output/` trùng tên với folder tương ứng trong `input/`.

### Ví dụ

| Input | Output |
|-------|--------|
| `input/Giải thưởng/KHKTMT-2352410-Trần Minh Huy.png` | `output/Giải thưởng/2352410_Giải thưởng_Trần Minh Huy.png` |

Nếu nhiều file cùng `(folder, MSSV, họ tên)` → trùng tên đích:

| Lần | Tên file output |
|-----|-----------------|
| 1 | `2352410_Giải thưởng_Trần Minh Huy.png` |
| 2 | `2352410_Giải thưởng-2_Trần Minh Huy.png` |
| 3 | `2352410_Giải thưởng-3_Trần Minh Huy.png` |

Phần `-2`, `-3` gắn vào **tên folder** (giữa MSSV và họ tên), không đổi MSSV hay họ tên.

## Cấu trúc thư mục

```text
renamer/
  input/
    Giải thưởng/
      KHKTMT-2352410-Trần Minh Huy.png
    Ảnh thẻ/
      CS-2410712-Nguyễn Tiến Đạt.jpg
  output/          ← tạo tự động khi chạy
  rename.py
  rename.log       ← mặc định
```

Mặc định tool quét **mọi file** trong từng folder con (kể cả thư mục lồng nhau). Dùng `--no-recursive` nếu chỉ muốn file nằm trực tiếp trong folder loại.

File không khớp mẫu (MSSV phải là dãy số giữa hai dấu `-`) được **bỏ qua** và ghi vào log.

## Chạy tool

Ở **thư mục gốc repo**:

```text
.\renamer.ps1
```

Script dùng `.venv` chung của repo (tạo nếu chưa có). Tool chỉ dùng thư viện chuẩn Python, không cần cài thêm package.

Hoặc gọi trực tiếp:

```text
.\.venv\Scripts\python.exe renamer\rename.py
```

### Luồng làm việc gợi ý

1. Copy bộ file gốc vào `renamer\input\...`
2. Chạy thử: `.\renamer.ps1 -DryRun`
3. Chạy thật: `.\renamer.ps1`
4. Nếu muốn dọn output cũ trước lượt mới: `.\renamer.ps1 -CleanOutput`

## Tuỳ chọn (PowerShell)

```text
.\renamer.ps1 -DryRun
.\renamer.ps1 -Only "Giải thưởng","Ảnh thẻ"
.\renamer.ps1 -Limit 10
.\renamer.ps1 -SkipExisting
.\renamer.ps1 -Move
.\renamer.ps1 -NoRecursive
.\renamer.ps1 -CleanOutput
.\renamer.ps1 -Quiet
.\renamer.ps1 -InputDir "D:\data\in" -OutputDir "D:\data\out"
.\renamer.ps1 -Log "D:\logs\rename.log"
.\renamer.ps1 -NoLog
```

| Tham số | Python | Ý nghĩa |
|---------|--------|---------|
| `-InputDir` | `--input` | Thư mục nguồn (mặc định `renamer/input`) |
| `-OutputDir` | `--output` | Thư mục đích (mặc định `renamer/output`) |
| `-Only` | `--only` (lặp) | Chỉ xử lý các folder con có tên khớp |
| `-Limit N` | `--limit N` | Chỉ N file đầu (0 = hết) |
| `-DryRun` | `--dry-run` | Không ghi file, chỉ xem tên đích |
| `-Move` | `--move` | Di chuyển thay vì copy |
| `-SkipExisting` | `--skip-existing` | Bỏ qua nếu file đích đã có |
| `-NoRecursive` | `--no-recursive` | Không quét folder lồng nhau |
| `-CleanOutput` | `--clean-output` | Xóa sạch `output` trước khi chạy |
| `-Quiet` | `--quiet` | Không in từng dòng (vẫn có tổng kết + log) |
| `-Log` | `--log` | Đường dẫn file log |
| `-NoLog` | `--no-log` | Không ghi log |

Mặc định: **copy** (giữ nguyên `input`), **ghi đè** file trùng tên ở output (trừ khi bật `-SkipExisting`).

## Kết quả và log

- File đích: `renamer\output\<tên folder>\...`
- Log mặc định: `renamer\rename.log`

| Status | Ý nghĩa |
|--------|---------|
| `ok` | Copy/di chuyển thành công |
| `dry-run` | Mô phỏng (không ghi disk) |
| `skip` | Tên không khớp mẫu, hoặc đã có file (khi `-SkipExisting`) |
| `error` | Lỗi OS (quyền, đĩa đầy, …) |
| `summary` | Tổng kết cuối lượt chạy |

Mã thoát: `0` thành công; `1` có ít nhất một `error`; `2` không có input / thư mục nguồn không tồn tại.
