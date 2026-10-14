# Chuyển ảnh minh chứng sang PDF

Web SV5T (trừ ảnh thẻ) yêu cầu minh chứng dạng **PDF**. Tool này chuyển hàng loạt file `.png`, `.jpg`, `.webp`, … trong một folder thành PDF **cùng tên**, **giữ nguyên kích thước ảnh** — không ép khổ A4 hay thêm viền trắng.

Tương tự lệnh ImageMagick trên CMD:

```text
for %i in (*.png) do magick "%i" "%~ni.pdf"
```

nhưng gom một lần cho nhiều đuôi, có log và tuỳ chọn xóa ảnh gốc.

## Đuôi file hỗ trợ

`.jpg`, `.jpeg`, `.jfif`, `.png`, `.webp`, `.bmp`, `.tif`, `.tiff`, `.gif`

## Cấu trúc

```text
pdf-converter/
  cv/                  ← (tuỳ chọn) bỏ ảnh CV/minh chứng vào đây rồi convert
    anh1.jpg
    anh2.png
  convert.py
  convert.log          ← tạo khi chạy
pdf-converter.ps1      ← wrapper ở thư mục gốc repo
```

## Quy ước đường dẫn

Trong README, **gốc repo** = thư mục có file `pdf-converter.ps1` (thường là clone `sv5t`).

| Ký hiệu | Ý nghĩa |
|---------|---------|
| `gốc repo` | Nơi chạy `.\pdf-converter.ps1` |
| `pdf-converter\cv` | Ví dụ folder ảnh — **thay** bằng folder bạn đang xử lý (vd. `distribute-files\output\2352410_Ho Ten\`) |

Luôn `cd` vào **gốc repo** trước khi gọi `.\pdf-converter.ps1 -InputDir "..."`, trừ khi ghi rõ là đang `cd` vào chính folder ảnh.

## Cách dùng (gợi ý)

### 1. Đứng trong folder ảnh (giống ImageMagick)

```text
cd <folder-anh-cua-ban>
<duong-dan-toi-goc-repo>\pdf-converter.ps1
```

Ví dụ ảnh nằm trong repo:

```text
cd pdf-converter\cv
..\..\pdf-converter.ps1
```

Mặc định quét **thư mục hiện tại** (nơi bạn `cd`), không quét folder con.

### 2. Chỉ định folder ảnh từ gốc repo

```text
cd <goc-repo>
.\pdf-converter.ps1 -InputDir "pdf-converter\cv"
```

### 3. Python trực tiếp

Từ gốc repo:

```text
cd <goc-repo>
.\.venv\Scripts\python.exe pdf-converter\convert.py pdf-converter\cv
```

Đã `cd` vào folder ảnh:

```text
cd pdf-converter\cv
..\..\pdf-converter.ps1
```

(hoặc từ trong `cv`: `..\..\.venv\Scripts\python.exe ..\convert.py .` — ít dùng hơn `.ps1`)

### 4. Ví dụ: convert ảnh trong `pdf-converter/cv/`

Cho ảnh nằm **trực tiếp** trong `pdf-converter/cv/` (không quét folder con trừ khi bật `-Recursive`).

**Chạy ở đâu:** `cd` vào **gốc repo** (có `pdf-converter.ps1`), **không** bắt buộc `cd` vào `cv`.

```text
cd <goc-repo>
.\pdf-converter.ps1 -InputDir "pdf-converter\cv"
```

Kết quả: mỗi `pdf-converter\cv\<ten>.jpg` → `pdf-converter\cv\<ten>.pdf` (cùng folder).

Thử trước, không ghi file:

```text
.\pdf-converter.ps1 -InputDir "pdf-converter\cv" -DryRun
```

**Cách 2 — đứng trong `cv`:**

```text
cd pdf-converter\cv
..\..\pdf-converter.ps1
```

Nếu ảnh nằm trong **folder con** (vd. `cv\2024\scan.jpg`), thêm `-Recursive`:

```text
cd <goc-repo>
.\pdf-converter.ps1 -InputDir "pdf-converter\cv" -Recursive
```

## Chỉ xóa PNG / Convert PNG rồi xóa PNG

Hai nhu cầu thường gặp khi folder đã có cả `.png` và `.pdf` (hoặc còn JPG không muốn đụng tới).

### Trường hợp 1 — Chỉ xóa file PNG (không chạy convert)

Dùng khi **đã có PDF** tương ứng (convert trước đó) và bạn chỉ muốn dọn ảnh PNG. Tool **không** có lệnh “chỉ xóa”; dùng PowerShell/CMD trong folder ảnh.

**Cách A — từ gốc repo** (thay `pdf-converter\cv` bằng folder ảnh của bạn):

```text
cd <goc-repo>
Remove-Item -Path "pdf-converter\cv\*.png"
```

**Cách B — `cd` vào folder ảnh** (giống `del *.png` trên CMD):

```text
cd pdf-converter\cv
Remove-Item *.png
```

CMD (đang ở trong folder ảnh):

```text
cd pdf-converter\cv
del *.png
```

Lưu ý:

- Lệnh trên xóa **mọi** `.png` trong folder đó; **không** kiểm tra đã có `.pdf` hay chưa — nên backup hoặc `-DryRun` convert trước.
- **Không** xóa `.jpg`, `.webp`, … — chỉ đuôi `.png`.

### Trường hợp 2 — Tạo PDF từ PNG và xóa PNG ngay (một lệnh)

Dùng `-Ext png` (chỉ quét PNG) kèm `-DeleteSources` (xóa **đúng** file PNG vừa convert thành công). JPG/WebP/… **không** bị convert, **không** bị xóa.

**Bước 1 — xem trước** (từ gốc repo):

```text
cd <goc-repo>
.\pdf-converter.ps1 -InputDir "pdf-converter\cv" -Ext png -DryRun
```

**Bước 2 — convert + xóa PNG**:

```text
cd <goc-repo>
.\pdf-converter.ps1 -InputDir "pdf-converter\cv" -Ext png -DeleteSources
```

Mỗi `minh-chung.png` thành công → `minh-chung.pdf` cùng folder, rồi `minh-chung.png` bị xóa; log có dòng `deleted`.

**Đã `cd` vào folder ảnh** (không cần `-InputDir`):

```text
cd pdf-converter\cv
..\..\pdf-converter.ps1 -Ext png -DeleteSources
```

**Python** (tương đương):

```text
cd <goc-repo>
.\.venv\Scripts\python.exe pdf-converter\convert.py pdf-converter\cv --ext png --delete-sources
```

Nếu PDF cùng tên **đã tồn tại** và bạn không muốn ghi đè nhưng vẫn muốn bỏ PNG sau khi chắc chắn có PDF — chạy convert **không** xóa với `-SkipExisting`, rồi xóa PNG thủ công (trường hợp 1). `-SkipExisting` sẽ **bỏ qua** file đó nên **không** xóa PNG tương ứng.

### Gộp ý: convert mọi đuôi, sau đó chỉ dọn PNG

```text
cd <goc-repo>
.\pdf-converter.ps1 -InputDir "pdf-converter\cv"
Remove-Item -Path "pdf-converter\cv\*.png"
```

Bước 1 tạo PDF từ png/jpg/webp/…; bước 2 chỉ xóa `.png`, giữ JPG nếu còn.

## Tuỳ chọn (PowerShell)

```text
.\pdf-converter.ps1 -DryRun
.\pdf-converter.ps1 -Ext png -Ext jpg
.\pdf-converter.ps1 -SkipExisting
.\pdf-converter.ps1 -DeleteSources
.\pdf-converter.ps1 -Recursive
.\pdf-converter.ps1 -Quiet
.\pdf-converter.ps1 -NoLog
.\pdf-converter.ps1 -Log "pdf-converter\my-run.log"
```

| Tham số | Python | Ý nghĩa |
|---------|--------|---------|
| (vị trí / `-InputDir`) | `input` | Folder ảnh (mặc định `.` = cwd khi gọi Python; ps1 mặc định **cwd**) |
| `-Ext` | `--ext` (lặp) | Chỉ một số đuôi, vd. `-Ext png` `-Ext jpg` |
| `-Recursive` | `--recursive` | Quét cả thư mục con |
| `-DryRun` | `--dry-run` | Liệt kê, không tạo PDF |
| `-SkipExisting` | `--skip-existing` | Bỏ qua nếu đã có `.pdf` cùng tên |
| `-DeleteSources` | `--delete-sources` | Xóa ảnh gốc **vừa convert OK** trong lần chạy (kết hợp `-Ext png` → chỉ xóa PNG) |
| `-Quiet` | `--quiet` | Không in từng dòng |
| `-Log` / `-NoLog` | `--log` / `--no-log` | File log |

## Ví dụ theo từng đuôi (PowerShell)

Chỉ PNG (folder ảnh qua `-InputDir`):

```text
cd <goc-repo>
.\pdf-converter.ps1 -InputDir "pdf-converter\cv" -Ext png
```

Chỉ JPG/JPEG:

```text
cd <goc-repo>
.\pdf-converter.ps1 -InputDir "pdf-converter\cv" -Ext jpg -Ext jpeg
```

Convert **mọi** đuôi hỗ trợ rồi xóa **tất cả** ảnh vừa convert (cẩn thận):

```text
cd <goc-repo>
.\pdf-converter.ps1 -InputDir "pdf-converter\cv" -DeleteSources
```

Xóa từng loại thủ công (đang `cd` trong folder ảnh):

```text
del *.png
del *.jpg
```

## Kích thước trang PDF

Mỗi PDF **một trang**, kích thước trang = kích thước pixel của ảnh (1 pixel ≈ 1 point, giống `magick ảnh.png ảnh.pdf` mặc định). **Không** pad A4/Letter.

Ảnh có xoay EXIF được chỉnh trước khi tạo PDF.

## Log

Mặc định: `pdf-converter/convert.log`

| Status | Ý nghĩa |
|--------|---------|
| `ok` | Tạo PDF thành công |
| `dry-run` | Mô phỏng |
| `skip` | Đã có PDF (`-SkipExisting`) |
| `deleted` | Đã xóa ảnh gốc (`-DeleteSources`) |
| `error` | Lỗi từng file |
| `summary` | Tổng kết |

Mã thoát: `0` thành công; `1` có lỗi; `2` không có ảnh / thư mục không tồn tại.

## Luồng với các tool khác trong repo

1. `renamer` → đổi tên file  
2. `distribute-files` → gom theo sinh viên  
3. **`pdf-converter`** → đổi minh chứng ảnh sang PDF trong folder từng SV  
4. (tuỳ chọn) `resizer` — thường làm **trước** bước PDF nếu cần giảm dung lượng ảnh  

Dùng chung `.venv` và `requirements.txt` của repo (`pymupdf`, `pillow`).
