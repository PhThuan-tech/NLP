# Chuẩn bị dataset v3

## Dataset được dùng

Training hiện chỉ dùng artifact frozen:

```text
artifacts/processed_clean_semantic_seed67_v3/
```

Manifest phải có:

- `dataset_id = legal_envi_clean_semantic_seed67_v3`
- `semantic_audit_only = false`
- split seed `67`, đơn vị split là `duplicate_group`
- alignment threshold `0.75`
- semantic model `sentence-transformers/LaBSE`, revision `836121a`
- semantic threshold `0.70`

Số record cuối:

| Split | EN→VI | VI→EN | Rejected khi freeze |
|---|---:|---:|---:|
| Train | 27.756 | 27.756 | 1.948 |
| Dev | 2.783 | 2.783 | 193 |
| Public test | 1.837 | 1.837 | 121 |

Public test có reference để báo cáo cuối nhưng không thuộc train/dev.

## Ba giai đoạn

1. **Parent v3**: chuẩn hóa tài liệu, nhóm duplicate, split theo document/group,
   segment theo giới hạn tokenizer và loại lỗi alignment cơ bản.
2. **Semantic audit**: LaBSE chấm cosine similarity cho từng cặp; artifact audit
   giữ toàn bộ score để duyệt ngưỡng. Cảnh báo chiều dài 256 của LaBSE cho biết
   embedding bị truncation; nó không làm hỏng tokenizer training 448/512 token.
3. **Freeze**: lọc score dưới `0.70`, khóa manifest/hash và sinh sáu config trong
   `configs/generated_v3/`. Freeze dùng lại score, không chạy LaBSE lần hai.

Notebook chuẩn cho toàn bộ quy trình là
`notebooks/04_v3_builder_kaggle.ipynb`. Sau khi freeze, tải artifact về và giữ
nguyên tên thư mục; không chỉnh JSONL bằng tay.

## Tạo parent trên local

Khi cần dựng lại từ dữ liệu gốc:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/prepare_v3.ps1
```

Sau đó dùng notebook 04 trên Kaggle để audit/freeze. Cần attach snapshot LaBSE
vào Kaggle Input nếu Internet bị tắt. Model VinAI chỉ cần cho bước segment/token
audit; bước training dùng hai snapshot riêng đã pin revision.

## Đóng gói dataset frozen cho Kaggle

```powershell
powershell -ExecutionPolicy Bypass -File scripts/package_colab.ps1 `
  -DatasetPath artifacts\processed_clean_semantic_seed67_v3 `
  -OutputPath NLP_v3_frozen_offline.zip
```

Script chỉ đóng gói dataset frozen, code, config, notebook và tài liệu cần thiết;
không đưa cache Python vào ZIP. Hai base model offline được chuẩn bị riêng để
không phải tạo lại gói project mỗi lần.

## Kiểm tra contract

```powershell
python -m unittest tests.test_data_preparation tests.test_vinai_baseline -v
```

Các invariant quan trọng:

- train/dev không trùng source hoặc target sau chuẩn hóa;
- không có identity pair hay duplicate pair trong split;
- cả hai chiều dùng cùng document split;
- config, manifest và file JSONL cùng dataset ID/seed;
- file public test bị từ chối nếu được đặt làm training file;
- artifact audit-only không thể được dùng để train.

## Quy tắc tái lập

- Không ghi đè artifact frozen; tạo dataset ID mới khi đổi threshold/split/code.
- Không trộn file v2 với config v3.
- Ghi lại revision model, hash manifest, seed và config trong mỗi run.
- Chọn checkpoint và decoding trên dev. Chạy public test sau khi lựa chọn đã chốt.
