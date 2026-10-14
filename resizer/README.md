# Chuẩn hoá dung lượng ảnh

Đọc ảnh trong `input/`, so với `MIN` và `MAX` trong `.env`, rồi ghi ảnh đã xử lý vào `output/`.

- Lớn hơn MAX: nén JPEG hoặc PNG. Vẫn quá lớn thì thu nhỏ pixel bằng LANCZOS, không thêm viền.
- Nhỏ hơn MIN: làm nét nhẹ, lưu chất lượng cao, có thể phóng tối đa `MAX_UPSCALE_RATIO`. Vẫn thiếu thì chèn metadata (JPEG COM hoặc PNG `tEXt`). Ảnh hiển thị không đổi.
- Nằm trong khoảng: bỏ qua, trừ khi ảnh vừa được xoá watermark hoặc làm nét.
- Watermark myBk (`www.hcmut.edu.vn`): dò từng chữ rồi làm sáng nét chữ về màu nền. Không làm mờ khuôn mặt.
- Ảnh có cạnh dài không quá `ENHANCE_MAX_SIDE`: phóng bằng Real-ESRGAN trên CPU, sau bước xoá watermark.

## Chuẩn bị

Bỏ ảnh vào `resizer/input/`. Lần chạy đầu, `resizer.ps1` copy `.env.sample` thành `.env` nếu chưa có. Sửa MIN/MAX trong `.env` trước khi chạy hàng loạt.

| Biến | Ý nghĩa |
|------|---------|
| `MIN_SIZE_MB`, `MAX_SIZE_MB` | Ngưỡng dung lượng, ví dụ `1MB`, `500KB` |
| `SHARPEN` | `1` bật UnsharpMask cho ảnh không qua Real-ESRGAN |
| `ALLOW_UPSCALE`, `MAX_UPSCALE_RATIO` | Cho phép phóng nhẹ nếu vẫn dưới MIN |
| `JPEG_SUBSAMPLING` | `0` là 4:4:4, file nặng và nét hơn |
| `REMOVE_WATERMARK` | `1` bật xoá watermark myBk |
| `WATERMARK_MIN_HITS` | Số chữ tối thiểu để coi là có watermark |
| `WATERMARK_STRENGTH` | Mức làm sáng so với độ đậm đo được |
| `WATERMARK_PASSES` | Số lượt dò và xoá |
| `ENHANCE`, `ENHANCE_SCALE`, `ENHANCE_BLEND` | Làm nét bằng model, hệ số phóng, mức trộn với ảnh phóng thường |
| `ENHANCE_MAX_SIDE` | Chỉ làm nét ảnh có cạnh dài không vượt quá số pixel này |

Model `models/realesr-general-x4v3.onnx` đã có trong repo. Thiếu file thì tool vẫn chạy và bỏ qua bước làm nét. Tải lại:

```text
Invoke-WebRequest https://huggingface.co/CoderViking/realesr-general-x4v3-onnx/resolve/main/realesr-general-x4v3.onnx -OutFile resizer\models\realesr-general-x4v3.onnx
```

## Chạy

```text
.\resizer.ps1
.\resizer.ps1 -Limit 10 -DryRun
.\resizer.ps1 -SkipExisting -Recursive
.\resizer.ps1 -NoWatermark -NoEnhance
.\resizer.ps1 -InputDir "D:\anh" -OutputDir "D:\ra"
```

Python tương ứng: `--input`, `--output`, `--limit`, `--recursive`, `--dry-run`, `--skip-existing`, `--no-watermark`, `--no-enhance`.

## Kết quả

Ảnh ra `resizer/output/`, giữ thư mục con khi bật `-Recursive`. Nhật ký `resize.log`.

| Trạng thái | Ý nghĩa |
|------------|---------|
| `compress` | Ảnh lớn hơn MAX, đã nén hoặc thu nhỏ |
| `expand` | Ảnh nhỏ hơn MIN, đã làm nét hoặc pad metadata |
| `watermark` | Đã xoá watermark. `hits=N` là số chữ đã xử lý |
| `enhance` | Ảnh đã trong khoảng MIN–MAX và được làm nét |
| `skip` | Đã đúng khoảng, hoặc file đích đã có khi dùng `-SkipExisting` |
| `error` | Không đọc hoặc ghi được ảnh |

Mã thoát: `0` không lỗi, `1` có lỗi, `2` thiếu ảnh hoặc `.env` không hợp lệ.

## Watermark và làm nét

Watermark myBk là chữ xám, nghiêng khoảng 45 độ, lặp nhiều lần, làm tối ảnh theo tỉ lệ. Mẫu chữ và các bố cục đã gom trong `mybk_watermark.npz`. Tool tìm cỡ chữ, khớp mẫu, lấy thêm vị trí từ bố cục đã biết, rồi làm sáng đúng nét chữ. Mức sáng bị giới hạn theo độ đậm đo được nên mắt và lông mày không bị xoá theo.

Real-ESRGAN `realesr-general-x4v3` (BSD-3-Clause) phóng 4 lần rồi thu về `ENHANCE_SCALE` và trộn với ảnh phóng thường theo `ENHANCE_BLEND`. Tool không dùng model vẽ lại khuôn mặt.

Khi myBk đổi watermark, dựng lại mẫu từ ít nhất 20 ảnh thẻ:

```text
.\.venv\Scripts\python.exe resizer\resize.py --build-watermark-template crawl-profile-image-mybk
```

Một số cổng upload cắt metadata. Nếu ảnh vẫn dưới MIN sau khi upload, hạ nhẹ ngưỡng hoặc bật `ALLOW_UPSCALE`.
