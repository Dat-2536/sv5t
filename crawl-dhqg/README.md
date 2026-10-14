# Cào hồ sơ SV5T ĐHQG

Đăng nhập từng tài khoản trên https://youth.vnuhcm.edu.vn/, đọc thông tin cá nhân và nội dung từng tiêu chí, kèm tên file và link minh chứng, rồi ghi một file Excel.

Đăng nhập bằng form thường, không mở Chrome và không qua reCAPTCHA. Mỗi sinh viên một dòng: thông tin cá nhân bên trái, mỗi tiêu chí ba cột (nội dung, tên file, link file).

## Chuẩn bị

Đặt `crawl-dhqg/data.xlsx`, hoặc truyền đường dẫn khác bằng `-Data`. Dòng tiêu đề phải có cột tài khoản và mật khẩu. File mẫu: [`samples/danh-sach.sample.xlsx`](../samples/danh-sach.sample.xlsx).

Các tên sau đều được nhận, có dấu hoặc không:

| Cột | Tên chấp nhận |
|-----|----------------|
| Tài khoản | Tài khoản, Email, Username |
| Mật khẩu | Mật khẩu, Password |
| MSSV | Không bắt buộc |
| Họ tên | Không bắt buộc |

## Chạy

```text
.\crawl-dhqg.ps1
.\crawl-dhqg.ps1 -Limit 5
.\crawl-dhqg.ps1 -Workers 8 -Retries 3
.\crawl-dhqg.ps1 -Account "sinhvien@hcmut.edu.vn"
.\crawl-dhqg.ps1 -Data "D:\duong\dan\data.xlsx"
```

`-Account` hỏi mật khẩu lúc chạy và chỉ cào một tài khoản.

```text
.\.venv\Scripts\python.exe crawl-dhqg\crawl.py crawl-dhqg\data.xlsx --limit 5 --workers 6 --retries 2
```

## Kết quả

- `crawl-dhqg/kết quả/Du_lieu_SV5T_DHQG_<thời gian>.xlsx`
- `crawl-dhqg/nhật ký/Nhat_ky_SV5T_DHQG_<thời gian>.log`
- `crawl-dhqg/nhật ký/schema.json` ghi tên model và trường trên web, không chứa dữ liệu sinh viên

Trạng thái: `Thành công`, `Lỗi một phần`, `Chưa có hồ sơ`, `Sai tài khoản/mật khẩu`, `Lỗi ngoài dự kiến`. Sai mật khẩu không được thử lại. Lỗi mạng thử lại theo `-Retries`, mặc định 2. Số luồng mặc định là 6.
