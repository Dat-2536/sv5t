# Đổi tên file minh chứng

Quét `input/`, đọc file theo mẫu `<tên khoa>-<mssv>-<họ tên>.<đuôi>` trong từng thư mục loại, rồi copy sang `output/` với tên:

`<mssv>_<tên thư mục>_<họ tên>.<đuôi>`

Thư mục con trong `output/` trùng tên thư mục trong `input/`.

| Nguồn | Đích |
|-------|------|
| `input/Giải thưởng/KHKTMT-2210001-Nguyễn Văn A.png` | `output/Giải thưởng/2210001_Giải thưởng_Nguyễn Văn A.png` |

Nhiều file cùng thư mục, MSSV và họ tên được đánh số vào tên thư mục: `2210001_Giải thưởng-2_Nguyễn Văn A.png`.

File không có MSSV là dãy số nằm giữa hai dấu `-` bị bỏ qua và ghi log. Mặc định quét cả thư mục lồng nhau.

## Chạy

Bỏ file gốc vào `renamer/input/<loại>/`, rồi ở thư mục gốc repo:

```text
.\renamer.ps1 -DryRun
.\renamer.ps1
.\renamer.ps1 -Only "Giải thưởng","Ảnh thẻ" -Limit 10
.\renamer.ps1 -Move -CleanOutput
```

Tool chỉ dùng thư viện chuẩn của Python.

| Tham số | Python | Ý nghĩa |
|---------|--------|---------|
| `-InputDir` | `--input` | Nguồn, mặc định `renamer/input` |
| `-OutputDir` | `--output` | Đích, mặc định `renamer/output` |
| `-Only` | `--only` | Chỉ các thư mục loại khớp tên |
| `-Limit` | `--limit` | Chỉ N file đầu. `0` là tất cả |
| `-DryRun` | `--dry-run` | In tên đích, không ghi file |
| `-Move` | `--move` | Di chuyển thay vì copy |
| `-SkipExisting` | `--skip-existing` | Bỏ qua nếu file đích đã có |
| `-NoRecursive` | `--no-recursive` | Không quét thư mục con |
| `-CleanOutput` | `--clean-output` | Xóa `output` trước khi chạy |
| `-Quiet` | `--quiet` | Không in từng dòng |
| `-Log`, `-NoLog` | `--log`, `--no-log` | Đường dẫn log, hoặc tắt log |

Mặc định là copy và ghi đè file trùng tên ở đích.

## Kết quả

File đích nằm trong `renamer/output/`. Nhật ký `rename.log` ghi `ok`, `dry-run`, `skip`, `error`, `summary`.

Mã thoát: `0` thành công, `1` có lỗi, `2` không có nguồn.
