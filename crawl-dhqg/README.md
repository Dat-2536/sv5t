# Cào hồ sơ SV5T cấp ĐHQG-HCM

Tool đăng nhập từng tài khoản trên https://youth.vnuhcm.edu.vn/, đọc thông tin cá nhân và toàn bộ nội dung tiêu chí (kèm tên file và link minh chứng), rồi ghi một file Excel.

Đăng nhập đi bằng form thường, không mở Chrome và không qua reCAPTCHA. Cách xuất Excel giống tool cấp Thành phố: một dòng một sinh viên, thông tin cá nhân ở bên trái, mỗi tiêu chí ba cột (nội dung, tên file, link file).

## File tài khoản

Đặt `data.xlsx` trong thư mục `crawl-dhqg`. Chạy `.\crawl-dhqg.ps1` là tool tự đọc file đó.

Dòng tiêu đề cần có cột tài khoản và mật khẩu. Các tên sau đều được nhận:

- Tài khoản, Email, Tài khoản / Email
- Mật khẩu
- MSSV, Mã số sinh viên/cán bộ (không bắt buộc)
- Họ tên, Họ và tên (không bắt buộc)

## Chạy

Ở thư mục gốc repo:

```text
.\crawl-dhqg.ps1
```

Lệnh này tự tạo `.venv` nếu chưa có, cài thư viện, rồi cào. Kết quả:

- `crawl-dhqg/kết quả/Du_lieu_SV5T_DHQG_<thời gian>.xlsx`
- `crawl-dhqg/nhật ký/Nhat_ky_SV5T_DHQG_<thời gian>.log`
- `crawl-dhqg/nhật ký/schema.json` — tên model và trường trên web, không có dữ liệu sinh viên

```text
.\crawl-dhqg.ps1 -Limit 5
.\crawl-dhqg.ps1 -Workers 8 -Retries 3
.\crawl-dhqg.ps1 -Account "sinhvien@hcmut.edu.vn"
```

Muốn dùng file khác:

```text
.\crawl-dhqg.ps1 -Data "D:\duong\dan\data.xlsx"
```

Hoặc gọi trực tiếp:

```text
.\.venv\Scripts\python.exe crawl-dhqg\crawl.py --limit 5
```

Trạng thái trong Excel và nhật ký: `Thành công`, `Lỗi một phần`, `Chưa có hồ sơ`, `Sai tài khoản/mật khẩu`, `Lỗi ngoài dự kiến`. Sai mật khẩu không được thử lại. Lỗi mạng được thử lại theo `-Retries`.
