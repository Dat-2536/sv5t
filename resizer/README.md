# Chuẩn hoá dung lượng ảnh minh chứng

Tool đọc ảnh trong `input/`, so sánh dung lượng với **MIN** và **MAX** trong `resizer/.env`, rồi ghi ảnh đã xử lý vào `output/`.

- **Lớn hơn MAX**: giảm dung lượng bằng nén JPEG (tìm quality phù hợp) hoặc giảm `compress_level` PNG; nếu vẫn quá lớn thì thu nhỏ kích thước pixel (LANCZOS), không thêm viền.
- **Nhỏ hơn MIN**: làm nét nhẹ (UnsharpMask), lưu JPEG chất lượng cao / PNG ít nén; có thể phóng to tối đa ~15% (`MAX_UPSCALE_RATIO`); nếu vẫn dưới MIN thì **pad metadata** (segment COM trong JPEG, chunk `tEXt` trong PNG) — không vẽ margin, ảnh hiển thị giữ nguyên.
- **Trong khoảng MIN–MAX**: bỏ qua, không ghi ra `output/` (trừ khi ảnh đã được xoá watermark hoặc làm nét).
- **Watermark myBk** (ảnh thẻ từ `crawl-profile-image-mybk`): dò từng chữ `www.hcmut.edu.vn` trong ảnh rồi làm sáng lại nét chữ về màu nền — xoá cả trên nền, mặt và áo mà không làm mờ khuôn mặt.
- **Làm nét**: ảnh nhỏ (cạnh dài ≤ `ENHANCE_MAX_SIDE`) được phóng to ×2 bằng model Real-ESRGAN (chạy CPU, khoảng 1–8 giây/ảnh), sau bước xoá watermark.

Ảnh mẫu: một số file đã copy từ `crawl-profile-image-mybk/Ảnh thẻ/` vào `resizer/input/` để thử.

## Cấu hình

Lần chạy đầu, `resizer.ps1` tự copy `resizer/.env.example` → `resizer/.env` nếu chưa có file `.env`.

```env
MIN_SIZE_MB=1MB
MAX_SIZE_MB=5MB
SHARPEN=1
ALLOW_UPSCALE=1
MAX_UPSCALE_RATIO=1.15
JPEG_SUBSAMPLING=0
REMOVE_WATERMARK=1
WATERMARK_MIN_HITS=8
WATERMARK_STRENGTH=1.3
WATERMARK_PASSES=4
ENHANCE=1
ENHANCE_SCALE=2
ENHANCE_BLEND=0.8
ENHANCE_MAX_SIDE=1200
```

| Biến | Ý nghĩa |
|------|---------|
| `MIN_SIZE_MB` / `MIN_MB` / `MIN` | Dung lượng tối thiểu (vd. `1MB`, `500KB`) |
| `MAX_SIZE_MB` / `MAX_MB` / `MAX` | Dung lượng tối đa |
| `SHARPEN` | `1` = làm nét nhẹ (UnsharpMask) trước khi tăng size với ảnh không qua Real-ESRGAN; `0` = tắt |
| `ALLOW_UPSCALE` | Cho phép phóng to pixel nhẹ nếu vẫn dưới MIN |
| `MAX_UPSCALE_RATIO` | Hệ số phóng to tối đa so với ảnh gốc (mặc định `1.15`) |
| `JPEG_SUBSAMPLING` | `0` = 4:4:4 (file nặng hơn, nét hơn); `2` = 4:2:0 |
| `REMOVE_WATERMARK` | `1` = bật xoá watermark ảnh thẻ myBk |
| `WATERMARK_MIN_HITS` | Số chữ watermark tối thiểu dò được để coi là có watermark (tăng nếu nhận nhầm ảnh thường) |
| `WATERMARK_STRENGTH` | Mức làm sáng tối đa = hệ số × độ đậm đo được của từng chữ (mặc định `1.3`); giảm nếu thấy mắt/lông mày bị nhạt |
| `WATERMARK_PASSES` | Số lượt dò + xoá, mỗi lượt dọn tiếp vết còn sót (mặc định `4`; tăng nếu còn vết mờ) |
| `ENHANCE` | `1` = làm nét bằng Real-ESRGAN; `0` = tắt |
| `ENHANCE_SCALE` | Ảnh đầu ra lớn gấp bao nhiêu lần ảnh gốc (`1`–`4`, mặc định `2`) |
| `ENHANCE_BLEND` | Tỉ lệ lấy từ model (`1` = nét nhất; thấp hơn = da tự nhiên hơn, ít vẻ "vẽ") |
| `ENHANCE_MAX_SIDE` | Chỉ làm nét ảnh có cạnh dài ≤ giá trị này (px) |

## Chạy tool

Ở **thư mục gốc repo**:

```text
.\resizer.ps1
```

Hoặc gọi Python trực tiếp:

```text
.\.venv\Scripts\python.exe resizer\resize.py
```

### Tuỳ chọn

```text
.\resizer.ps1 -Limit 10
.\resizer.ps1 -DryRun
.\resizer.ps1 -SkipExisting
.\resizer.ps1 -InputDir "D:\path\to\anh" -OutputDir "D:\path\to\out"
.\resizer.ps1 -Recursive
.\resizer.ps1 -NoWatermark
.\resizer.ps1 -NoEnhance
```

| Tham số | Ý nghĩa |
|---------|---------|
| `-InputDir` | Thư mục nguồn (mặc định `resizer/input`) |
| `-OutputDir` | Thư mục đích (mặc định `resizer/output`) |
| `-Limit N` | Chỉ xử lý N file đầu |
| `-Recursive` | Quét cả thư mục con của input |
| `-DryRun` | Chỉ log, không ghi file |
| `-SkipExisting` | Bỏ qua nếu file đích đã tồn tại |
| `-NoWatermark` | Tắt bước xoá watermark |
| `-NoEnhance` | Tắt bước làm nét |

Tương đương Python: `--input`, `--output`, `--limit`, `--recursive`, `--dry-run`, `--skip-existing`, `--no-watermark`, `--no-enhance`.

## Kết quả

- Ảnh đã chỉnh: `resizer/output/` (giữ cấu trúc thư mục con nếu dùng `-Recursive`)
- Log: `resizer/resize.log`

| Status | Ý nghĩa |
|--------|---------|
| `compress` | Ảnh ban đầu > MAX, đã nén/thu nhỏ |
| `expand` | Ảnh ban đầu < MIN, đã làm nét / pad metadata |
| `watermark` | Đã xoá watermark myBk (log có `watermark hits=N` = số chữ đã xử lý) |
| `enhance` | Ảnh đã trong MIN–MAX, chỉ được làm nét (log có `enhanced WxH`) |
| `skip` | Đã nằm trong MIN–MAX hoặc đã có file đích (`-SkipExisting`) |
| `error` | Lỗi đọc/ghi ảnh |
| `summary` | Tổng kết cuối lượt chạy |

Mã thoát: `0` nếu không lỗi; `1` nếu có ít nhất một `error`; `2` nếu thiếu ảnh hoặc `.env` không hợp lệ.

## Ghi chú kỹ thuật

### Cách xoá watermark

Watermark myBk là chuỗi `www.hcmut.edu.vn` màu xám, nghiêng ~45°, lặp khoảng 20–30 lần trên ảnh. Mọi ảnh dùng **cùng một mẫu chữ**, chỉ khác cỡ chữ và vị trí, và watermark làm tối ảnh theo tỉ lệ (rõ trên nền trắng, gần như không thấy trên áo/tóc tối).

1. **Mẫu chữ + thư viện bố cục** (`resizer/mybk_watermark.npz`): dựng một lần từ nhiều ảnh crawl — lấy trung vị để triệt tiêu khuôn mặt, chỉ giữ lại watermark, rồi tách ra một chữ đơn. Đồng thời gom các ảnh có cùng cách đặt chữ thành "bố cục" (vị trí chữ chuẩn hoá theo khổ ảnh).
2. **Dò**: với mỗi ảnh, tìm cỡ chữ phù hợp rồi template matching để định vị từng chữ (tinh chỉnh cỡ và vị trí riêng cho mỗi chữ).
3. **Bổ sung chữ bị sót** (thường nằm trên mặt, tóc, áo — khớp mẫu kém):
   - Nếu ảnh khớp một bố cục đã biết, lấy các vị trí còn thiếu từ bố cục.
   - Nhận thêm ứng viên khớp mẫu yếu nếu phần lớn nét chữ tại đó đúng là nét tối mảnh với độ đậm giống các chữ chắc chắn.
4. **Xoá**: watermark làm tối ảnh theo tỉ lệ và không đổi màu, nên chỉ cần làm sáng lại kênh độ sáng tại nét chữ về mức nền cục bộ. Mức làm sáng mỗi chữ bị giới hạn theo độ đậm watermark đo được (của chính chữ đó và của cả ảnh), nên mắt, lông mày, nốt ruồi không bị xoá theo. Chạy 4 lượt, lượt sau dọn tiếp vết sót.

### Làm nét

Dùng model [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) `realesr-general-x4v3` (giấy phép BSD-3-Clause) dạng ONNX tại `resizer/models/realesr-general-x4v3.onnx`, chạy bằng `onnxruntime` trên CPU. Ảnh được phóng ×4 rồi thu về `ENHANCE_SCALE` (mặc định ×2) và trộn một phần với ảnh phóng thường (`ENHANCE_BLEND`) để giữ kết cấu da tự nhiên. Không dùng model "phục hồi khuôn mặt" (GFPGAN, CodeFormer) vì chúng vẽ lại mắt/mũi, làm ảnh thẻ không còn đúng người.

Thiếu model thì tool vẫn chạy, chỉ bỏ qua bước làm nét. Tải lại model:

```text
Invoke-WebRequest https://huggingface.co/CoderViking/realesr-general-x4v3-onnx/resolve/main/realesr-general-x4v3.onnx -OutFile resizer\models\realesr-general-x4v3.onnx
```

Dựng lại mẫu chữ (khi myBk đổi watermark), cần ≥ 20 ảnh thẻ có watermark:

```text
.\.venv\Scripts\python.exe resizer\resize.py --build-watermark-template crawl-profile-image-mybk
```

### Khác
- Pad metadata an toàn cho trình xem ảnh thông thường; một số cổng upload có thể strip metadata — khi đó hãy tăng `MIN` nhẹ hoặc bật `ALLOW_UPSCALE`.
- Ảnh PNG quá lớn thường được chuyển sang JPEG khi nén; ảnh JPG nhỏ thường giữ định dạng JPG.
