# VLSP 2026 Legal MT submission

Thư mục này chứa lớp triển khai cho cả EN→VI và VI→EN. Docker image dùng merged
models local, bật chế độ Hugging Face/Transformers offline và không gọi API ngoài.

Nguồn yêu cầu chính thức, kiểm tra ngày 2026-10-04:
<https://vlsp.org.vn/vlsp2026/eval/mt_challenge>.

## 1. Ghép và kiểm tra hai model cuối

Tải `best_model` của từng chiều từ hai run Kaggle đã chốt, cùng hai snapshot base
model đúng revision. Trên Windows chạy từ gốc repo:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/prepare_submission.ps1 `
  -En2ViAdapterDir D:\models\en2vi_best_model `
  -Vi2EnAdapterDir D:\models\vi2en_best_model `
  -En2ViBaseModelDir D:\models\vinai-translate-en2vi-v2 `
  -Vi2EnBaseModelDir D:\models\vinai-translate-vi2en-v2
```

Script không truy cập mạng. Nó merge LoRA bằng base model local, kiểm tra file và
SHA-256 trong `merge_manifest.json`, xác nhận model/revision/direction, đếm tham
số từ safetensors, yêu cầu tổng dưới 3B, rồi tạo:

```text
outputs/merged/en2vi/
outputs/merged/vi2en/
outputs/merged/validation_report.json
dist/VLSP2026_MT_build_context.zip
dist/VLSP2026_MT_build_context.zip.md5
```

Muốn chỉ đóng gói hai merged model đã có:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/package_submission.ps1 `
  -En2ViModelDir outputs/merged/en2vi `
  -Vi2EnModelDir outputs/merged/vi2en
```

## 2. Build và chạy Docker

Giải nén đúng build-context ZIP trên máy Linux có Docker/NVIDIA runtime:

```bash
docker build -f submission/Dockerfile -t vlsp2026-legal-mt:latest .
docker run --gpus all --rm -p 8000:8000 \
  --name vlsp2026-mt vlsp2026-legal-mt:latest
```

Ở terminal khác, chạy smoke test hai chiều:

```bash
bash submission/smoke_test.sh http://127.0.0.1:8000 dist/smoke
```

Wrapper chính nhận đúng ba đối số:

```bash
bash submission/translate.sh http://127.0.0.1:8000 input.md output.md
```

Service hỗ trợ `POST /translate`, `/translate/en2vi`, `/translate/vi2en`. Với
endpoint chung, service tự phát hiện ngôn ngữ; có thể ép chiều bằng biến
`TRANSLATION_DIRECTION=en2vi` hoặc `vi2en`. Input/output là UTF-8 Markdown.

## 3. Kiểm tra offline

Khởi động một container mới với external network bị vô hiệu hóa và chạy smoke
test từ container/client trong cùng mạng Docker nội bộ. Xác nhận:

- `/health` trả về trạng thái sẵn sàng của cả hai model;
- cả hai output không rỗng và đọc được UTF-8;
- headings, lists, tables, số và viện dẫn pháp lý còn hợp lý;
- log không có request tới Hugging Face hoặc API ngoài;
- đo runtime, throughput và peak VRAM trên tài liệu dài đại diện.

## 4. Xuất đúng image đã kiểm thử

```bash
bash submission/export_image.sh vlsp2026-legal-mt:latest dist
```

File nộp chính là `dist/vlsp2026_legal_mt_submission.tar.gz`; nó chứa image
archive, `translate.sh`, README và `MD5SUMS`. File
`vlsp2026_legal_mt_submission.tar.gz.md5` dùng để kiểm tra gói sau khi tải lại:

```bash
cd dist
md5sum -c vlsp2026_legal_mt_submission.tar.gz.md5
tar -xzf vlsp2026_legal_mt_submission.tar.gz
md5sum -c MD5SUMS
```

Upload hai file trên vào nơi tải công khai không cần đăng nhập. Tự tải lại và
kiểm tra cả checksum ngoài lẫn checksum thành phần trước khi gửi link.

## 5. Việc phải xác nhận trước hạn nộp

Trang hiện tại chưa công bố schema HTTP cuối, endpoint, port, GPU/runtime,
timeout, giới hạn dung lượng và việc nhận image archive hay build context. Kiểm
tra lại trang challenge và email ban tổ chức; nếu protocol thay đổi chỉ cần sửa
service/wrapper và build lại image, không cần train lại.
