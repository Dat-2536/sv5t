# SV5T Toolkit trên trình duyệt

Làm các việc ảnh và PDF ngay trong trình duyệt. File được xử lý local, không tải lên máy chủ.

- Ảnh sang PDF: mỗi ảnh một file, hoặc gộp nhiều ảnh vào một PDF. Khổ theo ảnh hoặc A4.
- Gộp PDF, kèm ảnh nếu cần.
- Nén ảnh theo dung lượng tối đa hoặc theo chất lượng.
- Chỉnh dung lượng vào khoảng tối thiểu và tối đa, có thể pad metadata nếu ảnh quá nhẹ.
- Xoá watermark ảnh thẻ myBk, hoặc tô vùng rồi để model vẽ lại.

## Mở

Mở `web-tools/index.html` bằng trình duyệt. Một số bước dùng WebAssembly nhiều luồng nên Chrome ổn định hơn nếu mở qua một máy chủ tĩnh:

```text
.\.venv\Scripts\python.exe -m http.server 8080 --directory web-tools
```

Rồi vào http://localhost:8080/.

Model xoá vùng tô nằm ở `models/migan_pipeline_v2.onnx`. Thư viện PDF, ZIP, OpenCV và ONNX Runtime nằm trong `vendor/`.

## Đưa lên trang tĩnh

`deploy.ps1` copy riêng thư mục web sang repo GitHub Pages `sv5t-pdf-tools` và có thể deploy Vercel. Script không mang dữ liệu của repo này.

```text
.\web-tools\deploy.ps1 -Target github
.\web-tools\deploy.ps1 -Target vercel
```

Lần cập nhật GitHub Pages, script đẩy nhánh `main` của repo web bằng `--force`. Chỉ chạy khi đúng là muốn thay toàn bộ bản đang public.