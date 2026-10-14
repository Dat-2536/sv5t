# Gom minh chứng theo sinh viên

Đọc file đã đổi tên bởi [renamer](../renamer/README.md), mẫu `<mssv>_<loại>_<họ tên>.<đuôi>`, rồi copy vào:

```text
distribute-files/output/<mssv>_<họ tên>/<tên file giữ nguyên>
```

Ví dụ `renamer/output/Giải thưởng/2210001_Giải thưởng_Nguyễn Văn A.png` thành `distribute-files/output/2210001_Nguyễn Văn A/2210001_Giải thưởng_Nguyễn Văn A.png`.

Một sinh viên có nhiều loại minh chứng thì các file nằm chung một thư mục. File không bắt đầu bằng MSSV và không có họ tên ở đoạn cuối bị bỏ qua.

## Chạy

Sau khi renamer đã có output:

```text
.\distribute-files.ps1 -DryRun
.\distribute-files.ps1
.\distribute-files.ps1 -Only "Giải thưởng","Ảnh thẻ"
.\distribute-files.ps1 -Move -CleanOutput
.\distribute-files.ps1 -InputDir "D:\renamer\out" -OutputDir "D:\dist\out"
```

| Tham số | Python | Ý nghĩa |
|---------|--------|---------|
| `-InputDir` | `--input` | Nguồn, mặc định `renamer/output` |
| `-OutputDir` | `--output` | Đích, mặc định `distribute-files/output` |
| `-Only` | `--only` | Chỉ các thư mục loại khớp tên |
| `-Limit` | `--limit` | Chỉ N file đầu |
| `-DryRun` | `--dry-run` | Không ghi đĩa |
| `-Move` | `--move` | Di chuyển thay vì copy |
| `-SkipExisting` | `--skip-existing` | Bỏ qua file đích đã có |
| `-NoRecursive` | `--no-recursive` | Không quét thư mục con |
| `-CleanOutput` | `--clean-output` | Xóa đích trước khi chạy |
| `-Quiet` | `--quiet` | Không in từng dòng |
| `-Log`, `-NoLog` | `--log`, `--no-log` | File log |

Mặc định là copy và ghi đè file trùng tên. `data.xlsx` trong thư mục này không được tool đọc.

## Kết quả

Nhật ký `distribute.log` ghi `ok`, `dry-run`, `skip`, `error`, `summary`.

Mã thoát: `0` thành công, `1` có lỗi, `2` không có file hoặc thư mục nguồn không tồn tại.
