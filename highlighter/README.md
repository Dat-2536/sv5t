# Tô vàng dòng MSSV trên PDF scan

OCR PDF danh sách sinh viên, giữ dòng thuộc Khoa học và Kỹ thuật Máy tính, và chỉ xử lý MSSV có trong `data.xlsx`. Bản sao đã tô vàng cả hàng được ghi vào `highlighted/`.

Tên file:

```text
<mssv>_<tên thư mục loại>_<họ tên trong Excel>.pdf
```

Ví dụ: `2210001_TNTT_Nguyễn Văn A.pdf`. Họ tên lấy từ Excel, không lấy từ OCR.

## Chuẩn bị

```text
highlighter/
  data.xlsx          cột MSSV và Họ tên
  TNTT/
    danh-sach.pdf    một hoặc nhiều PDF scan
  highlighted/       tạo khi chạy
  .ocr_cache/        cache OCR, tạo khi chạy
```

Mỗi thư mục loại, ví dụ `TNTT`, chứa PDF nguồn. Tool bỏ qua `highlighted/`, `.ocr_cache/` và `_probe/`.

`data.xlsx` dùng sheet đầu. Bắt buộc có cột **MSSV** (7 chữ số) và **Họ tên**. File mẫu: [`samples/danh-sach.sample.xlsx`](../samples/danh-sach.sample.xlsx).

OCR dùng [RapidOCR](https://github.com/RapidAI/RapidOCR), chạy CPU. PDF scan không có lớp chữ nên tool render từng trang rồi ghép ô thành hàng.

## Chạy

```text
.\highlighter.ps1 -DryRun -Limit 3
.\highlighter.ps1 -Only TNTT -SkipExisting
.\highlighter.ps1 -RefreshCache
.\.venv\Scripts\python.exe highlighter\highlight.py --only TNTT
```

| Tham số | Ý nghĩa |
|---------|---------|
| `-Only` / `--only` | Chỉ một thư mục loại, lặp lại được |
| `-Limit` / `--limit` | Chỉ N MSSV đầu sau khi lọc |
| `-DryRun` / `--dry-run` | Không ghi PDF |
| `-SkipExisting` / `--skip-existing` | Không ghi đè file đã có |
| `-RefreshCache` / `--refresh-cache` | OCR lại và cập nhật cache |
| `-NoCache` / `--no-cache` | Không đọc hay ghi `.ocr_cache` |
| `-CleanOutput` / `--clean-output` | Xóa `highlighted/` trước khi chạy |
| `-Faculty` / `--faculty` | Đơn vị cần lọc. Mặc định Khoa học và Kỹ thuật Máy tính |
| `-Data`, `-OutputDir`, `-Root` | File Excel, thư mục đích, thư mục gốc của tool |
| `--scale` | Độ phân giải render, mặc định `2.0` |

Nhật ký mặc định: `highlighter/highlight.log`.
