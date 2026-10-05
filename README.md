# VLSP 2026 — Document-Level Legal English–Vietnamese Machine Translation

Baseline dịch tài liệu pháp luật hai chiều **English → Vietnamese** và
**Vietnamese → English**, xây dựng từ VinAI Translate v2, thích nghi miền bằng
LoRA, đánh giá theo document/segment và triển khai dưới dạng Docker chạy offline.

> Trạng thái: dataset v3, hai LoRA run và decoding sweep đã hoàn thành. Repo đã
> có hai ZIP model đã train trong `modelAI/`; bước merge và kiểm thử Docker cuối
> vẫn cần thực hiện. Pipeline inference pháp lý mới đã có code và notebook offline,
> đang tắt trong submission để chờ full-dev ablation và nghiệm thu.

<a id="muc-luc"></a>
## Mục lục

1. [Giới thiệu cuộc thi](#gioi-thieu)
2. [Ý tưởng baseline](#baseline)
3. [Cấu trúc repository](#cau-truc)
4. [Dữ liệu và cách chia tập](#du-lieu)
5. [Cấu hình mô hình và huấn luyện](#cau-hinh)
6. [Chuẩn bị môi trường và tài nguyên offline](#chuan-bi)
7. [Tạo lại dataset v3](#tao-dataset)
8. [Chạy lại thực nghiệm](#thuc-nghiem)
9. [Kết quả hiện có](#ket-qua)
10. [Public test và private test](#test)
11. [Đóng gói submission](#submission)
12. [Kiểm thử repository](#kiem-thu)
13. [Pipeline inference pháp lý, không train lại](#inference-phap-ly)

<a id="gioi-thieu"></a>
## 1. Giới thiệu cuộc thi

[VLSP 2026 Legal Machine Translation Challenge](https://vlsp.org.vn/vlsp2026/eval/mt_challenge)
yêu cầu dịch **toàn bộ tài liệu pháp luật** theo hai chiều EN→VI và VI→EN. Bài
toán khó hơn dịch câu thông thường vì phải giữ đúng:

- thuật ngữ pháp lý và tính nhất quán trong toàn văn bản;
- quyền, nghĩa vụ, điều kiện và ngoại lệ;
- câu dài, mệnh đề lồng nhau và viện dẫn chéo;
- Điều/Khoản/Điểm, số hiệu văn bản, ngày tháng và con số;
- cấu trúc Markdown của tài liệu đầu vào.

Các ràng buộc chính:

- model cuối có ít hơn `3B` tham số;
- inference phải chạy local, không gọi API/dịch vụ online;
- private test chỉ có tài liệu nguồn, reference được giữ kín;
- input và output là tài liệu Markdown UTF-8 hoàn chỉnh;
- bài nộp là Docker image self-contained chạy offline, kèm Bash wrapper nhận
  đúng ba tham số: `host:port/path`, input file và output file;
- đánh giá gồm metric tự động, đánh giá bằng LLM, độ đúng/nhất quán pháp lý,
  thời gian inference và peak memory.

Các mốc đang công bố: training data `18/09/2026`, public test `25/09/2026`,
private test `09/10/2026`, công bố kết quả `15/10/2026`.

<a id="baseline"></a>
## 2. Ý tưởng baseline

### 2.1 Base model theo từng chiều

Repo dùng hai mô hình seq2seq mBART chuyên biệt do VinAI phát hành:

| Chiều | Base model | Revision được khóa |
|---|---|---|
| EN→VI | [`vinai/vinai-translate-en2vi-v2`](https://huggingface.co/vinai/vinai-translate-en2vi-v2) | `1e47495b5dac16097b1d9e7b4133c27e1f40504f` |
| VI→EN | [`vinai/vinai-translate-vi2en-v2`](https://huggingface.co/vinai/vinai-translate-vi2en-v2) | `4eb2219d447d4352861e71e371a6b6abcb0509c8` |

Mỗi chiều có tokenizer/language control riêng. Code kiểm tra token ngôn ngữ nguồn,
token ngôn ngữ đích và `decoder_start_token_id` trước khi train để tránh trường
hợp mô hình sinh sai ngôn ngữ dù loss vẫn giảm.

### 2.2 Domain adaptation bằng LoRA

Thay vì fine-tune toàn bộ model, baseline chèn LoRA vào `q_proj` và `v_proj` của
attention:

\[
W' = W + \frac{\alpha}{r}BA,
\]

trong đó trọng số gốc `W` được giữ cố định; chỉ hai ma trận hạng thấp `A, B`
được cập nhật. Cấu hình `r=16`, `alpha=32`, dropout `0.05` chỉ train khoảng
`0,55%` tham số, giảm VRAM và thời gian nhưng vẫn thích nghi được thuật ngữ pháp
lý. Hai adapter được merge vào base model trước khi đóng Docker.

### 2.3 Luồng lựa chọn hệ thống

```text
Base VinAI đã pin revision
        │
        ├── Zero-shot 256 mẫu: kiểm tra language control và lỗi suy biến
        │
        ├── LoRA smoke run: kiểm tra train/save/reload
        │
        ├── LoRA full run: 3 epoch, chọn checkpoint theo chrF++ trên dev
        │
        ├── Decoding sweep trên dev cố định
        │
        ├── Đánh giá cấu hình đã chốt trên public test
        │
        └── Merge adapter → Docker offline → private test
```

Quality gate phát hiện output rỗng, sai ngôn ngữ, lặp/collapse, độ dài bất thường
và cảnh báo under-translation. BLEU/chrF++ đo chất lượng tổng quát; các metric
number/reference/legal-identifier kiểm tra khả năng giữ thông tin pháp lý.

<a id="cau-truc"></a>
## 3. Cấu trúc repository

| Đường dẫn | Nội dung |
|---|---|
| `data/` | Dữ liệu gốc và mô tả challenge |
| `src/data/` | Chuẩn hóa, alignment, segment, split, semantic audit và freeze |
| `artifacts/processed_clean_semantic_seed67_v3/` | Dataset v3 frozen dùng chính thức |
| `configs/templates/` | Template để sinh config cho dataset mới |
| `configs/generated_v3/` | 6 config v3: zero-shot/LoRA/full × 2 chiều |
| `src/vinai_baseline/` | Training, metrics, quality gate, inference và HTTP service |
| `notebooks/04_v3_builder_kaggle.ipynb` | Tạo semantic audit, freeze v3 và sinh config |
| `notebooks/03_vinai_kaggle.ipynb` | Zero-shot, train, sweep, public-test trên Kaggle |
| `results_model_sweep_testset/` | Metric, report, prediction và checksum đã lưu |
| `submission/` | Dockerfile, config cuối, Bash wrapper và smoke test |
| `scripts/` | Chuẩn bị asset offline, package Kaggle và package submission |
| `tests/` | Unit/integration/contract tests |

<a id="du-lieu"></a>
## 4. Dữ liệu và cách chia tập

### 4.1 Nguyên tắc chia

Đơn vị split là **duplicate group của document**, không phải segment ngẫu nhiên.
Các document có nội dung nguồn trùng hoặc gần trùng được gom cùng nhóm trước khi
chia, nhờ đó các đoạn của cùng tài liệu không rơi vào cả train và dev.

Contract của split:

| Thuộc tính | Giá trị |
|---|---|
| Phương pháp | `sklearn.model_selection.train_test_split` |
| Đơn vị | `duplicate_group` |
| Stratify | `category` |
| Dev ratio | `0.10` |
| Split seed | `67` |
| Training seed | `67` |

Public test do ban tổ chức cung cấp được xử lý riêng và không tham gia phép chia
train/dev. Private test tuyệt đối không được dùng để train, chọn checkpoint hoặc
tuning decoding.

### 4.2 Làm sạch và semantic audit

Pipeline thực hiện theo thứ tự:

1. đọc tài liệu song ngữ và chuẩn hóa Unicode, newline, khoảng trắng;
2. tạo logical blocks, giữ tiêu đề/Điều/Khoản và loại separator trang trí;
3. align block hai ngôn ngữ bằng anchor và alignment score;
4. gom duplicate document rồi split train/dev theo category;
5. segment/pack theo tokenizer, không cắt âm thầm mẫu vượt giới hạn;
6. loại identity pair, duplicate pair và source/target leakage giữa train-dev;
7. chấm cosine similarity bằng LaBSE revision `836121a`;
8. freeze các cặp đạt alignment `≥ 0.75` và semantic similarity `≥ 0.70`.

LaBSE có encoder limit 256 nên audit ghi riêng tỷ lệ bị truncation. Đây là giới
hạn của phép chấm semantic, không phải giới hạn train: config VinAI dùng tối đa
512 source/target tokens và generation tối đa 448 tokens.

### 4.3 Dataset frozen cuối

Dataset ID: `legal_envi_clean_semantic_seed67_v3`.

| Split | EN→VI | VI→EN | Bị loại khi freeze |
|---|---:|---:|---:|
| Train | 27.756 | 27.756 | 1.948 |
| Dev | 2.783 | 2.783 | 193 |
| Public test | 1.837 | 1.837 | 121 |

Manifest và hash của parent dataset nằm trong
`artifacts/processed_clean_semantic_seed67_v3/manifest.json`.

<a id="cau-hinh"></a>
## 5. Cấu hình mô hình và huấn luyện

### 5.1 LoRA training

| Tham số | Giá trị |
|---|---:|
| Epochs | `3` |
| Learning rate | `5e-5` |
| Weight decay | `0.01` |
| Warmup ratio | `0.05` |
| Label smoothing | `0.1` |
| Micro batch size | `4` |
| Gradient accumulation | `4` |
| Effective batch size / GPU | `16` |
| Eval batch size | `16` |
| Precision | `fp16` |
| Gradient checkpointing | bật |
| Checkpoint eval subset | `256` mẫu, tối đa `6`/document |
| Best-model metric | `chrF++` |
| Early stopping patience | `2` |
| LoRA | `r=16`, `alpha=32`, dropout `0.05`, `q_proj/v_proj` |

Config nguồn:

- `configs/generated_v3/en2vi_lora.json`
- `configs/generated_v3/vi2en_lora.json`

### 5.2 Decoding cuối

Sweep thay đổi số beam, length penalty và repetition penalty trên một subset dev
cố định. Cấu hình được khóa trước private test:

| Chiều | Tên | Beams | Length penalty | Repetition penalty | No-repeat ngram |
|---|---|---:|---:|---:|---:|
| EN→VI | `longer110` | `2` | `1.10` | `1.00` | `3` |
| VI→EN | `beam4longer` | `4` | `1.10` | `1.00` | `3` |

Config Docker cuối nằm trong `submission/configs/` và không được thay đổi sau khi
xem private test.

<a id="chuan-bi"></a>
## 6. Chuẩn bị môi trường và tài nguyên offline

### 6.1 Kiểm thử trên local

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-training.txt
python -m unittest discover -s tests -v
```

`requirements-semantic.txt` chỉ cần khi tạo semantic audit bằng LaBSE.

### 6.2 Tải asset một lần khi local còn Internet

```powershell
python -m pip install -U huggingface_hub
python scripts/prepare_offline_training_assets.py `
  --output-dir offline_training_assets `
  --directions both `
  --python-version 313
```

Kết quả gồm:

```text
offline_training_assets/
├── vinai-translate-en2vi-v2.zip
├── vinai-translate-vi2en-v2.zip
└── vinai-training-wheelhouse-py313-linux.zip
```

Mỗi model ZIP có `offline_model_manifest.json` để kiểm tra repo ID, revision,
kích thước và SHA-256. Upload ba ZIP này vào Kaggle Dataset/Input; Kaggle notebook
không gọi Hugging Face khi `OFFLINE_TRAINING=True`.

### 6.3 Đóng gói code và dataset frozen

```powershell
powershell -ExecutionPolicy Bypass -File scripts/package_colab.ps1 `
  -DatasetPath artifacts\processed_clean_semantic_seed67_v3 `
  -OutputPath NLP_v3_frozen_offline.zip
```

Upload ZIP này cùng ba offline assets vào Kaggle Input.

<a id="tao-dataset"></a>
## 7. Tạo lại dataset v3

Nếu đã có artifact frozen, bỏ qua phần này. Muốn tái tạo từ dữ liệu gốc:

1. Tạo parent v3 trên local:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/prepare_v3.ps1
   ```

2. Upload project/parent artifact và snapshot LaBSE lên Kaggle.
3. Mở `notebooks/04_v3_builder_kaggle.ipynb`.
4. Chạy semantic audit với `SEMANTIC_THRESHOLD=None` để sinh report và duyệt
   phân phối score.
5. Đặt `SEMANTIC_THRESHOLD=0.70`, `RUN_FREEZE=True`.
6. Freeze dataset và sinh đủ sáu config vào `configs/generated_v3/`.
7. Chạy validation cell, tải ZIP frozen về máy và kiểm tra manifest.

Không ghi đè dataset đã freeze. Khi đổi threshold/split/code, dùng dataset ID mới
để các run còn truy vết được.

<a id="thuc-nghiem"></a>
## 8. Chạy lại thực nghiệm

Mở `notebooks/03_vinai_kaggle.ipynb`, bật GPU, tắt Internet và chạy từ đầu.

### Bước 1 — Attach input

Attach:

- `NLP_v3_frozen_offline.zip`;
- model ZIP đúng chiều hoặc cả hai model ZIP;
- wheelhouse ZIP;
- output của run trước nếu cần resume.

### Bước 2 — Chọn thí nghiệm

Trong cell cấu hình:

```python
DATASET_PROFILE = "v3_frozen"
DIRECTION = "en2vi"       # hoặc "vi2en"
MODE = "lora"             # zero_shot | lora | full
OFFLINE_TRAINING = True
RUN_FULL = False
```

### Bước 3 — Zero-shot preflight

Chạy 256 dev records cố định, không train. Gate phải xác nhận:

- model/tokenizer và language control đúng chiều;
- không có output rỗng hoặc generation collapse;
- report khớp dataset, model revision, decoding và code hiện tại.

Nếu chỉ có warning under-translation, vẫn có thể tiếp tục LoRA; hard failure phải
được xem trong `gate_report.json` trước khi train.

### Bước 4 — LoRA smoke run

Giữ `RUN_FULL=False`. Smoke run kiểm tra một tập nhỏ để chắc chắn forward/backward,
save adapter, reload và generation đều hoạt động. Chỉ chạy full khi smoke pass.

### Bước 5 — Full training

Đặt:

```python
RUN_FULL = True
```

Notebook train 3 epoch, đánh giá subset 256 ở mỗi epoch, giữ checkpoint tốt nhất
theo chrF++, sau đó chạy final generation. Nếu phiên Kaggle bị ngắt, attach output
cũ, giữ nguyên `RUN_ID`, đặt `RESUME_FROM_CHECKPOINT="last"` và trỏ
`RESUME_RUN_SOURCE` đến đúng run directory.

### Bước 6 — Verify và decoding sweep

Reload `best_model`, chạy quality gate rồi sweep các candidate decoding trên cùng
subset dev. Không so candidate nếu khác dataset hash, model revision, segment IDs
hoặc code identity.

### Bước 7 — Đánh giá cấu hình đã chọn

Sau khi sweep chốt config, chạy lại candidate được chọn trên evaluation subset lớn
và lưu `subset.json`, `gate_report.json`, `predictions.jsonl`. Artifact hiện có dùng
1.821/2.783 dev records, được chọn category-proportional bằng hash seed; vì vậy
không gọi 1.821 records này là toàn bộ dev.

### Bước 8 — Public test

Chỉ sau khi checkpoint/decoding đã chốt, chạy cell `Public-test final evaluation`.
Lưu report/prediction riêng cho từng chiều và không ghi public test vào train/dev.
Trang cuộc thi cho phép dùng metric public test để quyết định hệ thống sẽ nộp;
repo vẫn giữ một cấu hình đã khóa để tránh tuning lặp lại trên test.

### Bước 9 — Tải artifact cần thiết

Tải về tối thiểu:

- `best_model/adapter_config.json`;
- `best_model/adapter_model.safetensors`;
- resolved config và run manifest;
- validation/public-test reports và predictions;
- log train/verify và checksum.

Các ZIP hiện có trong `results_model_sweep_testset/` chỉ chứa report/prediction,
không chứa adapter weights.

<a id="ket-qua"></a>
## 9. Kết quả hiện có

### 9.1 Zero-shot 256 records

| Chiều | BLEU | chrF++ | Ghi chú |
|---|---:|---:|---|
| EN→VI | 19.338 | 39.799 | log lịch sử trước khi cập nhật gate |
| VI→EN | 26.922 | 52.290 | gate pass, 4 warnings |

### 9.2 Evaluation subset 1.821/2.783 dev records

| Chiều | Decoding | BLEU | chrF++ | Number F1 | Reference F1 | Legal-ID F1 | Gate |
|---|---|---:|---:|---:|---:|---:|---|
| EN→VI | `longer110` | 54.395 | 69.938 | 93.851 | 92.431 | 73.829 | pass |
| VI→EN | `beam4longer` | 34.323 | 60.743 | 92.035 | 88.579 | 64.895 | pass, 3 warnings |

### 9.3 Public test 1.837 records mỗi chiều

| Chiều | BLEU | chrF++ | Number F1 | Reference F1 | Legal-ID F1 | Empty output |
|---|---:|---:|---:|---:|---:|---:|
| EN→VI | 64.086 | 76.108 | 94.904 | 93.978 | 80.992 | 0% |
| VI→EN | 41.295 | 65.428 | 95.062 | 90.332 | 72.572 | 0% |

Public test có vài `dominant_token` false positive chủ yếu ở bảng số dày đặc, nhưng
cũng cho thấy rủi ro thật với dấu thập phân và cấu trúc nhiều cột. Báo cáo đầy đủ:
`results_model_sweep_testset/EXPERIMENT_SUMMARY.md`.

<a id="test"></a>
## 10. Public test và private test

### 10.1 Khi public test có reference

Có thể tính BLEU, chrF++, number/reference/legal-ID F1 và quality gate. Chỉ so sánh
các hệ thống đã train hợp lệ; ghi lại model/config/hash để quyết định có thể audit.

### 10.2 Khi nhận private test

Private test chỉ có Markdown nguồn và reference ẩn. Quy trình đúng là:

1. **Không train lại và không sweep.** Dùng đúng merged model và config đã khóa.
2. Xác định chiều từ thông báo/file của ban tổ chức. Nếu protocol không truyền
   chiều, service có fallback phát hiện ngôn ngữ toàn document.
3. Khởi động Docker offline và kiểm tra `GET /health`.
4. Dịch từng file bằng wrapper ba tham số:

   ```bash
   TRANSLATION_DIRECTION=en2vi bash submission/translate.sh \
     http://127.0.0.1:8000 private_en.md predictions/private_vi.md

   TRANSLATION_DIRECTION=vi2en bash submission/translate.sh \
     http://127.0.0.1:8000 private_vi.md predictions/private_en.md
   ```

5. Kiểm tra **không cần reference**:
   - file output tồn tại, không rỗng và đọc được UTF-8;
   - không có replacement character `�`;
   - đúng ngôn ngữ đích;
   - số lượng heading/list/table/link không mất bất thường;
   - số, ngày tháng, URL và mã văn bản được bảo toàn hợp lý;
   - không có lặp/collapse hoặc output quá ngắn;
   - ghi runtime, input words/s, chunks/s và peak VRAM.
6. Giữ nguyên tên/thứ tự file theo protocol chính thức, tạo checksum prediction
   nếu được yêu cầu và lưu log inference riêng.

Không thể tính BLEU/chrF++ thật trên private test vì không có reference. Mọi đánh
giá lúc này là sanity check nguồn-output; điểm chính thức do ban tổ chức tính.

### 10.3 Smoke test trước private test

```bash
docker run --gpus all --rm -p 8000:8000 \
  --name vlsp2026-mt vlsp2026-legal-mt:latest

bash submission/smoke_test.sh http://127.0.0.1:8000 dist/smoke
```

Chạy lại với external network bị tắt và kiểm tra log không có request tới Hub/API.

<a id="submission"></a>
## 11. Đóng gói submission

### 11.1 Merge hai adapter và tạo build context

```powershell
powershell -ExecutionPolicy Bypass -File scripts/prepare_submission.ps1 `
  -En2ViAdapterDir D:\models\en2vi_best_model `
  -Vi2EnAdapterDir D:\models\vi2en_best_model `
  -En2ViBaseModelDir D:\models\vinai-translate-en2vi-v2 `
  -Vi2EnBaseModelDir D:\models\vinai-translate-vi2en-v2
```

Script chạy offline, merge LoRA, kiểm tra model/revision/SHA-256, đếm tham số từ
safetensors và tạo `dist/VLSP2026_MT_build_context.zip` cùng MD5.

### 11.2 Build, kiểm tra và export

```bash
docker build -f submission/Dockerfile -t vlsp2026-legal-mt:latest .
bash submission/export_image.sh vlsp2026-legal-mt:latest dist
```

Upload `vlsp2026_legal_mt_submission.tar.gz` và file `.md5` lên cloud với quyền tải
không cần đăng nhập. Tải lại rồi kiểm tra cả MD5 ngoài và `MD5SUMS` bên trong.

Checklist cuối: `submission/READINESS_CHECKLIST.md`.

<a id="kiem-thu"></a>
## 12. Kiểm thử repository

```powershell
$env:PYTHONDONTWRITEBYTECODE = "1"
python -m unittest discover -s tests -v
```

Trạng thái ngày 05/10/2026: **117 tests chạy, 116 passed, 1 optional cached-tokenizer
integration test skipped**. Các test bao phủ data split/finalization, language control, config
contract, quality gate, resume safety, document chunking, offline model resolution,
submission service, merged-model validation, parser giữ byte nguồn, validator,
glossary đã duyệt, retry và điều kiện chốt pipeline.

Trước khi nộp, luôn kiểm tra lại trang challenge và mailing list. Endpoint, port,
GPU/RAM, timeout, giới hạn archive và protocol private test cuối vẫn có thể được
ban tổ chức bổ sung.

<a id="inference-phap-ly"></a>
## 13. Pipeline inference pháp lý, không train lại

Lớp mới dùng adapter VI→EN đã train: giữ cấu trúc Markdown và placeholder,
chia đoạn theo thống kê train, kiểm số/ngày/viện dẫn, rồi dịch lại một vòng nếu
có lỗi. Glossary chỉ dùng các dòng bạn duyệt; bảng ứng viên đang ở `pending`.

**Hướng dẫn từng bước:** [docs/legal_inference_pipeline.md](docs/legal_inference_pipeline.md).
Notebook riêng: [05_inference_pipeline_kaggle.ipynb](notebooks/05_inference_pipeline_kaggle.ipynb).

```powershell
.venv\Scripts\python.exe scripts\package_inference_pipeline.py
```

Script tạo `dist/NLP_inference_pipeline.zip` và SHA256 để upload Kaggle. Add Input
thêm base VI→EN offline và wheelhouse đã dùng train. Notebook dùng frozen dev để
chạy A/B và R0–R5, xuất report và 30 mẫu chờ bạn rà soát; không chạy training.

Parser round-trip đạt 2.783/2.783 đoạn dev. Probe 10 mẫu cụt `/ND` cho thấy EOS
xuất hiện trước cap; chỉ tắt ngram3 cải thiện chrF++ trên nhóm này từ 41,9001 lên
72,9127. Đây là **nhóm mẫu lỗi được chọn**, chưa phải cải thiện toàn dev.
Xem [bằng chứng cause probe](reports/inference_pipeline/cutoff_cause_probe.md).

Pipeline đang tắt tại `submission/configs/inference_pipeline.json`. Full-dev
R0–R5, review pháp lý, placeholder survival, Docker GPU và ngân sách thời gian
còn chờ. Dev hiện không có markup dạng cặp để đo survival trên 200 units; giới
hạn này được ghi trong report và chặn chốt pipeline khi chưa có bằng chứng.
