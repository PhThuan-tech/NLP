# Trạng thái triển khai SPEC — 05/10/2026

Code và quy trình đánh giá đã được triển khai. **Chưa nghiệm thu đầy đủ SPEC**:
full-dev A/B/R0–R5, review pháp lý, placeholder survival và GPU/runtime còn chờ.
Không train lại, không thay adapter, không tái tạo frozen dataset. Config decoding
submission chính thức không đổi; pipeline mới đang tắt.

| Milestone | Đã thực hiện | Còn chờ nghiệm thu |
|---|---|---|
| M0 | Khám phá repo, snapshot baseline/taxonomy, probe 10 mẫu EOS/ngram thật | Full current-service R0 |
| M1 | Parser theo offset, reassembler, 3 placeholder formats; round-trip 2.783/2.783 dev | 200 dev markup units thật; frozen JSONL hiện không có |
| M2 | Token budget từ 27.756 train pairs; giữ cụm pháp lý/số/ngày | Ảnh hưởng chất lượng qua R2 full dev |
| M3 | Translator có EOS/cap provenance, validator, CLI A/B; CPU smoke A0–A4 | Paired-dev A/B đầy đủ |
| M4 | 72 glossary candidates pending; approved-only, domain, longest match, một vòng retry | Người dùng duyệt; hiệu quả R4/R5 |
| M5 | Service/CLI, report JSON+MD, fallback, ngân sách theo stage; adapter thật chạy smoke | Build/run Docker trên GPU và budget submission |
| M6 | Runner R0–R5, manual-review export, kiểm bằng chứng chốt; CPU smoke đủ 6 đường | Full dev, review 30 mẫu, quyết định deployment |

Kiểm tra local: 117 tests chạy, 116 passed, 1 optional integration test skipped.
Smoke model thật: 2 units OK, không SOURCE_KEPT, không fallback, giữ CRLF và
marker cấu trúc. Đây là kiểm chạy code, không chứng nhận chất lượng pháp lý.
SHA256 toàn bộ file frozen theo manifest và hai adapter đã được đối chiếu.
Chi tiết máy đọc: [implementation_status.json](implementation_status.json).

Probe 10 mẫu lỗi: [cutoff_cause_probe.md](cutoff_cause_probe.md).
Không gộp số liệu probe/smoke vào điểm toàn dev.

## Tiếp tục trên Kaggle

1. Upload `dist/NLP_inference_pipeline.zip`; Add Input thêm base VI→EN offline
   và wheelhouse đã dùng train. Không cần LaBSE hoặc builder/freeze.
2. Mở `notebooks/05_inference_pipeline_kaggle.ipynb`, GPU ON, Internet OFF.
3. Chạy theo thứ tự; duyệt `submission/resources/glossary_candidates.csv`.
4. Sau smoke, bật `RUN_FULL_ABLATION=True`; tải `NLP_inference_reports.zip`.
5. Rà soát report và 30 mẫu. Giữ submission ở đường cũ khi bằng chứng còn thiếu.

Hướng dẫn đầy đủ: [legal_inference_pipeline.md](../../docs/legal_inference_pipeline.md).
Việc thiếu markup dev và budget là giới hạn đã xác nhận; không tự đổi trạng thái
report hoặc bỏ gate để tuyên bố hoàn thành nghiệm thu.
