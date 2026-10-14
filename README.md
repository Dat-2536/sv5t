# SV5T Toolkit

Bộ công cụ xử lý hồ sơ Sinh viên 5 tốt cho Khoa Khoa học và Kỹ thuật Máy tính, Trường Đại học Bách khoa TP.HCM. Các tool Python chạy trên máy, dùng chung một môi trường `.venv`. Bản web xử lý ảnh và PDF ngay trên trình duyệt, file không rời máy.

## Cài đặt

Cần Python 3.12 trở lên. Tool đăng ký tài khoản cần thêm Google Chrome.

Ở thư mục gốc repo:

```text
python -m venv .venv
.\venv.ps1
pip install -r requirements.txt
```

Mỗi file `*.ps1` cũng tự tạo `.venv` và cài thư viện nếu chưa có. Chạy chúng từ thư mục gốc repo.

## Luồng làm việc

Các tool độc lập. Thứ tự dưới đây là một lượt chuẩn bị minh chứng rồi đưa lên web ĐHQG.

| Bước | Lệnh | Việc làm |
|------|------|----------|
| 1 | `.\crawl-profile-image-mybk.ps1` | Tải ảnh thẻ từ myBk |
| 2 | `.\resizer.ps1` | Đưa ảnh về khoảng dung lượng, xoá watermark, làm nét |
| 3 | `.\renamer.ps1` | Đổi tên file minh chứng theo MSSV |
| 4 | `.\distribute-files.ps1` | Gom file vào từng thư mục sinh viên |
| 5 | `.\pdf-converter.ps1` | Chuyển ảnh minh chứng sang PDF |
| 6 | `.\highlighter.ps1` | Tô vàng dòng MSSV trên PDF scan |
| 7 | `.\register-dhqg.ps1` | Tạo tài khoản và ghi hồ sơ trên youth.vnuhcm.edu.vn |
| 8 | `.\crawl-dhqg.ps1` | Cào hồ sơ đã nộp về Excel |

`web-tools` làm các việc ảnh/PDF tương tự ngay trên trình duyệt. Mở `web-tools/index.html`.

## Dữ liệu

Danh sách sinh viên, mật khẩu, ảnh và kết quả chạy ở lại trên máy, không đưa lên GitHub.

- Danh sách tài khoản: copy [`samples/danh-sach.sample.xlsx`](samples/danh-sach.sample.xlsx) thành `data.xlsx` trong thư mục tool cần dùng.
- Hồ sơ đăng ký ĐHQG: copy [`samples/ho-so.sample.xlsx`](samples/ho-so.sample.xlsx) thành `register-dhqg/data.xlsx`.
- Tài khoản myBk: copy `crawl-profile-image-mybk/.env.sample` thành `.env` rồi điền mật khẩu.
- Ngưỡng dung lượng ảnh: copy `resizer/.env.sample` thành `resizer/.env` nếu muốn đổi MIN/MAX. `resizer.ps1` tự copy lần chạy đầu.

## Từng tool

- [crawl-profile-image-mybk](crawl-profile-image-mybk/README.md) — tải ảnh thẻ myBk
- [resizer](resizer/README.md) — chuẩn hoá dung lượng, xoá watermark, làm nét
- [renamer](renamer/README.md) — đổi tên file minh chứng
- [distribute-files](distribute-files/README.md) — gom file theo sinh viên
- [pdf-converter](pdf-converter/README.md) — ảnh sang PDF
- [highlighter](highlighter/README.md) — tô dòng trên PDF scan
- [register-dhqg](register-dhqg/README.md) — đăng ký và ghi hồ sơ ĐHQG
- [crawl-dhqg](crawl-dhqg/README.md) — cào hồ sơ ĐHQG ra Excel
- [web-tools](web-tools/README.md) — bản chạy trên trình duyệt
