# Các công việc tiếp theo sau data preprocessing

## Mục tiêu

Sau structural preprocessing, cần hoàn thiện chất lượng dữ liệu, xây baseline,
fine-tune model, đánh giá ở cấp document và đóng gói submission. Không nên
fine-tune trực tiếp từ `artifacts/processed` trước khi chạy semantic filtering.

Tài liệu này là roadmap thực thi cho cả nhóm. Mỗi giai đoạn có mục đích, đầu ra
và điều kiện hoàn thành. Chỉ nên chuyển bước khi đầu ra trước đó đã được kiểm
tra và lưu đủ cấu hình để thành viên khác có thể chạy lại.

## Trạng thái hiện tại

| Hạng mục | Trạng thái | Ghi chú |
|---|---|---|
| EDA dữ liệu gốc | Hoàn thành | Có notebook khám phá dữ liệu. |
| Chuẩn hóa, deduplicate, train/dev split | Hoàn thành | Split ở cấp document. |
| Structural segmentation/alignment | Hoàn thành baseline | Vẫn có khả năng lệch nghĩa. |
| Semantic filtering | Chưa chạy | Code đã có; cần chạy LaBSE và chọn threshold. |
| Tokenizer analysis | Chưa làm | Thực hiện sau semantic filtering. |
| Zero-shot baseline và evaluator | Chưa làm | Là bước trước fine-tuning. |
| Fine-tuning | Chưa làm | Chỉ bắt đầu khi data gate đạt. |
| Document inference và Docker | Chưa làm | Giai đoạn sau khi model ổn định. |

## Nguyên tắc chung

1. **Đo trước khi tối ưu:** mọi thay đổi phải có baseline và metric so sánh.
2. **Không dùng public test để train:** public test chỉ dùng đánh giá cuối.
3. **Một thay đổi mỗi thí nghiệm:** không đồng thời đổi dataset, model và decode
   nếu muốn biết yếu tố nào tạo ra cải thiện.
4. **Ưu tiên độ trung thành pháp lý:** BLEU cao nhưng mất phủ định, điều kiện,
   con số hoặc nghĩa vụ vẫn là bản dịch không đạt.
5. **Theo dõi cả chi phí:** ranking có inference time và memory, nên model tốt
   nhất là điểm cân bằng chứ không nhất thiết là model lớn nhất.

## Các cổng quyết định

```text
DATA GATE
  Dữ liệu semantic-clean và đã audit
       ↓
BASELINE GATE
  Có evaluator + zero-shot baseline tái lập được
       ↓
MODEL GATE
  Fine-tuned model tốt hơn baseline và vượt legal checks
       ↓
DOCUMENT GATE
  Dịch document hoàn chỉnh, không mất/đảo/lặp chunk
       ↓
SUBMISSION GATE
  Docker chạy offline, đúng giao diện và giới hạn tài nguyên
```

## 1. Semantic filtering

**Mục đích:** loại các cặp structural alignment có độ dài tương tự nhưng không
phải bản dịch của nhau. LaBSE tạo embedding cho hai ngôn ngữ, còn cosine
similarity đo độ gần nghĩa. LaBSE không sinh bản dịch.

- Dùng LaBSE để đo semantic similarity giữa segment Anh–Việt.
- Loại các cặp tương tự về độ dài nhưng không tương ứng về nghĩa.
- Thử các threshold như `0.65`, `0.70`, `0.72`, `0.75`, `0.80`.
- Kiểm tra thủ công các mẫu quanh threshold trước khi chốt.
- So sánh tỷ lệ được giữ lại theo train/dev và theo `category`.

Lệnh khởi đầu:

```powershell
pip install -r requirements-semantic.txt

.\NLP_venv\Scripts\python.exe -m src.data.semantic_filter `
  --input-dir artifacts/processed `
  --output-dir artifacts/semantic `
  --model-name sentence-transformers/LaBSE `
  --minimum-similarity 0.72 `
  --batch-size 64
```

**Đầu ra:** các file segment đã lọc trong `artifacts/semantic`.

**Hoàn thành khi:** nhóm đã audit mẫu đúng/sai ở nhiều khoảng điểm, chọn threshold
có lý do và không có category bị mất tỷ lệ dữ liệu bất thường.

## 2. Đóng băng phiên bản dataset

**Đóng băng dataset** nghĩa là xác định một bộ file và cấu hình bất biến để mọi
thành viên dùng cùng dữ liệu. Nếu nội dung tiếp tục thay đổi nhưng vẫn mang tên
`v1`, kết quả giữa các máy sẽ không còn so sánh được.

- Đặt version, ví dụ `legal-envi-v1`.
- Lưu seed, structural threshold, semantic model và semantic threshold.
- Lưu hash của các file JSONL.
- Lưu số document, segment, từ và phân bố category.
- Giữ nguyên document-level train/dev split cho mọi thí nghiệm cùng version.
- Nếu thay preprocessing, tạo version mới thay vì ghi đè âm thầm.

**Đầu ra:** manifest của dataset version và checksum các file.

**Checksum** là hash của toàn bộ file. Nó giúp xác minh hai thành viên đang dùng
đúng cùng một bản dữ liệu mà không cần so từng dòng.

## 3. Phân tích tokenizer

**Tokenizer** chia văn bản thành các token ID. Token không nhất thiết là một từ:
một từ tiếng Việt hoặc số hiệu pháp lý có thể thành nhiều token. Vì vậy `400
words` không đồng nghĩa với `400 tokens`.

Chạy tokenizer của từng pretrained candidate:

- VinAI Translate v2.
- EnViT5 Translation.
- NLLB distilled 1.3B.

Thống kê cho source và target:

- `p50`, `p90`, `p95`, `p99`, `max` token.
- Tỷ lệ vượt 512, 768 và 1024 token.
- Số token trung bình theo ngôn ngữ và category.
- Tỷ lệ segment phải chia lại.

Không được truncate target âm thầm. Segment vượt context phải được tách lại ở
ranh giới pháp lý hoặc câu.

**Đầu ra:** báo cáo tokenizer và dataset tokenized cho từng model.

**Hoàn thành khi:** đã chọn `max_source_length`/`max_target_length`, biết tỷ lệ
segment vượt giới hạn và có quy tắc chia lại thay vì truncate target.

## 4. Xây evaluator dùng chung

Evaluator là code nhận source, reference và prediction rồi sinh cùng một hệ
metric cho mọi model. Nếu mỗi người normalize hoặc cấu hình metric khác nhau,
kết quả sẽ không so sánh được.

### Chất lượng dịch

- SacreBLEU.
- chrF++.
- COMET nếu tài nguyên cho phép.

Giải nghĩa ngắn:

- **SacreBLEU:** đo mức trùng khớp cụm từ theo quy trình chuẩn hóa có thể tái
  lập; hữu ích cho MT nhưng không hiểu đầy đủ nghĩa pháp lý.
- **chrF++:** so khớp chủ yếu theo chuỗi ký tự và bổ sung thông tin từ; hữu ích
  với dấu tiếng Việt và các khác biệt nhỏ về hình thức.
- **COMET:** metric học máy đánh giá mức phù hợp ngữ nghĩa dựa trên source,
  prediction và reference; nặng hơn và vẫn không thay thế legal checks.

### Chất lượng pháp lý

- Bảo toàn con số và phần trăm.
- Bảo toàn mã/số hiệu văn bản.
- Bảo toàn Article/Điều/Khoản.
- Độ đầy đủ của bản dịch.
- Tỷ lệ lặp đoạn.
- Phát hiện output sai ngôn ngữ.
- Terminology accuracy và consistency.

### Hiệu năng

- Thời gian inference trung bình, P50 và P95.
- Peak VRAM và RAM.
- Token/giây.
- Kích thước model và Docker image.

Evaluator phải lưu prediction và cấu hình decode để có thể so sánh các lần chạy
mà không cần inference lại.

**Đầu ra:** script đánh giá, prediction files và báo cáo tổng hợp.

**Hoàn thành khi:** cùng một prediction luôn cho cùng metric, báo cáo tách được
hai chiều/category và đo được latency cùng peak memory.

## 5. Chạy zero-shot baseline

**Zero-shot baseline** là chạy pretrained model nguyên bản, chưa fine-tune bằng
dữ liệu cuộc thi. Nó cho biết model khởi đầu tốt đến đâu và phần cải thiện sau
fine-tuning có thực sự đến từ domain data hay không.

Chạy cùng một dev set trên:

1. VinAI Translate v2.
2. EnViT5 Translation.
3. NLLB distilled 1.3B.

Cấu hình decode ban đầu:

```yaml
num_beams: 2
length_penalty: 1.0
no_repeat_ngram_size: 3
early_stopping: true
```

So sánh thêm beam `1`, `2`, `4` để tìm điểm cân bằng chất lượng–tốc độ. Không
dùng public test để chọn hyperparameter ban đầu.

**Beam search** giữ đồng thời nhiều chuỗi ứng viên khi sinh bản dịch. Beam lớn
thường tốn thời gian và memory hơn; không đảm bảo beam càng lớn càng tốt.

**Đầu ra:** bảng benchmark chất lượng, latency và memory của ba model.

**Hoàn thành khi:** ba model dùng cùng dataset/evaluator, lưu đầy đủ config và
prediction, rồi được so sánh trên mặt bằng chất lượng–tốc độ–memory.

## 6. Fine-tune model chính

**Fine-tuning** tiếp tục huấn luyện pretrained model trên dữ liệu pháp lý đã
làm sạch. Mục tiêu là học thuật ngữ, văn phong và cấu trúc domain mà không làm
mất năng lực dịch tổng quát ban đầu.

Ưu tiên thử VinAI Translate v2 trước:

- Model riêng English → Vietnamese.
- Model riêng Vietnamese → English.
- Chỉ train bằng `artifacts/semantic/segments_train_*`.
- Chọn checkpoint bằng dev set.
- Không dùng public test để cập nhật trọng số.

Các thí nghiệm tối thiểu:

| ID | Thí nghiệm |
|---|---|
| E0 | Zero-shot baseline |
| E1 | LoRA fine-tuning |
| E2 | Full fine-tuning |
| E3 | Full fine-tuning có legal context |
| E4 | Full fine-tuning có terminology information |

- **Full fine-tuning:** cập nhật toàn bộ trọng số; có tiềm năng chất lượng cao
  nhưng cần nhiều VRAM và checkpoint lớn.
- **LoRA:** chỉ học các adapter hạng thấp gắn vào model; tiết kiệm VRAM và lưu
  trữ, phù hợp chạy nhiều thử nghiệm.
- **Legal context:** đưa heading hoặc đoạn trước vào input để giảm dịch sai đại
  từ/thuật ngữ, nhưng target chỉ chứa đoạn hiện tại.

Cấu hình full fine-tuning khởi đầu:

```yaml
precision: bf16
learning_rate: 2e-5
epochs: 3
warmup_ratio: 0.05
weight_decay: 0.01
label_smoothing: 0.1
gradient_checkpointing: true
early_stopping_patience: 3
```

Batch theo tổng số token thay vì số segment cố định. Chọn checkpoint bằng score
tổng hợp gồm BLEU, chrF, thuật ngữ, bảo toàn identifier và độ đầy đủ.

**Đầu ra:** checkpoint tốt nhất mỗi chiều, training log và bảng so sánh thí nghiệm.

**Hoàn thành khi:** model tốt hơn zero-shot trên nhiều metric, cải thiện ở phần
lớn category và không đánh đổi bằng lỗi mất số hoặc mất nội dung.

## 7. Error analysis

Error analysis là đọc có hệ thống các prediction sai để tìm nguyên nhân, thay vì
chỉ nhìn một điểm trung bình. Kết quả cho biết cần sửa dữ liệu, training hay
inference.

Thu thập và phân loại các lỗi:

- Alignment sai.
- Truncation hoặc tokenization sai.
- Bỏ sót nội dung.
- Hallucination.
- Sai thuật ngữ pháp lý.
- Sai số, ngày hoặc mã văn bản.
- Sai tham chiếu chéo.
- Mất cấu trúc hoặc format.
- Thuật ngữ không nhất quán giữa các chunk.
- Output bị lặp.

Phân tích riêng theo hai chiều dịch và 7 category. Nếu lỗi bắt nguồn từ dữ liệu,
cần sửa dataset version thay vì chỉ điều chỉnh hyperparameter.

**Đầu ra:** error taxonomy và danh sách lỗi ưu tiên cần sửa.

## 8. Xây legal glossary

**Legal glossary** là từ điển thuật ngữ có source, target, lĩnh vực, tần suất và
mức tin cậy. Nó giúp đánh giá và duy trì cách dịch nhất quán trong document.

- Trích các cụm pháp lý xuất hiện nhiều lần từ semantic-clean data.
- Gom các cách dịch và tính tần suất/độ nhất quán.
- Kiểm tra thủ công các thuật ngữ quan trọng.
- Tạo glossary chung và glossary theo category.
- Không tự động ép các term có nhiều nghĩa phụ thuộc ngữ cảnh.

Glossary được dùng để:

- Tính terminology metrics.
- Bổ sung context khi fine-tune.
- Kiểm tra consistency ở cấp document.
- Dịch lại các chunk vi phạm thuật ngữ quan trọng.

**Đầu ra:** glossary có source, target, category, frequency và confidence.

## 9. Xây document-level inference pipeline

Model được train trên segment nhưng hệ thống được chấm trên document. Pipeline
phải tách, dịch, kiểm tra và ghép lại mà không đổi thứ tự hay mất cấu trúc.

```text
Markdown document
    ↓
Chuẩn hóa và nhận diện chiều dịch
    ↓
Tách cấu trúc pháp lý
    ↓
Token-aware chunking
    ↓
Batch translation
    ↓
Kiểm tra từng chunk
    ↓
Dịch lại chunk lỗi nếu cần
    ↓
Ghép đúng thứ tự và khôi phục format
```

Validator cần phát hiện:

- Thiếu hoặc trùng chunk.
- Mất số và identifier.
- Output rỗng hoặc quá ngắn.
- Output sai ngôn ngữ.
- Lặp đoạn.
- Sai thứ tự Article/Điều.
- Sinh thêm lời giải thích ngoài bản dịch.

Có thể dùng beam 2 mặc định và chỉ retry bằng beam 4 hoặc chunk nhỏ hơn khi
validator phát hiện lỗi.

**Đầu ra:** hàm dịch document hoàn chỉnh và bộ validator.

**Validator** kiểm tra các bất biến có thể xác minh tự động như số lượng chunk,
mã văn bản, con số, ngôn ngữ output và repetition. Nó không thay thế đánh giá
ngữ nghĩa của con người. Chunk lỗi có thể được retry với cấu hình cẩn thận hơn.

## 10. Đánh giá document-level

Segment score có thể tốt nhưng document vẫn sai nếu ghép thiếu, đảo thứ tự hoặc
dịch cùng một thuật ngữ theo nhiều cách. Đây là phép đánh giá gần submission
thực tế nhất.

- Ghép prediction thành document trước khi chấm.
- Đánh giá SacreBLEU/chrF trên toàn document.
- Kiểm tra terminology consistency xuyên nhiều chunk.
- Kiểm tra thứ tự điều khoản và độ đầy đủ.
- Kiểm tra formatting.
- Benchmark document median, P90 và document lớn nhất.

**Đầu ra:** báo cáo chất lượng và hiệu năng ở đúng đơn vị submission.

## 11. Dữ liệu ngoài và augmentation

**Data augmentation** tạo thêm ví dụ từ dữ liệu hiện có hoặc nguồn công khai.
**Back-translation** dịch dữ liệu đơn ngữ sang ngôn ngữ còn lại để tạo cặp
synthetic. Dữ liệu synthetic phải được lọc vì lỗi của teacher có thể được model
mới học lại.

Chỉ thực hiện sau khi baseline nội bộ ổn định:

- MTet/PhoMT cho dữ liệu tổng quát.
- Tài liệu pháp lý song ngữ chính thức.
- Legal monolingual data.
- Back-translation bằng model local.
- Terminology-aware augmentation.

Trước khi dùng phải kiểm tra license, deduplicate với train/dev/public test và
đảm bảo dữ liệu tổng quát không lấn át legal corpus. Fine-tune cuối cùng lại trên
dữ liệu cuộc thi với learning rate nhỏ.

## 12. Tối ưu inference và đóng gói Docker

Các dạng số học và kỹ thuật thường gặp:

- **BF16:** số 16-bit có dải giá trị rộng, thường ổn định trên GPU mới.
- **FP16:** số 16-bit phổ biến, tiết kiệm memory nhưng dải giá trị hẹp hơn.
- **INT8:** lượng tử hóa trọng số xuống 8-bit để giảm memory/có thể tăng tốc;
  phải đo lại chất lượng.
- **Dynamic batching:** gom segment có độ dài phù hợp để tận dụng GPU và giảm
  lượng padding thừa.

**Docker image** đóng gói code, dependency và model weights để hệ thống chạy
giống nhau trên máy ban tổ chức. Offline inference nghĩa là container không tải
model hoặc gọi dịch vụ ngoài trong lúc chấm.

- So sánh BF16, FP16 và INT8.
- Dùng dynamic batching.
- Chỉ load model cần cho chiều dịch hiện tại.
- Pin phiên bản dependency.
- Đưa toàn bộ model weights vào image.
- Không gọi API hoặc tải dữ liệu trong lúc inference.
- Viết API service và Bash wrapper đúng yêu cầu ba tham số.
- Test container khi mạng bị tắt.

Nên duy trì hai cấu hình:

```text
quality:  beam=4, ưu tiên chất lượng
balanced: beam=2, ưu tiên score tổng hợp và tốc độ
```

**Đầu ra:** Docker image offline, Bash script và báo cáo benchmark cuối.

## Thứ tự ưu tiên

```text
1. Semantic filtering
2. Audit và chọn semantic threshold
3. Đóng băng dataset v1
4. Tokenizer analysis
5. Evaluator
6. Zero-shot baselines
7. Chọn và fine-tune model chính
8. Error analysis và legal glossary
9. Document-level inference
10. Tối ưu, Docker và kiểm thử offline
```

Điểm dừng gần nhất là tạo được `artifacts/semantic` đã kiểm toán. Chưa đạt điểm
này thì chưa nên bắt đầu fine-tuning.

## Checklist quản lý thí nghiệm

Mỗi lần chạy nên lưu tối thiểu:

- mã thí nghiệm và câu hỏi cần kiểm chứng;
- dataset version và checksum;
- model checkpoint gốc, số tham số và license;
- seed;
- hyperparameter;
- tokenizer và giới hạn token;
- hardware;
- training time;
- decoding config;
- prediction trên dev;
- metric tổng và metric theo category;
- peak VRAM/RAM và latency;
- ghi chú lỗi quan sát được.

Một run được ghi chép tốt phải giúp thành viên khác trả lời: “Nếu chạy lại đúng
cấu hình này, tôi có nhận được kết quả tương đương không?”.

## Thuật ngữ nhanh

| Thuật ngữ | Nghĩa và mục đích |
|---|---|
| Pretrained model | Model đã học từ dữ liệu lớn trước cuộc thi, dùng làm điểm khởi đầu. |
| Zero-shot | Chạy model chưa fine-tune trên dữ liệu cuộc thi. |
| Fine-tuning | Huấn luyện tiếp pretrained model trên dữ liệu của task/domain. |
| Domain adaptation | Điều chỉnh model cho lĩnh vực cụ thể, ở đây là pháp lý. |
| Checkpoint | Trạng thái trọng số model được lưu tại một thời điểm training. |
| Hyperparameter | Tham số do người huấn luyện chọn như learning rate, batch size, epoch. |
| Epoch | Một lượt model đi qua toàn bộ tập train. |
| Learning rate | Độ lớn mỗi bước cập nhật trọng số; quá cao dễ mất ổn định, quá thấp học chậm. |
| Batch | Nhóm mẫu được xử lý trong cùng một bước. |
| Gradient accumulation | Cộng gradient qua nhiều batch nhỏ để mô phỏng batch lớn khi VRAM hạn chế. |
| Early stopping | Dừng khi dev metric không cải thiện để giảm overfitting. |
| Overfitting | Model nhớ train/dev quá mức và tổng quát kém sang private test. |
| LoRA | Fine-tuning bằng adapter hạng thấp, tiết kiệm tài nguyên. |
| Beam search | Chiến lược giữ nhiều chuỗi ứng viên khi giải mã. |
| SacreBLEU | BLEU được chuẩn hóa để kết quả dễ tái lập. |
| chrF++ | Metric so khớp chủ yếu theo ký tự và bổ sung thông tin từ. |
| COMET | Metric neural đánh giá chất lượng dịch theo ngữ nghĩa. |
| Glossary | Danh sách thuật ngữ và cách dịch mong muốn. |
| Back-translation | Dùng model dịch dữ liệu đơn ngữ để tạo cặp huấn luyện synthetic. |
| Synthetic data | Dữ liệu do model/quy tắc tạo ra thay vì do người dịch trực tiếp. |
| Quantization | Giảm độ chính xác số của trọng số để giảm memory hoặc tăng tốc. |
| Latency | Thời gian xử lý một request hoặc document. |
| Throughput | Lượng token/request xử lý được trong một đơn vị thời gian. |
| Peak VRAM | Mức bộ nhớ GPU cao nhất trong quá trình chạy. |
| Docker | Gói môi trường chạy gồm code, dependency và model. |
| Offline inference | Inference không gọi mạng hoặc dịch vụ bên ngoài. |
| Pareto frontier | Các lựa chọn mà muốn cải thiện một tiêu chí phải đánh đổi tiêu chí khác, ví dụ chất lượng và tốc độ. |
