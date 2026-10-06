# Submission readiness audit

Audit date: 2026-10-04  
Official requirements: <https://vlsp.org.vn/vlsp2026/eval/mt_challenge>

## Kết luận

Code, config, tài liệu và quy trình đóng gói đã sẵn sàng. Chưa thể tạo file nộp
cuối vì repo không chứa hai `best_model` adapter từ Kaggle, và máy hiện tại chưa
có Docker daemon/CUDA runtime đang hoạt động để build và kiểm thử image thật.

## Đã hoàn thành và kiểm tra

- [x] Dataset/config mặc định đã chuyển hoàn toàn sang v3; config v2 cũ đã bỏ.
- [x] Cả EN→VI và VI→EN dùng đúng base model và revision đã pin.
- [x] Decoding cuối khóa ở `longer110` (EN→VI) và `beam4longer` (VI→EN).
- [x] Service nhận UTF-8 Markdown, có endpoint chung và endpoint từng chiều.
- [x] Bash wrapper nhận đúng ba đối số và ghi output atomically.
- [x] Docker runtime bật Hugging Face/Transformers offline và chạy non-root.
- [x] Script merge cuối chỉ dùng base model local; không cần Internet.
- [x] Validator kiểm tra direction/model/revision, SHA-256 inventory, safetensors
  và tổng số tham số dưới 3B.
- [x] Build-context ZIP dùng dấu `/`, bỏ cache Python và tạo MD5.
- [x] Script export tạo một gói phát hành chứa image, wrapper, README và checksum.
- [x] Có smoke inputs cho headings, lists, tables, số và viện dẫn pháp lý.
- [x] Full test suite: 77 passed, 1 optional cached-tokenizer integration skipped.
- [x] Kaggle package dry-run: 82 entries, đủ dataset/config/notebook v3.
- [x] Submission package dry-run: 42 entries, đúng model layout, không có cache.
- [x] README và data-preparation guide đã phản ánh dataset/quy trình hiện tại.

## Gate bắt buộc còn mở

- [ ] Tải `best_model` EN→VI từ run đã chốt.
- [ ] Tải `best_model` VI→EN từ run đã chốt.
- [ ] Chạy `scripts/prepare_submission.ps1` với hai adapter và hai base model local.
- [ ] Lưu `outputs/merged/validation_report.json` và kiểm tra tổng tham số thực.
- [ ] Build CUDA Docker image từ đúng build-context ZIP vừa sinh.
- [ ] Smoke-test cả hai chiều bằng `submission/smoke_test.sh`.
- [ ] Chạy lại image khi external network bị tắt, kiểm tra log không gọi Hub/API.
- [ ] Đo runtime, throughput và peak VRAM trên tài liệu dài đại diện.
- [ ] Export đúng image đã test bằng `submission/export_image.sh`.
- [ ] Upload gói `.tar.gz` và `.md5` vào link công khai, tải lại và verify MD5.
- [ ] Kiểm tra thông báo cuối của ban tổ chức về endpoint, port, GPU, timeout,
  giới hạn dung lượng và định dạng artifact được nhận.

## Không đưa vào image cuối

Dataset train/dev/test, notebook, optimizer checkpoint, LoRA adapter rời, log,
prediction có reference, cache Python và virtual environment đều nằm ngoài build
context cuối. Image chỉ chứa source inference, hai config và hai merged model.
