# reCAPTCHA trên youth.vnuhcm.edu.vn

Trang đăng ký `/web/signup` dùng Google reCAPTCHA v3, action `signup`. Script của trang tự gọi `grecaptcha.execute` khi bấm Đăng ký. Server Odoo từ chối nếu token thiếu, hết hạn, hoặc bị Google chấm điểm thấp. Lỗi thường gặp là `The reCaptcha token is invalid.` và `Suspicious activity detected` / `Google reCaptcha phát hiện hoạt động đáng ngờ.`

reCAPTCHA chỉ chặn bước tạo tài khoản. Đăng nhập và ghi hồ sơ `nominee.info` đi bằng form login cùng JSON-RPC, không qua reCAPTCHA.

## Cách đã thử

Request HTTP thuần không có token do trình duyệt tạo, nên bị từ chối ngay.

Playwright và patchright mở Chrome mới, hoặc Chrome có cờ automation, vẫn bị Google đánh dấu. Bản sao profile gắn bằng `launch_persistent_context` cũng bị, vì Chrome nhận ra phiên do công cụ tự động mở.

Chrome 155 không cho remote debugging trên đúng thư mục profile mặc định (`DevTools remote debugging requires a non-default data directory`). Playwright 1.63 cũng không gắn được vào Chrome 155 qua cổng debug.

## Cách đang dùng

1. Đóng Chrome của người dùng.
2. Sao các phần profile Default (cookie, `Local Storage`, `Preferences`, lịch sử) sang `%LOCALAPPDATA%\sv5t-chrome-profile`.
3. Mở Chrome thật với thư mục đó và `--remote-debugging-port=9333`.
4. Điều khiển tab bằng Chrome DevTools Protocol: mở `/web/signup`, điền form, bấm Đăng ký.
5. Để chính trang web gọi `grecaptcha.execute`. Tool không tự tạo token và không gọi API giải captcha.

Cookie và lịch sử của profile thật giúp những lượt đầu được điểm đủ cao. Khi tạo liên tiếp nhiều tài khoản trên cùng một trình duyệt và cùng một IP, Google hạ điểm. Từ lúc đó mỗi lượt trả về "hoạt động đáng ngờ". Script thử lại một lần sau 30 giây rồi ghi `captcha_error` và chuyển sang dòng kế tiếp.

Vì mỗi lượt thất bại mất khoảng nửa phút cho lần thử và lần chờ, đoạn cuối danh sách chạy chậm. Đó là thời gian chờ reCAPTCHA, không phải thời gian ghi hồ sơ.

## Nhiều tài khoản Google

reCAPTCHA v3 không gắn theo email Google đang đăng nhập trên Chrome, mà theo hành vi trình duyệt, cookie và địa chỉ IP. Mở nhiều Chrome song song trên cùng một laptop vẫn dùng chung một IP, nên thường không giúp “bypass” và còn dễ bị chặn hơn.

Cách tool hỗ trợ: luân phiên **nhiều user-data-dir Chrome** (mỗi thư mục một phiên Google đã vào `youth.vnuhcm.edu.vn` trước đó), đăng ký tuần tự với `--pause` và `--batch-size`. Chuẩn bị thư mục bằng `register-dhqg/prepare-chrome-profiles.ps1`, rồi chạy:

```text
.\register-dhqg.ps1 -ChromeProfiles "$env:LOCALAPPDATA\sv5t-chrome-profiles" -Pause 35
```

Hoặc gọi trực tiếp `register.py` khi cần chống reCAPTCHA mạnh hơn:

```text
python register-dhqg/register.py --use-chrome-profile ^
  --chrome-profiles "%LOCALAPPDATA%\sv5t-chrome-profiles" ^
  --pause 35 --batch-size 1 --captcha-retries 5 --refresh-chrome-profile
```

- **`--batch-size 1`**: mỗi tài khoản xong thì đổi profile Chrome.
- **`--captcha-retries 5`**: thử lại nhiều lần, chờ dài hơn giữa các lần.
- **`--refresh-chrome-profile`**: sao lại cookie từ Chrome hàng ngày (giúp điểm v3).
- Trước khi chạy: vào `/web/login` vài giây (warm-up) rồi mới mở `/web/signup`.

Tool **không** dùng dịch vụ giải captcha hay API bên thứ ba. Chỉ dùng Chrome thật để trang web tự gọi `grecaptcha.execute`.

## Sau khi đã có tài khoản

Ghi hồ sơ đăng nhập bằng `/web/login`, rồi `search_read` / `write` / `create` trên model `nominee.info`. Bước này chạy được nhiều luồng và không đụng reCAPTCHA. Kiểm tra đối chiếu với Excel cũng đi đường này.

Nếu tài khoản đã tồn tại, bước đăng ký chỉ ghi `skipped` và không ghi lại hồ sơ. Muốn cập nhật hồ sơ của những tài khoản đó thì dùng `--fill-existing`.
