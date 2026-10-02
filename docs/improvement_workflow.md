# Quy trình cải thiện baseline sau E0/E1

Trước khi áp dụng cải tiến tiếp theo, chạy quy trình sửa language control tại
[`language_recovery.md`](language_recovery.md): zero-shot 256 → kiểm tra adapter cũ
→ smoke/retrain LoRA V2. Kết quả lặp của run ngày 01/10 chưa phải baseline hợp lệ.

Đây là quy trình chính sau khi đã có kết quả EN→VI Zero-shot và LoRA trên
`legal_envi_clean_seed67_v2`. Không ghi đè v2 và không sửa document split.
Split seed và training seed tiếp tục là `67`.

## Chạy ngay với dataset v2

`artifacts/processed_clean_seed67_v2` là baseline đã freeze và có thể dùng ngay để
kiểm tra các thay đổi của pipeline mà không cần chạy LaBSE. Trong notebook Kaggle,
giữ phần semantic v3 ở trạng thái tắt và chọn:

```python
RUN_V3_SEMANTIC_AUDIT = False
SEMANTIC_THRESHOLD = None
DATASET_PROFILE = "v2"
DIRECTION = "en2vi"  # hoặc vi2en
MODE = "lora"        # zero_shot | lora | full
CONFIG_OVERRIDE = ""
RUN_FULL = False      # smoke trước
```

Notebook tự chọn `configs/vinai/<direction>_<mode>.json`, xác minh dataset ID,
manifest, split seed 67 và training seed 67. Khi smoke thành công mới đặt
`START_FULL_NOW=True` ở cell Full run. Kết quả v2 là mốc đối chứng; không so trực
tiếp điểm v2 và v3 như thể chỉ có model thay đổi vì dữ liệu validation khác nhau.

```text
generation sweep trên adapter hiện tại
        ↓
token-aware parent dataset
        ↓
semantic audit (chưa loại theo threshold)
        ↓
nhóm duyệt mẫu và chốt threshold
        ↓
freeze dataset v3 → sinh config v3
        ↓
Zero-shot v3 → LoRA v3
        ↓
merge adapter → document inference
```

## 1. Generation sweep không train lại

Giải nén run LoRA và trỏ `--saved-model-dir` vào `best_model`. Lệnh mặc định
chạy bốn cấu hình trên 256 mẫu cố định, phân bổ theo category và giới hạn số
segment lấy từ một document:

```powershell
python -m src.vinai_baseline.sweep_cli `
  --config configs/vinai/en2vi_lora.json `
  --saved-model-dir path/to/lora_run/best_model `
  --output-dir outputs/sweeps/en2vi_lora_v2 `
  --samples 256 `
  --batch-size 16
```

Mỗi candidate có prediction và metric riêng. `sweep_summary.json` chỉ đánh dấu
candidate hợp lệ khi không có output rỗng, tỷ lệ output dài hơn reference trên
3 lần không vượt ngưỡng, repeated-trigram rate không vượt ngưỡng và không có
quá nhiều output bị một token duy nhất chiếm trên 20%. Nếu không
candidate nào hợp lệ, report ghi `recommendation_used_fallback=true`; không coi
fallback là cấu hình đã chốt.

Candidate riêng có định dạng:

```text
--candidate ten:beams:length_penalty:repetition_penalty:no_repeat_ngram:max_new_tokens
--candidate safe_c:2:0.6:1.10:4:448
```

Dùng `none` ở trường cuối để giữ `max_length` của config.

## 2. Tạo parent dataset theo token

Stage này đọc lại CSV gốc, giữ `train_test_split` document-level seed 67 và tạo
chunk không quá 448 token theo tokenizer VinAI đã khóa revision:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/prepare_v3.ps1 -Stage prepare
```

Tương đương trên Linux/Kaggle:

```bash
python -m src.data.prepare \
  --project-root . \
  --output-dir artifacts/processed_token448_seed67_v3_parent \
  --seed 67 \
  --dataset-version token448_seed67_v3_parent \
  --minimum-alignment-score 0.75 \
  --maximum-block-words 220 \
  --maximum-chunk-words 220 \
  --maximum-chunk-tokens 448 \
  --tokenizer-model vinai/vinai-translate-en2vi-v2 \
  --tokenizer-revision 1e47495b5dac16097b1d9e7b4133c27e1f40504f
```

Nếu một alignment đơn lẻ vẫn vượt 448 token, pipeline dừng thay vì âm thầm tạo
mẫu mà Trainer sẽ drop. Khi đó cần cải thiện logical-block splitting hoặc giảm
`maximum_block_words`; không chuyển sang truncate.

Để đưa parent dataset lên Kaggle chạy semantic audit:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/package_colab.ps1 `
  -DatasetPath artifacts\processed_token448_seed67_v3_parent `
  -OutputPath NLP_v3_parent.zip
```

Sau khi freeze, đóng gói lại với `-DatasetPath
artifacts\processed_clean_semantic_seed67_v3` để train.

## 3. Semantic audit trước khi lọc

Cài dependency semantic và chấm toàn bộ cặp. Stage audit không loại theo cosine
threshold:

```powershell
pip install -r requirements-semantic.txt
powershell -ExecutionPolicy Bypass -File scripts/prepare_v3.ps1 -Stage audit
```

LaBSE revision mặc định trong script được khóa ở `836121a`. Manifest ghi model
revision và phiên bản `sentence-transformers`. Đọc:

```text
artifacts/processed_semantic_audit_seed67_v3/semantic_audit.json
```

Report có phân vị, bin count, năm mẫu điểm thấp nhất và tỷ lệ input bị LaBSE
truncate cho từng category/split. LaBSE giữ giới hạn chính thức 256 token; pipeline
không âm thầm nâng giới hạn embedding. Nếu `truncated_rate` đáng kể, giảm kích
thước chunk và tạo lại parent dataset trước khi chọn threshold.
Manifest audit có `semantic_audit_only=true`; runner và công cụ sinh config sẽ
từ chối dùng dataset này để train/evaluate vì chống rò rỉ chỉ hoàn tất sau freeze.
Nhóm cần kiểm tra thủ công các vùng `<0.60`, `0.60–0.65`, `0.65–0.70`,
`0.70–0.72`, `0.72–0.75` và `0.75–0.80`, đặc biệt ở
`Vi_pham_hanh_chinh`. Cosine score không phải xác suất đúng.

Trên Kaggle/Linux chạy trực tiếp:

```bash
python -m src.data.finalize \
  --input-dir artifacts/processed_token448_seed67_v3_parent \
  --output-dir artifacts/processed_semantic_audit_seed67_v3 \
  --dataset-id legal_envi_semantic_audit_seed67_v3 \
  --split-seed 67 \
  --minimum-alignment-score 0.75 \
  --semantic-model sentence-transformers/LaBSE \
  --semantic-model-revision 836121a
```

Nếu dùng `notebooks/03_vinai_kaggle.ipynb`, upload `NLP_v3_parent.zip`. Kaggle
có thể tự giải nén Input; notebook hỗ trợ cả thư mục đã giải nén và file ZIP.
Trong phần **Tạo và duyệt dataset v3**, đặt
`RUN_V3_SEMANTIC_AUDIT=True`. Sau khi audit xong, tải
`/kaggle/working/semantic_audit_seed67_v3.zip` về để nhóm duyệt.

## 4. Freeze v3 bằng score đã audit

Ví dụ sau khi nhóm chốt `0.72`:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/prepare_v3.ps1 `
  -Stage freeze `
  -SemanticThreshold 0.72
```

Stage freeze đọc lại `semantic_similarity` đã lưu, không chạy LaBSE lần hai.
Dataset kết quả là `artifacts/processed_clean_semantic_seed67_v3`.
Train–dev overlap chỉ được loại ở stage freeze, sau khi dev đã qua semantic
threshold; vì vậy mẫu train không bị mất oan do trùng với một dev cuối cùng bị loại.
Trong notebook Kaggle, sau khi chốt threshold, đặt `RUN_V3_SEMANTIC_AUDIT=False`
và `SEMANTIC_THRESHOLD=<giá trị đã chốt>`. Cell sẽ freeze, sinh sáu config v3 và
tạo `processed_clean_semantic_seed67_v3.zip` trong Kaggle Output.

Lệnh tương đương trên Kaggle/Linux:

```bash
python -m src.data.finalize \
  --input-dir artifacts/processed_semantic_audit_seed67_v3 \
  --output-dir artifacts/processed_clean_semantic_seed67_v3 \
  --dataset-id legal_envi_clean_semantic_seed67_v3 \
  --split-seed 67 \
  --minimum-alignment-score 0.75 \
  --semantic-model sentence-transformers/LaBSE \
  --semantic-model-revision 836121a \
  --minimum-semantic-similarity 0.72 \
  --reuse-semantic-scores
```

Trước khi train phải kiểm tra:

- manifest có split seed 67;
- train/dev không overlap source hoặc target;
- token audit không drop mẫu nào;
- các cặp lệch đã biết không còn trong accepted segments;
- số mẫu bị loại theo category không mất cân đối bất thường.

## 5. Sinh sáu config v3

Dùng generation candidate đã thắng sweep thay cho các giá trị minh họa:

```powershell
python -m src.vinai_baseline.create_configs `
  --project-root . `
  --dataset-dir artifacts/processed_clean_semantic_seed67_v3 `
  --output-dir configs/generated_v3 `
  --learning-rate 0.00005 `
  --checkpoint-samples 256 `
  --length-penalty 0.8 `
  --repetition-penalty 1.1 `
  --max-new-tokens 448
```

Công cụ sinh đủ Zero-shot/LoRA/full cho hai chiều và đặt seed 67,
`overlength_policy=error`, LoRA LR `5e-5`, checkpoint subset 256 stratify theo
category và tối đa sáu segment mỗi document.

Trong notebook chạy Zero-shot v3 trước:

```python
CONFIG_OVERRIDE = "configs/generated_v3/en2vi_zero_shot.json"
```

Sau đó chạy LoRA:

```python
CONFIG_OVERRIDE = "configs/generated_v3/en2vi_lora.json"
```

Không so trực tiếp score v2 với v3 vì dev fingerprint đã thay đổi. Chỉ so
Zero-shot v3 và LoRA v3 trên cùng fingerprint.

## 6. Điều kiện chấp nhận LoRA v3

- BLEU và chrF++ tốt hơn Zero-shot cùng frozen dev.
- Output rỗng bằng 0.
- Length-ratio p95 và tỷ lệ trên 3 lần giảm rõ rệt.
- Number F1 và source-number F1 không suy giảm không giải thích được.
- Reference preservation và mã văn bản (`63/2025/QH15`, `15/2020/NĐ-CP`...)
  không suy giảm.
- Không còn output lặp nghiêm trọng trong error sample.
- Reload smoke pass.

Ba epoch vẫn là giới hạn mặc định. Chỉ tăng epoch nếu metric epoch cuối tiếp tục
cải thiện đồng thời trên quality và safety metrics.

## 7. Merge LoRA cho inference

```powershell
python -m src.vinai_baseline.merge_lora `
  --config configs/generated_v3/en2vi_lora.json `
  --adapter-dir path/to/run/best_model `
  --output-dir outputs/merged/en2vi_v3
```

`merge_manifest.json` ghi base model/revision và SHA-256 các file. Benchmark
adapter và merged model trên cùng input trước khi dùng bản merge.
`document_cli` tự nhận biết adapter (`adapter_config.json`) và model đã merge
(`config.json`). Khi truyền thư mục đã merge thì bỏ cờ `--merge-lora`.

## 8. Dịch document Markdown

```powershell
python -m src.vinai_baseline.document_cli `
  --config configs/generated_v3/en2vi_lora.json `
  --saved-model-dir path/to/run/best_model `
  --input input_document.md `
  --output translated_document.md `
  --report translated_document.report.json `
  --maximum-source-tokens 448 `
  --batch-size 8 `
  --merge-lora
```

Document inference chia ở blank line rồi sentence/word boundary, không truncate
source, bucket theo độ dài, phục hồi đúng thứ tự, dừng nếu output rỗng và xuất
chunk map/runtime report. Report còn so số heading, list item, blockquote, code
fence, link và dòng bảng giữa input/output để phát hiện hỏng cấu trúc. Đây là
validator cấu trúc cơ bản; trước submission vẫn cần kiểm tra thuật ngữ và Docker
offline.

## 9. Những việc không được tự động chốt

- Semantic threshold: cần audit thủ công.
- Generation winner: cần sweep trên GPU.
- Mở rộng LoRA sang `k_proj/out_proj/fc1/fc2`: chỉ thử sau E1-v3.
- Full fine-tuning: chỉ chạy khi LoRA v3 vượt Zero-shot và qua quality gate.
- HAN/context: chưa ưu tiên trước khi document baseline ổn định.
