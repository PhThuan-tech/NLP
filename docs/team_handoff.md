# Hướng dẫn bàn giao và kế thừa dự án

Tài liệu này là điểm bắt đầu cho thành viên mới. Pipeline chính chạy trên
Google Colab; không cần chép virtual environment từ Windows vào ZIP.

## 1. Trạng thái đã chốt

| Thành phần | Giá trị dùng chung |
|---|---|
| Dataset training | `legal_envi_clean_seed67_v2` |
| Thư mục dataset | `artifacts/processed_clean_seed67_v2/` |
| Cách chia | `sklearn.model_selection.train_test_split` ở cấp duplicate-group |
| Split seed | `67` |
| Training/data seed | `67` |
| Dev ratio | `0.10` |
| Model EN→VI | `vinai/vinai-translate-en2vi-v2` |
| Model VI→EN | `vinai/vinai-translate-vi2en-v2` |
| Baseline nên chạy trước | zero-shot, sau đó LoRA |
| Nền tảng chính | Google Colab GPU |

Dataset v2 kế thừa nguyên split sklearn seed 67 từ v1 rồi loại source=target,
duplicate trong split, source/target leakage giữa train–dev và cặp có dấu hiệu
đảo ngôn ngữ. V2 không chia lại document.

Dev chỉ dùng cho metric, early stopping và chọn checkpoint. Public test không
được dùng để train, chọn hyperparameter hoặc chọn checkpoint.

## 2. Cấu trúc cần biết

```text
configs/vinai/                    cấu hình 2 chiều × 3 chế độ
artifacts/processed_clean_seed67_v2/
                                  dataset duy nhất dùng để train/evaluate
notebooks/02_vinai_colab.ipynb    giao diện chạy chính
src/data/prepare.py               tạo structural dataset v1 từ CSV gốc
src/data/finalize.py              tạo clean dataset v2/v3
src/vinai_baseline/               train, evaluate, metric và so sánh run
tests/                            test dữ liệu, config, leakage và resume
docs/                             tài liệu kỹ thuật và quy ước nhóm
scripts/package_colab.ps1         tạo ZIP tối thiểu, không kèm môi trường local
```

`artifacts/processed_sklearn_seed67/` là dataset cha để audit/tái tạo v2, không
dùng trực tiếp trong config training. `notebooks/01_dataset_eda.ipynb` phục vụ
khám phá dữ liệu, không phải notebook training.

## 3. Kiểm tra trước khi bàn giao

Từ thư mục gốc dự án:

```powershell
python -m unittest discover -s tests -v
python -m src.vinai_baseline.cli --help
```

Không tiếp tục nếu test checksum, dataset contract hoặc leakage thất bại.

## 4. Tạo ZIP đúng cách

Không nén `.git`, `NLP_venv`, `outputs`, checkpoint hay cache. Chạy:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/package_colab.ps1
```

Script tạo `NLP_colab.zip` chỉ gồm code, config, tài liệu, test, notebook và
dataset v2 cần thiết. Nếu file ZIP cùng tên đã tồn tại, script sẽ thay file đó.

## 5. Chạy trên Google Colab

1. Mở `notebooks/02_vinai_colab.ipynb` trên Colab.
2. Chọn **Runtime → Change runtime type → GPU**.
3. Chạy cell GPU và mount Google Drive.
4. Upload `NLP_colab.zip` tại cell upload.
5. Notebook cài stack đã khóa từ `requirements-training-colab.txt`.
6. Đặt `MEMBER_TAG` bằng tên riêng viết thường, không dấu.
7. Đặt `EXPERIMENT_TAG` mô tả đúng một thay đổi đang thử.
8. Giữ `RUN_FULL=False`, chạy audit và smoke test trước.
9. Chỉ khi smoke thành công mới đặt `RUN_FULL=True`.

Mỗi run có ID riêng:

```text
<dataset>__<direction>__<mode>__seed<seed>__<member>__<experiment>__<UTC timestamp>
```

### Run E0: zero-shot

```python
DIRECTION = "en2vi"       # hoặc vi2en
MODE = "zero_shot"
RUN_FULL = False           # smoke trước
MEMBER_TAG = "ten_thanh_vien"
EXPERIMENT_TAG = "e0_zero_shot"
RUN_ID_OVERRIDE = ""
RESUME_FROM_CHECKPOINT = ""
```

Sau smoke, đặt `RUN_FULL=True` và chạy cell full. Zero-shot phải hoàn thành trên
toàn dev trước khi kết luận LoRA có cải thiện.

### Run E1: LoRA

```python
MODE = "lora"
RUN_FULL = False
EXPERIMENT_TAG = "e1_lora_default"
RUN_ID_OVERRIDE = ""
RESUME_FROM_CHECKPOINT = ""
```

Smoke LoRA gồm cả save và reload adapter. Chỉ chạy full khi
`reports/reload_smoke.json` có `status: passed`.

Profile Colab/T4 chung của nhóm dùng train batch 4, accumulation 4 (effective
batch 16), eval batch 16 và subset cố định 128 mẫu để chọn checkpoint mỗi epoch.
Sau training vẫn chạy toàn bộ dev đúng một lần. Không tự đổi các giá trị này
giữa thành viên; nếu T4 báo OOM, lưu log và tạo profile/config mới thay vì sửa
âm thầm config baseline.

### Run E2: full fine-tuning

Chỉ chạy sau khi E0 và E1 đã hoàn tất. Đổi `MODE="full"`, dùng
`EXPERIMENT_TAG="e2_full_default"` và tạo run mới. Full fine-tuning tốn VRAM,
thời gian và dung lượng checkpoint lớn hơn LoRA; không dùng kết quả E2 để thay
thế E0/E1 nếu chưa chạy trên cùng dev set.

### Resume sau khi Colab ngắt

```python
RUN_FULL = True
RUN_ID_OVERRIDE = "<đúng tên thư mục run cũ>"
RESUME_FROM_CHECKPOINT = "last"
```

Không đổi dataset, direction, mode, seed hay hyperparameter khi resume. Code sẽ
từ chối checkpoint ngoài thư mục run và từ chối ghi đè run đã hoàn thành.
Notebook tự bỏ qua smoke test khi resume.

## 6. Cách xác nhận một run hợp lệ

Run chỉ hoàn tất khi có:

```text
run_manifest.json
resolved_config.json
reports/validation_metrics.json
reports/validation_metrics_by_category.json
predictions/validation_predictions.jsonl
```

LoRA/full còn phải có `best_model/`, `reports/reload_smoke.json` và
`reports/checkpoint_validation_subset.json`. Số dòng prediction phải bằng
`evaluated_records` trong validation metrics.

Tối thiểu phải giữ lại `resolved_config.json`, `run_manifest.json`, `reports/`,
`predictions/validation_predictions.jsonl` và `best_model/` đối với LoRA/full.
Chỉ giữ checkpoint cần resume; checkpoint trung gian không còn dùng có thể bỏ
sau khi run đã hoàn thành và được sao lưu.

Đọc tối thiểu các chỉ số: BLEU, chrF++, output rỗng, length ratio, bảo toàn số,
bảo toàn Điều/Khoản/Điểm, runtime và peak VRAM. Luôn đọc thêm các mẫu
`source → prediction → reference`; metric smoke không dùng để kết luận chất
lượng.

## 7. So sánh kết quả giữa thành viên

Sau khi tải các thư mục run về cùng máy:

```powershell
python -m src.vinai_baseline.compare_runs `
  outputs/run_zero_shot `
  outputs/run_lora `
  --output outputs/comparison.csv
```

Công cụ chỉ cho so sánh khi cùng dataset ID, direction, base model/revision,
dev checksum, số mẫu, generation config, mã metric, Transformers và SacreBLEU.
Không so smoke với full run.

## 8. Quy tắc khi mở rộng

- Chỉ thay một yếu tố trong mỗi thí nghiệm.
- Không sửa nội dung JSONL nhưng giữ nguyên dataset ID.
- Thay preprocessing/filter phải tạo thư mục và dataset ID mới.
- LaBSE là tùy chọn trong `src.data.finalize`; chỉ bật sau khi audit threshold
  thủ công và phải tạo v3, không ghi đè v2.
- Không dùng public test để train, early stopping hoặc chọn hyperparameter.
- Không commit output, checkpoint, cache, token hoặc virtual environment.
- Giữ nguyên model revision, seed và generation config khi so E0/E1.
- Không sửa config dùng chung chỉ để chạy thử cá nhân; tạo config mới hoặc dùng
  CLI override.
- Chỉ merge code khi unit test và smoke test thành công.
- Không dùng chung output directory giữa hai thành viên hoặc hai giả thuyết.

## 9. Ma trận thí nghiệm và cách chốt kết quả

Chạy riêng cho `en2vi` và `vi2en`:

| ID | Mode | Dataset | Seed | Mục đích |
|---|---|---|---:|---|
| E0 | zero-shot | `legal_envi_clean_seed67_v2` | 67 | Mốc pretrained |
| E1 | LoRA | `legal_envi_clean_seed67_v2` | 67 | Baseline thích nghi domain |
| E2 | full | `legal_envi_clean_seed67_v2` | 67 | Đối chiếu với LoRA |

Không chốt bằng một “accuracy” duy nhất. Báo cáo BLEU, chrF++, output rỗng,
length ratio, F1 bảo toàn số, F1 bảo toàn viện dẫn, runtime và peak VRAM. Ngoài
metric tổng, phải đọc mẫu theo category, đặc biệt là phủ định, nghĩa vụ, điều
kiện, số liệu và Điều/Khoản/Điểm.

Chỉ sau E0–E2 mới thử context/HAN, glossary hoặc semantic dataset v3. Mỗi thay
đổi đó là một nhánh thí nghiệm mới, không thay âm thầm baseline.

## 10. Lỗi thường gặp

### Labels và logits khác chiều

Nếu gặp lỗi dạng `index [batch, target_length, 1]` lớn hơn logits
`[batch, source_length, vocab]`, không tự giảm target xuống 128. Kiểm tra phiên
bản code có tạo `decoder_input_ids` từ labels trong
`DynamicSeq2SeqCollator`. Baseline hiện tại giữ max source/target 512, audit
đoạn dài trước và dùng dynamic padding.

### PEFT báo `incompatible version of torchao`

Một số Colab runtime cài sẵn `torchao 0.10.0`, nhưng PEFT 0.21 chỉ hỗ trợ bản
trên 0.16. Baseline không dùng TorchAO/quantization; cell cài dependency trong
`02_vinai_colab.ipynb` sẽ tự gỡ bản cũ trước khi chạy LoRA. Sau khi cập nhật
notebook, nên tạo runtime mới và chạy tuần tự từ đầu.

## 11. Tài liệu chi tiết

- `docs/vinai_baseline_training.md`: kiến trúc và toàn bộ pipeline model.
- `docs/data_preparation.md`: cách tạo, audit và version dữ liệu.
- `docs/next_steps.md`: roadmap sau baseline.
