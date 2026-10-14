# Tải ảnh thẻ từ myBk

Đọc MSSV trong `data.xlsx`, đăng nhập CAS HCMUT bằng tài khoản cán bộ, rồi tải ảnh thẻ 4×6 về `Ảnh thẻ/`. Chỉ dùng HTTP, không mở Chrome.

API: `GET /api/public/media/hinh-the-4x6/{MSSV}/original/v1` trên myBk.

## Chuẩn bị

1. Copy `.env.sample` thành `.env` trong thư mục này và điền tài khoản có quyền xem hồ sơ sinh viên:

```env
ACCOUNT=ten_dang_nhap
PASSWORD=mat_khau
```

2. Đặt `data.xlsx` cùng thư mục. Dòng 1 là tiêu đề. Tool đọc theo vị trí cột, không theo tên:

| Cột | Nội dung |
|-----|----------|
| B | MSSV |
| E | Họ tên, dùng khi chưa có tên file |
| F | Tên file đích, không bắt buộc. Thiếu thì tool đặt `{MSSV}_Ảnh thẻ_{Họ tên}.jpg` |

File mẫu danh sách: [`samples/danh-sach.sample.xlsx`](../samples/danh-sach.sample.xlsx). File đó chưa có cột F, nên tên ảnh sẽ được ghép từ MSSV và họ tên.

## Chạy

Ở thư mục gốc repo:

```text
.\crawl-profile-image-mybk.ps1
.\crawl-profile-image-mybk.ps1 -Limit 5
.\crawl-profile-image-mybk.ps1 -SkipExisting
```

Hoặc:

```text
.\.venv\Scripts\python.exe crawl-profile-image-mybk\crawl.py --limit 5 --skip-existing
```

## Kết quả

Ảnh nằm trong `crawl-profile-image-mybk/Ảnh thẻ/`. Nhật ký `crawl.log` ghi `ok`, `skip`, `error`, `summary`.

Mã thoát: `0` không lỗi, `1` có ít nhất một dòng lỗi, `2` thiếu `.env` hoặc không có dòng hợp lệ.
