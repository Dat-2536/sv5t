# Tạo tài khoản SV5T ĐHQG-HCM

## Mô tả
- Tool này tạo tài khoản hàng loạt cho Sinh viên 5 tốt trên hệ thống web của ĐHQG
- Đối với các tài khoản đã tồn tại, nó sẽ tự bỏ qua mà không bị lỗi, nhưng sẽ có log lại

## Web
Chính: https://youth.vnuhcm.edu.vn/
Trang đăng ký tài khoản: https://youth.vnuhcm.edu.vn/web/signup?redirect=%2Fodoo%3F

## Đăng ký
Khi đăng ký cần nhập:
Your Email
Your Name
Password
Confirm Password

và nhấn Sign Up là xong

## Nhập thông tin
Khi vừa đăng ký xong sẽ được redirect về trang nhập thông tin, hoặc nếu không thì tự chuyển về trang đó.

https://youth.vnuhcm.edu.vn/odoo/bat-dau/action-165/<mã hồ sơ>

Nhập toàn bộ thông tin với các label tương ứng với header trong file data.xlsx.

Lưu ý: Trong file data.xlsx cột cần lưu ý format:
1. Số điện thoại nhập 10 chữ số (tính các số 0 ở đầu cho đủ 10 ký tự);
2. CMND/CCCD nhập 12 chữ số (fill thêm số 0 ở đầu cho đủ 10 ký tự)

## Chạy tool

Cần Google Chrome. Ở thư mục gốc của repo, bật `.venv` rồi cài dependency:

```text
.\venv.ps1
pip install -r requirements.txt
```

Save `data.xlsx`, đóng hết cửa sổ Chrome, rồi ở thư mục gốc chạy:

```text
.\register-dhqg.ps1
```

Một lệnh này tự tạo `.venv`, cài thư viện, sao profile Chrome, đăng ký từng tài khoản, ghi hồ sơ (kèm ảnh đại diện >= 1 MB), rồi đối chiếu lại với Excel. Tài khoản đã có sẽ được cập nhật hồ sơ. Kết quả nằm ở `register-dhqg\register.log` và `register-dhqg\validate.log`.

Luân phiên nhiều profile Google (giảm reCAPTCHA): chạy `register-dhqg\prepare-chrome-profiles.ps1`, đăng nhập từng profile Chrome một lần, rồi:

```text
.\register-dhqg.ps1 -ChromeProfiles "$env:LOCALAPPDATA\sv5t-chrome-profiles" -Pause 15
```

Chi tiết reCAPTCHA: `register-dhqg\reCAPCHA.md`.

```text
.\register-dhqg.ps1 -Limit 1
.\register-dhqg.ps1 -ValidateOnly
```

Một cửa sổ Chrome hiện trong lúc đăng ký. `register.log` ghi `created`, `skipped`, `invalid_data`, `signup_error`, `captcha_error`, `profile_error`. `validate.log` ghi `ok`, `missing_account`, `missing_profile`, `mismatch`.
