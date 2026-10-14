# Highlight danh sách PDF theo MSSV

Tool OCR PDF scan (danh sách sinh viên đính kèm quyết định), lọc dòng thuộc **Khoa học và Kỹ thuật Máy tính**, chỉ xử lý MSSV có trong `data.xlsx`, rồi xuất bản sao PDF có **tô vàng cả hàng** vào `highlighted/`.

Tên file output:

**`<mssv>_<tên folder loại>_<họ tên sinh viên>.pdf`**

Ví dụ: `2210182_TNTT_Lê Thành Bách.pdf`

## Cấu trúc thư mục

```text
highlighter/
  data.xlsx          ← danh sách MSSV (bắt buộc)
  TNTT/
    TNTT.pdf         ← PDF nguồn (scan)
  highlighted/       ← PDF đã highlight (tạo khi chạy)
  .ocr_cache/        ← cache kết quả OCR (tùy chọn, tăng tốc lần sau)
  highlight.py
  highlight.log
```

Mỗi **folder loại** (vd. `TNTT`) chứa một hoặc nhiều file `.pdf`. Tool bỏ qua `highlighted/`, `.ocr_cache/`, `_probe/`.

## File `data.xlsx`

Sheet đầu tiên, bắt buộc có cột **MSSV** và **Họ tên** (có dấu). Tool chỉ dò MSSV 7 chữ số trên PDF; **họ tên trong tên file luôn lấy từ Excel**, không dùng OCR.

| MSSV    | Họ tên           |
|---------|------------------|
| 2210182 | Lê Thành Bách    |

## OCR

Dùng [RapidOCR](https://github.com/RapidAI/RapidOCR) (ONNX, nhẹ, không cần GPU). PDF không có lớp text — tool render từng trang rồi OCR, ghép ô theo hàng, nhận diện cột STT / Họ tên / MSSV / Đơn vị.

## Chạy tool

Ở **thư mục gốc repo**:

```text
.\highlighter.ps1
```

Thử nhanh (không ghi file):

```text
.\highlighter.ps1 -DryRun -Limit 3
```

Chỉ folder `TNTT`, bỏ qua file đã có:

```text
.\highlighter.ps1 -Only TNTT -SkipExisting
```

OCR lại (cập nhật cache):

```text
.\highlighter.ps1 -RefreshCache
```

Gọi trực tiếp Python:

```text
.\.venv\Scripts\python.exe highlighter\highlight.py --only TNTT
```

## Tuỳ chọn chính

| Tham số | Ý nghĩa |
|---------|---------|
| `--faculty` | Đơn vị cần lọc (mặc định: Khoa học và Kỹ thuật Máy tính) |
| `--scale` | Độ phân giải render OCR (mặc định `2.0`) |
| `--limit N` | Chỉ xử lý N MSSV đầu |
| `--dry-run` | Log only |
| `--skip-existing` | Không ghi đè file trong `highlighted/` |
| `--clean-output` | Xóa `highlighted/` trước khi chạy |
| `--no-cache` | Không dùng `.ocr_cache` |

Log mặc định: `highlighter/highlight.log` (TSV: thời gian, trạng thái, nguồn, chi tiết).
