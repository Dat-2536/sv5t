# Tạo tài khoản và ghi hồ sơ SV5T ĐHQG

Tạo tài khoản hàng loạt trên https://youth.vnuhcm.edu.vn/, ghi hồ sơ `nominee.info`, rồi đăng nhập lại để đối chiếu với Excel. Tài khoản đã tồn tại được ghi `skipped` và vẫn được cập nhật hồ sơ.

Đăng ký đi qua Chrome thật vì trang dùng reCAPTCHA v3. Tool không tự tạo token và không gọi dịch vụ giải captcha. Chi tiết nằm ở [reCAPCHA.md](reCAPCHA.md). Đăng nhập và ghi hồ sơ đi bằng form cùng JSON-RPC, không qua reCAPTCHA.

## Chuẩn bị

Cần Google Chrome. Đóng hết cửa sổ Chrome trước khi chạy, trừ khi dùng `-FreshChrome`.

Đặt `register-dhqg/data.xlsx`. Dòng tiêu đề cần đúng các tên sau. File mẫu: [`samples/ho-so.sample.xlsx`](../samples/ho-so.sample.xlsx).

| Cột | Ghi chú |
|-----|---------|
| Tài khoản | Email đăng ký |
| Mật khẩu | |
| Họ tên | |
| MSSV hoặc Mã số sinh viên/cán bộ | |
| Trường | Tên đơn vị trên web, khớp chính xác |
| Khoa/Phòng/Ban | |
| Số điện thoại | 9 hoặc 10 số. Ngắn hơn thì thêm 0 cho đủ 10 |
| Nhóm đối tượng | `Sinh viên`, `Giảng viên, trợ giảng, nghiên cứu viên`, `Cán bộ làm công tác quản lý`, `Giáo viên trẻ THPT Năng khiếu` |
| CMND/CCCD | 11 hoặc 12 số. Ngắn hơn thì thêm 0 cho đủ 12 |
| Giới tính | `Nam` hoặc `Nữ` |
| Dân tộc | `1` được hiểu là `Kinh (Việt)` |
| Tôn giáo | `1` được hiểu là `Không` |
| Trình độ học vấn | `Sinh viên`, `Cử nhân/Kỹ sư`, `Thạc sĩ`, `Tiến sĩ` |
| Ngày sinh | `dd/mm/yyyy`, hoặc ô ngày của Excel |
| Địa chỉ thường trú | |
| Địa chỉ tạm trú trùng địa chỉ thường trú? | `Có` / `Không`, hoặc `1` / `0` |
| Địa chỉ tạm trú | Bắt buộc khi không trùng địa chỉ thường trú |

Ảnh đại diện phải từ 1 MB. Nếu chưa có `avatar-placeholder.jpg`, tool tự tạo một ảnh JPEG đủ dung lượng bằng Pillow. File này không được đưa lên GitHub.

## Chạy

```text
.\register-dhqg.ps1
.\register-dhqg.ps1 -Limit 1
.\register-dhqg.ps1 -ValidateOnly
.\register-dhqg.ps1 -SkipValidate
.\register-dhqg.ps1 -FreshChrome
```

Mặc định script sao profile Chrome hàng ngày, nghỉ 15 giây giữa hai lần đăng ký, rồi đối chiếu toàn bộ Excel.

Khi tạo nhiều tài khoản, chuẩn bị vài profile và đăng nhập Google trên từng profile một lần:

```text
.\register-dhqg\prepare-chrome-profiles.ps1 -Count 3
.\register-dhqg.ps1 -ChromeProfiles "$env:LOCALAPPDATA\sv5t-chrome-profiles" -Pause 35 -BatchSize 1 -CaptchaRetries 5 -RefreshChromeProfile
```

Gọi Python khi cần cờ không có trên script PowerShell:

```text
.\.venv\Scripts\python.exe register-dhqg\register.py --data register-dhqg\data.xlsx --limit 1
.\.venv\Scripts\python.exe register-dhqg\register.py --validate
.\.venv\Scripts\python.exe register-dhqg\register.py --fill-existing
```

| Tham số | Ý nghĩa |
|---------|---------|
| `--use-chrome-profile` | Dùng bản sao profile Chrome. Script PowerShell bật cờ này trừ khi có `-FreshChrome` |
| `--chrome-profiles` | Thư mục chứa nhiều profile, mỗi thư mục con một tài khoản Google |
| `--pause` | Số giây nghỉ giữa hai lần đăng ký |
| `--batch-size` | Số tài khoản trên một profile trước khi đổi profile. Mặc định 7 |
| `--captcha-retries` | Số lần thử lại khi gặp reCAPTCHA. Mặc định 5 |
| `--refresh-chrome-profile` | Sao lại cookie từ Chrome hàng ngày |
| `--fill-existing` | Đăng nhập tài khoản đã có và ghi lại hồ sơ, không mở Chrome |
| `--validate` | Chỉ đối chiếu, không đăng ký |
| `--status` | Chỉ xử lý email có trạng thái này ở cuối `validate.log` |
| `--workers` | Số luồng đối chiếu |

## Kết quả

`register.log`: `created`, `skipped`, `invalid_data`, `signup_error`, `captcha_error`, `profile_error`.

`validate.log`: `ok`, `missing_account`, `missing_profile`, `mismatch`.
