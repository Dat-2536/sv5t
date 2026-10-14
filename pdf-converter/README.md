# Chuyển ảnh minh chứng sang PDF

Web SV5T, trừ ảnh thẻ, nhận minh chứng dạng PDF. Tool đổi hàng loạt `.jpg`, `.jpeg`, `.jfif`, `.png`, `.webp`, `.bmp`, `.tif`, `.tiff`, `.gif` thành PDF cùng tên, cùng thư mục.

Mỗi PDF một trang, khổ bằng kích thước pixel của ảnh. Không ép A4 và không thêm viền trắng. Ảnh có xoay EXIF được chỉnh trước khi ghi.

## Chạy

Từ thư mục gốc repo, chỉ định folder ảnh:

```text
.\pdf-converter.ps1 -InputDir "distribute-files\output\2210001_Nguyễn Văn A"
.\pdf-converter.ps1 -InputDir "pdf-converter\cv" -DryRun
```

Hoặc đứng trong chính folder ảnh. Lúc đó tool quét thư mục hiện tại:

```text
cd distribute-files\output\2210001_Nguyễn Văn A
D:\duong\dan\sv5t\pdf-converter.ps1
```

Python:

```text
.\.venv\Scripts\python.exe pdf-converter\convert.py "pdf-converter\cv" --ext png --dry-run
```

Mặc định không quét thư mục con. Thêm `-Recursive` khi ảnh nằm trong folder lồng nhau.

## Tuỳ chọn hay dùng

| Tham số | Python | Ý nghĩa |
|---------|--------|---------|
| `-InputDir` | đối số vị trí | Folder ảnh. Script PowerShell mặc định là thư mục hiện tại |
| `-Ext` | `--ext` | Chỉ một số đuôi, lặp lại được: `-Ext png -Ext jpg` |
| `-Recursive` | `--recursive` | Quét cả thư mục con |
| `-DryRun` | `--dry-run` | Liệt kê, không tạo PDF |
| `-SkipExisting` | `--skip-existing` | Bỏ qua nếu PDF cùng tên đã có |
| `-DeleteSources` | `--delete-sources` | Xóa đúng ảnh vừa convert thành công |
| `-Quiet` | `--quiet` | Không in từng dòng |
| `-Log`, `-NoLog` | `--log`, `--no-log` | File log, mặc định `pdf-converter/convert.log` |

Chỉ PNG, tạo PDF rồi xóa PNG:

```text
.\pdf-converter.ps1 -InputDir "pdf-converter\cv" -Ext png -DryRun
.\pdf-converter.ps1 -InputDir "pdf-converter\cv" -Ext png -DeleteSources
```

`-SkipExisting` bỏ qua file đã có PDF nên không xóa ảnh tương ứng. Muốn dọn PNG sau khi chắc đã có PDF, xóa thủ công `*.png` trong folder đó.

## Kết quả

Nhật ký ghi `ok`, `dry-run`, `skip`, `deleted`, `error`, `summary`.

Mã thoát: `0` thành công, `1` có lỗi, `2` không có ảnh hoặc thư mục không tồn tại.

Trong luồng cả bộ tool, bước này thường đứng sau `distribute-files`. Nếu cần giảm dung lượng ảnh thì chạy `resizer` trước.
