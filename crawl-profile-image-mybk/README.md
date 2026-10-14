# Tải ảnh thẻ sinh viên từ myBk HCMUT

## Mô tả

Tool đọc danh sách MSSV trong `data.xlsx`, đăng nhập myBk bằng tài khoản cán bộ (CAS HCMUT), gọi API ảnh thẻ 4×6 và lưu file vào folder `Ảnh thẻ` theo cột **Tên ảnh**.

Không cần mở Chrome hay Playwright — chỉ HTTP (đăng nhập CAS + REST API).

## Web

- Trang quản lý (tham khảo): [Danh sách sinh viên](https://mybk.hcmut.edu.vn/app/he-thong-quan-ly-hoc-vu/quan-ly-sinh-vien/danh-sach-sinh-vien)
- API ảnh (bản gốc): `GET /api/public/media/hinh-the-4x6/{MSSV}/original/v1`

Tài khoản trong `.env` cần quyền tra cứu sinh viên (giống khi bạn filter MSSV và mở **Xem thông tin và hồ sơ** trên web).

## Cấu hình

Tạo file `crawl-profile-image-mybk/.env`:

```env
ACCOUNT=ten_dang_nhap_hcmut
PASSWORD=mat_khau
```

## File `data.xlsx`

Sheet mặc định, dòng 1 là header. Tool dùng các cột:

| Cột | Tên (gợi ý) | Ghi chú |
|-----|-------------|---------|
| B | MSSV | Số mã sinh viên |
| E | Họ tên | Chỉ dùng khi thiếu tên file |
| F | Tên ảnh | Tên file đích (không bắt buộc có `.jpg`; tool tự thêm) |

Ví dụ tên ảnh: `2410712_Ảnh thẻ_Nguyễn Tiến Đạt` → file `2410712_Ảnh thẻ_Nguyễn Tiến Đạt.jpg` trong `Ảnh thẻ/`.

## Chạy tool

Ở **thư mục gốc repo** (cùng cách với `register-dhqg`):

```text
.\crawl-profile-image-mybk.ps1
```

Script tự tạo `.venv` (nếu chưa có), cài `requirements.txt`, rồi chạy `crawl-profile-image-mybk\crawl.py`.

Hoặc gọi trực tiếp:

```text
.\.venv\Scripts\python.exe crawl-profile-image-mybk\crawl.py
```

### Tuỳ chọn

```text
.\crawl-profile-image-mybk.ps1 -Limit 5
.\crawl-profile-image-mybk.ps1 -SkipExisting
```

| Tham số | Ý nghĩa |
|---------|---------|
| `-Limit N` | Chỉ xử lý N dòng đầu (0 = tất cả) |
| `-SkipExisting` | Bỏ qua nếu file trong `Ảnh thẻ/` đã tồn tại và không rỗng |

Tương đương Python: `--limit 5`, `--skip-existing`.

## Kết quả

- Ảnh: `crawl-profile-image-mybk\Ảnh thẻ\*.jpg`
- Log: `crawl-profile-image-mybk\crawl.log`

Trạng thái trong log:

| Status | Ý nghĩa |
|--------|---------|
| `ok` | Tải và ghi file thành công |
| `skip` | Đã có file (khi dùng `-SkipExisting`) |
| `error` | Lỗi (không có ảnh, hết quyền, MSSV sai, …) |
| `summary` | Tổng kết cuối lượt chạy |

Mã thoát: `0` nếu không có dòng lỗi; `1` nếu có ít nhất một `error`; `2` nếu thiếu `.env`/dữ liệu.
