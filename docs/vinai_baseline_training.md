# VinAI Translate baseline: thiết kế, huấn luyện và hướng dẫn chạy

## 1. Phạm vi của baseline

Pipeline này triển khai hai mốc đầu tiên trong kế hoạch thí nghiệm:

- **A – Zero-shot:** đánh giá nguyên bản VinAI Translate v2 trên dev set.
- **B – Legal-adapted:** tiếp tục huấn luyện trên dữ liệu pháp luật đã được chia
  và căn chỉnh bằng LoRA hoặc full fine-tuning.

Hai chiều dịch dùng hai pretrained model riêng:

| Chiều | Model | Revision đã khóa |
|---|---|---|
| English → Vietnamese | `vinai/vinai-translate-en2vi-v2` | `1e47495...` |
| Vietnamese → English | `vinai/vinai-translate-vi2en-v2` | `4eb2219...` |

Revision là mã phiên bản cố định của model trên Hugging Face. Khóa revision giúp
hai lần chạy không vô tình nhận trọng số khác nếu nhánh `main` thay đổi. Model
dùng kiến trúc mBART và được phát hành với giấy phép AGPL-3.0; nhóm cần kiểm tra
lại điều khoản giấy phép trước khi đóng gói submission thương mại hoặc phân phối
Docker image.

HAN, glossary injection và context theo cross-reference chưa được trộn vào
baseline này. Tách riêng giúp trả lời rõ cải thiện đến từ domain fine-tuning hay
từ context/terminology.

## 2. Dữ liệu được sử dụng

Nguồn mặc định là:

```text
artifacts/processed_clean_seed67_v2/
├── segments_train_en2vi.jsonl
├── segments_train_vi2en.jsonl
├── segments_dev_en2vi.jsonl
├── segments_dev_vi2en.jsonl
├── document_splits.csv
└── manifest.json
```

Dataset v1 được chia bằng `sklearn.model_selection.train_test_split` ở cấp
document/duplicate-group, với `stratify=category` và `random_state=67`, trước
khi segmentation. Bước finalization xác định tạo v2, loại source=target, trùng
trong split, mọi source/target train trùng dev và các cặp có dấu hiệu đảo ngôn
ngữ. V2 giữ 18.316 segment train, 1.877 dev và 1.211 public test. Hai file theo
hai chiều chứa cùng cặp song ngữ nhưng đảo `source`/`target`.

Tạo lại v2 từ v1 (không ghi đè v1):

```bash
python -m src.data.finalize \
  --input-dir artifacts/processed_sklearn_seed67 \
  --output-dir artifacts/processed_clean_seed67_v2 \
  --dataset-id legal_envi_clean_seed67_v2
```

`src.data.finalize` cũng hỗ trợ LaBSE qua `--semantic-model` và
`--minimum-semantic-similarity`. Chỉ bật sau khi nhóm duyệt threshold và phải
tạo dataset ID/thư mục mới; không thay âm thầm v2 vì semantic filter sẽ làm đổi
benchmark.

Quy tắc sử dụng split:

- `train`: cập nhật trọng số hoặc LoRA adapter;
- `dev`: tính metric, early stopping và chọn checkpoint;
- `public_test`: chỉ đánh giá cuối, tuyệt đối không train hay chọn
  hyperparameter.

Code kiểm tra schema, `direction`, nội dung rỗng và `segment_id` trùng. Config
cũng từ chối file có `public_test` trong tên nếu file đó được gán làm train.

## 3. Kiến trúc code

```text
JSON config
    ↓
ExperimentConfig ── kiểm tra model, chiều dịch, split và hyperparameter
    ↓
JsonlCorpus ── schema validation ── TokenizerAuditor
    ↓                                      ↓
TranslationDataset                token_audit_*.json
    ↓
DynamicSeq2SeqCollator ── tokenize + dynamic padding
    ↓
VinAIModelFactory ── base mBART ── optional LoRA
    ↓
Seq2SeqTrainer ── checkpoint/early stopping/generation
    ↓
TranslationMetricSuite ── BLEU, chrF++, legal checks
    ↓
prediction + metric + manifest
```

Vai trò các file chính:

| File | Trách nhiệm |
|---|---|
| `src/vinai_baseline/config.py` | Dataclass cấu hình, validate và CLI override. |
| `src/vinai_baseline/data.py` | Đọc JSONL, kiểm tra schema, audit token, dataset và collator. |
| `src/vinai_baseline/modeling.py` | Tải đúng VinAI model/tokenizer, cấu hình generation và LoRA. |
| `src/vinai_baseline/metrics.py` | SacreBLEU, chrF++, độ dài, output rỗng, bảo toàn số và tham chiếu pháp lý. |
| `src/vinai_baseline/runner.py` | Điều phối audit/evaluate/train, checkpoint, prediction và manifest. |
| `src/vinai_baseline/cli.py` | Entry point thống nhất cho audit/evaluate/train/verify trên Colab. |
| `configs/vinai/*.json` | Cấu hình tái lập cho mỗi chiều và mỗi chế độ. |
| `tests/test_vinai_baseline.py` | Unit test không cần tải model/GPU. |

Thiết kế tách lớp giúp đổi model/config hoặc thêm context dataset sau này mà
không phải viết lại toàn bộ training loop.

## 4. Các chế độ thí nghiệm

### 4.1 Zero-shot

Không cập nhật trọng số. Đây là mốc E0 bắt buộc để biết fine-tuning có thực sự
cải thiện model hay không.

```bash
python -m src.vinai_baseline.cli evaluate \
  --config configs/vinai/en2vi_zero_shot.json
```

### 4.2 LoRA – khuyến nghị chạy đầu tiên

LoRA thêm các ma trận hạng thấp vào `q_proj` và `v_proj` của attention; base
model được đóng băng. Cấu hình khởi đầu là rank 16, alpha 32, dropout 0.05,
learning rate `1e-4`, effective batch size 16 và 3 epoch. Eval/save chạy cuối
mỗi epoch thay vì mỗi 250 optimizer step, giảm mạnh generation trên dev mà
không đổi cấu hình suy luận cuối.

Lợi ích: ít tham số cần cập nhật, dùng ít VRAM hơn full fine-tuning, checkpoint
nhỏ và phù hợp để thử nhiều giả thuyết trên GPU T4/P100 16 GB. `best_model/`
trong chế độ này là **adapter**, nên khi inference vẫn cần base VinAI model đúng
revision.

```bash
python -m src.vinai_baseline.cli train \
  --config configs/vinai/en2vi_lora.json
```

### 4.3 Full fine-tuning

Toàn bộ tham số được cập nhật. Cấu hình dùng learning rate nhỏ hơn `2e-5`.
Checkpoint lớn và optimizer cần nhiều VRAM; chỉ chạy sau khi LoRA baseline ổn
định. Nếu T4 hết bộ nhớ, giữ batch size 1, giảm eval batch size về 1 hoặc chuyển
sang GPU có nhiều VRAM. Không nên bật `auto_find_batch_size` ngay từ đầu vì nó
làm cấu hình thực tế giữa các run khó so sánh.

```bash
python -m src.vinai_baseline.cli train \
  --config configs/vinai/en2vi_full.json
```

Đổi `en2vi` thành `vi2en` cho chiều còn lại.

## 5. Token audit và xử lý đoạn dài

Trước training, tokenizer thật của VinAI đo độ dài source và target, tạo p50,
p90, p95, p99, max và số mẫu vượt giới hạn. Mặc định giới hạn là 512 token.

```bash
python -m src.vinai_baseline.cli audit \
  --config configs/vinai/en2vi_lora.json
```

`overlength_policy` có ba lựa chọn rõ ràng:

- `error`: dừng ngay nếu có mẫu vượt giới hạn; phù hợp lúc kiểm toán;
- `drop`: loại cặp vượt giới hạn và ghi số lượng vào báo cáo; mặc định hiện tại;
- `truncate`: cắt source/target; chỉ dùng khi đã chấp nhận rủi ro mất nội dung.

Không có truncate âm thầm. Với bản cuối, nên xem danh sách/tỷ lệ bị drop và
re-segment ở ranh giới câu hoặc khoản nếu tỷ lệ đáng kể.

Dynamic padding chỉ pad đến đoạn dài nhất trong từng batch, giảm token thừa so
với pad toàn bộ dữ liệu đến 512.

## 6. Metric và cách chọn model

Pipeline lưu:

- **SacreBLEU:** mức trùng khớp n-gram theo quy trình chuẩn hóa;
- **chrF++:** so khớp ký tự và từ, thường nhạy tốt với biến thể hình thái/dấu;
- tỷ lệ output rỗng và tỷ lệ độ dài prediction/reference;
- precision, recall, F1 và exact rate bảo toàn con số;
- precision, recall, F1 và exact rate của `Article/Điều`, `Clause/Khoản`,
  `Point/Điểm`, `Chapter/Chương`, `Section/Mục`;
- runtime, samples/giây do Trainer báo cáo và peak VRAM.

Checkpoint tốt nhất hiện được chọn theo dev `chrF`. Khi so sánh E0/E1/E2, không
chỉ nhìn một metric: model tốt phải tăng BLEU/chrF mà không làm giảm mạnh legal
preservation hoặc sinh output rỗng/quá ngắn.

## 7. Kiểm thử trước khi đóng gói

PyTorch CUDA đã có sẵn trên Colab. Vì vậy file requirement không
ép cài lại Torch để tránh phá phiên bản CUDA của runtime.

```bash
# Colab hoặc môi trường kiểm thử bất kỳ
python -m pip install -r requirements-training.txt
python -m unittest discover -s tests -v
python -m src.vinai_baseline.cli --help
```

Kiểm tra GPU:

```bash
nvidia-smi
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

`--allow-cpu` chỉ dành cho smoke test rất nhỏ. Model khoảng 1,69 GB và generation
trên CPU quá chậm cho full dev/training.

## 8. Chạy Google Colab

Notebook: `notebooks/02_vinai_colab.ipynb`.

1. Nén project thành một file ZIP, bao gồm `src/`, `configs/`,
   `requirements-training-colab.txt`, `requirements-training.txt` và
   `artifacts/processed_clean_seed67_v2/`.
2. Upload/mở notebook trong Colab.
3. Chọn **Runtime → Change runtime type → GPU**.
4. Chạy lần lượt các cell: kiểm tra GPU, mount Drive, upload/giải nén ZIP và
   cài dependency. Notebook ưu tiên file version-locked
   `requirements-training-colab.txt`; PyTorch vẫn dùng bản đi cùng CUDA runtime.
5. Nếu muốn, tạo Colab Secret `HF_TOKEN`; model public nên token không bắt buộc.
6. Chọn `DIRECTION` và `MODE`; giữ `RUN_FULL=False`.
7. Chạy audit và smoke test. Đọc `token_audit_summary.json` cùng metric smoke.
   Với LoRA/full, smoke còn reload model đã lưu và tạo
   `reports/reload_smoke.json`.
8. Chạy full zero-shot trên toàn dev để lấy mốc E0. Sau đó đổi sang LoRA, smoke
   lại, đặt `RUN_FULL=True` và chạy E1.

Output được ghi vào thư mục riêng cho từng run:

```text
/content/drive/MyDrive/NLP_runs/<dataset_id>/<direction>/<mode>/<run_id>/
```

Nhờ vậy checkpoint vẫn còn khi runtime bị ngắt. Ghi vào Drive có thể chậm hơn
disk local; nếu ưu tiên tốc độ, đổi `OUTPUT_DIR` sang `/content/outputs`, rồi
copy kết quả sang Drive sau khi run kết thúc.

Mỗi thành viên đặt `MEMBER_TAG` riêng và mỗi giả thuyết đặt `EXPERIMENT_TAG`
riêng. Chi tiết quy tắc nhóm nằm tại `docs/team_handoff.md`.

## 9. Smoke test trước full run

Notebook tự chạy 32 mẫu train và 16 mẫu dev đối với LoRA/full, hoặc 16 mẫu dev
đối với zero-shot. Mục tiêu smoke test là phát hiện:

- thiếu file hoặc sai schema/direction;
- model/tokenizer không tải được;
- LoRA target module không khớp kiến trúc;
- lỗi CUDA hoặc hết VRAM;
- lỗi generation/metric/save checkpoint.

Smoke metric không có ý nghĩa để kết luận chất lượng vì số mẫu quá ít và
fine-tuning quá ngắn.

Trong khi chạy, CLI in timestamp cho từng giai đoạn: tải tokenizer, audit dữ
liệu, tải model, train, sinh bản dịch validation và lưu artifact. Thanh tiến độ
của Trainer hiển thị số batch/step; cuối command notebook in thời điểm hoàn
thành và tổng thời gian `HH:MM:SS`.

Cell kết quả tự chọn run hoàn chỉnh gần nhất (smoke hoặc full), rồi hiển thị:

- BLEU, chrF++, runtime, peak VRAM và tỷ lệ output rỗng;
- F1 bảo toàn số và viện dẫn pháp luật;
- metric theo category;
- năm mẫu `source → prediction → reference` cố định bằng seed 67;
- kiểm tra số prediction có khớp `evaluated_records` hay không.

Để kết luận chất lượng, phải chạy toàn bộ dev set và so zero-shot với LoRA/full
trên đúng cùng split. BLEU/chrF không phải “accuracy” tuyệt đối; cần đọc mẫu lỗi,
đặc biệt là phủ định, nghĩa vụ, con số, điều/khoản/điểm và thuật ngữ pháp lý.

CLI tương đương:

```bash
python -m src.vinai_baseline.cli train \
  --config configs/vinai/en2vi_lora.json \
  --output-dir outputs/smoke_en2vi \
  --max-train-samples 32 \
  --max-validation-samples 16
```

## 10. Resume khi runtime bị ngắt

Có thể để code tự chọn checkpoint có step lớn nhất:

```bash
python -m src.vinai_baseline.cli train \
  --config configs/vinai/en2vi_lora.json \
  --output-dir outputs/vinai_en2vi_legal_lora \
  --resume-from-checkpoint last
```

Output directory phải là cùng run cũ. Không resume checkpoint bằng config/model
khác chiều. Code kiểm tra `trainer_state.json`, bắt checkpoint nằm trong đúng
`output_dir/checkpoints/` và từ chối nếu data/model/seed/hyperparameter khác
`resolved_config.json`. Trên notebook, đặt `RUN_ID_OVERRIDE` bằng run cũ và
`RESUME_FROM_CHECKPOINT="last"`.

## 11. Cấu trúc output

```text
output_dir/
├── resolved_config.json
├── run_manifest.json
├── best_model/
├── checkpoints/
│   └── checkpoint-*/
├── predictions/
│   └── validation_predictions.jsonl
└── reports/
    ├── parameter_report.json
    ├── reload_smoke.json
    ├── token_audit_train.json
    ├── token_audit_validation.json
    ├── token_audit_summary.json
    ├── training_plan.json
    ├── train_metrics.json
    ├── validation_metrics_by_category.json
    └── validation_metrics.json
```

- `resolved_config.json`: config cuối sau CLI override;
- `run_manifest.json`: thời gian, hardware, phiên bản package, model/revision và
  metric của run;
- `best_model/`: adapter LoRA hoặc full model đã chọn;
- `checkpoints/`: trạng thái trung gian để early stopping/resume;
- `validation_predictions.jsonl`: source, reference, prediction và metadata để
  error analysis mà không phải inference lại;
- `parameter_report.json`: tổng và tỷ lệ tham số thực sự được train;
- `reload_smoke.json`: bằng chứng adapter/full model đã save, reload và generate
  thành công (chỉ LoRA/full);
- `token_audit_*.json`: phân bố token, số mẫu retained/dropped;
- `training_plan.json`: số optimizer update dự kiến, effective batch và số lần
  chạy validation trong quá trình train;
- `validation_metrics.json`: quality, legal preservation, runtime và peak VRAM.
- `validation_metrics_by_category.json`: cùng bộ metric tách theo lĩnh vực để
  phát hiện model tăng điểm tổng nhưng giảm mạnh ở một category.

## 12. Hyperparameter nào nên chỉnh trước

Giữ cố định dataset/dev split và thay một yếu tố mỗi thí nghiệm:

1. chạy zero-shot beam 2;
2. chạy LoRA mặc định;
3. thử learning rate `5e-5`, `1e-4`, `2e-4` nếu loss/metric chưa ổn;
4. thử LoRA rank 8/16/32;
5. so beam 1/2/4 trên cùng checkpoint để tìm cân bằng chất lượng–tốc độ;
6. chỉ sau đó chạy full fine-tuning;
7. sau baseline B mới thêm glossary/cross-reference context thành run riêng.

Nếu OOM, ưu tiên giảm `per_device_eval_batch_size`, rồi giảm
`max_source_length`/`max_target_length` **sau khi xem token audit**. Không tăng
gradient accumulation một cách vô tình: effective batch size bằng
`per_device_train_batch_size × gradient_accumulation_steps × số GPU`.

Các tối ưu đang bật được chọn để giữ kết quả dễ so sánh: dynamic padding,
mixed precision, gradient checkpointing, LoRA và eval/save theo epoch. Chưa bật
QLoRA, quantization, pruning, distillation, `torch.compile` hoặc giảm beam trong
baseline vì chúng có thể đổi chất lượng, độ ổn định hoặc điều kiện so sánh.

## 13. Lỗi thường gặp

### `CUDA is required...`

Runtime chưa bật GPU hoặc Torch không khớp CUDA. Kiểm tra `nvidia-smi` và
`torch.cuda.is_available()`; restart runtime sau khi thay GPU.

### `CUDA out of memory`

Giảm eval batch 2 → 1. Với full fine-tuning, chuyển sang LoRA hoặc GPU VRAM lớn
hơn. Đừng dùng truncate để chữa OOM trước khi xem audit vì có thể làm mất nội
dung pháp lý.

### Tải model chậm/HTTP rate limit

Thêm `HF_TOKEN` vào Secrets, xác nhận Internet được bật và chạy lại. Cache của
Colab tồn tại trong session nên không cần tải lại ở mỗi cell.

### `No module named sentencepiece/peft/sacrebleu`

Chạy lại `pip install -r requirements-training.txt`, sau đó restart kernel nếu
pip yêu cầu.

### Audit báo nhiều mẫu vượt 512

Mở báo cáo, xác định category/segment bị ảnh hưởng, rồi re-segment theo câu,
khoản hoặc điểm. `drop` là baseline minh bạch, chưa chắc là lựa chọn cuối tốt
nhất.

## 14. Checklist trước khi ghi nhận kết quả chính thức

- [ ] Git đã chứa code/config/notebook cùng revision với run.
- [ ] GPU và phiên bản package được lưu trong `run_manifest.json`.
- [ ] Token audit đã được đọc; tỷ lệ drop được chấp nhận hoặc xử lý lại.
- [ ] Zero-shot và fine-tuned dùng cùng dev set và generation config.
- [ ] Không có public test trong train/config lựa chọn checkpoint.
- [ ] Prediction được lưu để error analysis.
- [ ] So sánh BLEU, chrF++, number/reference preservation, runtime và VRAM.
- [ ] Chạy cả `en2vi` và `vi2en`; không suy luận kết quả chiều này cho chiều kia.
- [ ] LoRA adapter đi kèm tên và revision base model.
- [ ] Sao lưu checkpoint khỏi runtime tạm thời.

## 15. Tài liệu kỹ thuật tham khảo

- VinAI model card: <https://huggingface.co/vinai/vinai-translate-en2vi-v2>
- Hugging Face Trainer: <https://huggingface.co/docs/transformers/main_classes/trainer>
- PEFT/LoRA: <https://huggingface.co/docs/peft/main/task_guides/lora_based_methods>
- SacreBLEU: <https://github.com/mjpost/sacrebleu>

Các API được dùng trực tiếp qua `AutoTokenizer`, `AutoModelForSeq2SeqLM` và
`Seq2SeqTrainer`; không gọi API dịch bên ngoài trong inference.
