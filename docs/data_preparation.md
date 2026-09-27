# Data preparation pipeline

## Mục tiêu

Pipeline biến CSV document-level thành dữ liệu JSONL có thể dùng cho bước
tokenization và fine-tuning, đồng thời bảo toàn một đường kiểm toán từ mỗi
segment về tài liệu gốc.

Tài liệu này dành cho thành viên mới của nhóm. Sau khi đọc xong, mọi người cần
hiểu được dữ liệu gốc có hình dạng gì, vì sao phải căn chỉnh document, cách
chống rò rỉ train/dev, tiêu chí chấp nhận segment và file nào thực sự nên dùng
để fine-tune.

## Tóm tắt dễ hiểu

Dữ liệu cuộc thi gồm các **tài liệu pháp lý hoàn chỉnh**, không phải các cặp câu
ngắn đã được căn sẵn. Một document có thể dài hàng chục đến hàng trăm nghìn ký
tự. Mô hình dưới 3B tham số không thể xử lý an toàn toàn bộ document trong một
lần, nên ta phải thực hiện chuỗi công việc sau:

```text
CSV chứa document song ngữ
    ↓
Kiểm tra và chuẩn hóa
    ↓
Loại trùng, chia train/dev ở cấp document
    ↓
Tách document thành các khối pháp lý có nghĩa
    ↓
Căn chỉnh khối tiếng Anh với khối tiếng Việt
    ↓
Loại các cặp đáng ngờ
    ↓
Đóng gói thành segment cho hai chiều dịch
    ↓
Lọc tiếp bằng semantic similarity
    ↓
Tokenize và fine-tune
```

Điểm quan trọng nhất là **không đồng nhất xuống dòng với một câu**. Nhiều dòng
chỉ bị ngắt do chiều rộng trang. Nếu cắt theo từng dòng, source và target sẽ
lệch nhau nhanh chóng.

## Dữ liệu đầu vào

```text
data/train/en-vi-train.csv
data/test/en-vi-public_test.csv
```

| Cột | Ý nghĩa |
|---|---|
| `sample_id` | Định danh document, ví dụ `Bat_dong_san/1`. |
| `category` | Lĩnh vực pháp lý của document. |
| `english_path` | Đường dẫn logic của bản tiếng Anh. |
| `vietnamese_path` | Đường dẫn logic của bản tiếng Việt. |
| `english_markdown` | Toàn bộ nội dung document tiếng Anh. |
| `vietnamese_markdown` | Toàn bộ nội dung document tiếng Việt. |

Hai cột nội dung chứa nhiều dòng và dấu phẩy bên trong một ô CSV. Vì vậy phải
đọc bằng CSV parser như `pandas.read_csv`; không dùng `readlines()` hoặc coi
mỗi dòng vật lý là một record.

Các bước chạy theo đúng thứ tự:

1. Đọc CSV bằng parser hỗ trợ quoted multiline fields.
2. Chuẩn hóa Unicode NFC, line ending và khoảng trắng cuối dòng.
3. Hash văn bản đã chuẩn hóa và loại cặp song ngữ trùng hoàn toàn.
4. Gom các tài liệu trùng một phía vào cùng duplicate group.
5. Chia train/dev theo duplicate group, có stratify theo `category`.
6. Nối các dòng bị wrap thành logical blocks.
7. Nhận diện `Article/Điều`, `Chapter/Chương`, danh sách và heading.
8. Căn chỉnh block theo thứ tự, tỷ lệ độ dài, con số và cấu trúc pháp lý.
9. Loại alignment điểm thấp hoặc quá dài.
10. Đóng gói các alignment liên tiếp thành chunk huấn luyện.
11. Xuất riêng hai chiều `en2vi` và `vi2en` cùng báo cáo chất lượng.

## Giải thích chi tiết từng bước

### 1. Kiểm tra schema và dữ liệu rỗng

Pipeline yêu cầu đủ sáu cột đầu vào và chuyển chúng về kiểu chuỗi. Nếu một
trường bắt buộc bị rỗng, pipeline dừng thay vì tạo source hoặc target rỗng cho
model.

### 2. Chuẩn hóa an toàn

Các thay đổi được phép gồm:

- chuẩn hóa Unicode về NFC;
- đổi `CRLF`/`CR` thành `LF` (`\n`);
- loại BOM và zero-width space;
- xóa tab/khoảng trắng ở cuối dòng;
- gộp nhiều dòng trống liên tiếp.

Pipeline không lowercase, không bỏ dấu tiếng Việt, không xóa dấu câu và không
tự đổi số hiệu văn bản vì đây đều là thông tin pháp lý hoặc tín hiệu alignment.

### 3. Hash và deduplicate

Pipeline tạo SHA-256 hash cho bản Anh, bản Việt và toàn bộ cặp song ngữ. Hash là
một dấu vân tay số có độ dài cố định; nội dung giống nhau sau chuẩn hóa sẽ có
cùng hash.

Nếu toàn bộ cặp Anh–Việt trùng nhau, chỉ một record được giữ. Nếu hai record chỉ
trùng bản Anh hoặc bản Việt, chúng được đưa vào cùng `duplicate_group` để không
rơi vào hai split khác nhau.

### 4. Chia train/dev

Split được thực hiện trên document và duplicate group trước segmentation.
Pipeline dùng `sklearn.model_selection.train_test_split` trên danh sách
`duplicate_group`, với `stratify=category` và `random_state=seed`. Seed mặc định
là `67`, nên cùng dữ liệu, phiên bản scikit-learn và cấu hình sẽ tạo cùng split.
Không split trực tiếp các segment vì làm vậy có thể đưa các đoạn của cùng một
document vào cả train và dev, gây data leakage.

Public test không tham gia split và không được gộp vào train. Target trong
public test chỉ phục vụ đánh giá và chọn hệ thống.

> **Dataset nguồn:** `artifacts/processed_sklearn_seed67` được tạo bằng split
> scikit-learn với seed `67`. Baseline huấn luyện dùng bản finalization bất biến
> `artifacts/processed_clean_seed67_v2`; không trộn hai version trong một run.

### 5. Tạo logical block

Một **logical block** là đơn vị có ý nghĩa hơn một dòng vật lý. Ví dụ:

```text
The organization shall comply with this
Decree and relevant regulations.
```

được nối thành:

```text
The organization shall comply with this Decree and relevant regulations.
```

Các mốc `Article/Điều`, `Chapter/Chương`, `Section/Mục` và danh sách đánh số
được giữ làm ranh giới. Đường kẻ trang trí bị bỏ khỏi tập huấn luyện, nhưng
document chuẩn hóa đầy đủ vẫn được lưu trong file document-level.

### 6. Structural alignment

Alignment trả lời câu hỏi: “khối tiếng Anh này tương ứng với khối tiếng Việt
nào?”. Pipeline khóa trước các anchor đáng tin cậy:

```text
Article 12  ↔  Điều 12
Chapter II  ↔  Chương II
```

Giữa các anchor, pipeline thử quan hệ `1-1`, `1-2`, `2-1`, `2-2` và phép skip
khi một block chỉ có ở một phía. Vùng nhỏ dùng dynamic programming; phụ lục lớn
dùng alignment tuyến tính có lookahead để giới hạn runtime.

### 7. Quality gate và đóng gói segment

Mỗi candidate nhận điểm từ 0 đến 1. Điểm cao nghĩa là có nhiều dấu hiệu tương
ứng hơn, nhưng **không phải xác suất đúng**. Cặp dưới threshold hoặc vượt giới
hạn độ dài được đưa vào `rejected_alignments.jsonl`.

Structural score hiện được tính từ:

```text
0.50 × length compatibility
+ 0.32 × number overlap
+ 0.18 × legal structure compatibility
```

- `length compatibility`: tỷ lệ độ dài Anh–Việt có hợp lý không;
- `number overlap`: các con số quan trọng có xuất hiện ở cả hai phía không;
- `legal structure compatibility`: Article/Điều, danh sách và loại block có
  tương thích không.

Các alignment tốt liên tiếp được đóng gói thành segment trong word budget. Mỗi
segment sau đó được xuất theo hai chiều:

```text
en2vi: source=English,    target=Vietnamese
vi2en: source=Vietnamese, target=English
```

## Semantic filtering bằng LaBSE

### LaBSE là gì?

**LaBSE** là viết tắt của **Language-agnostic BERT Sentence Embedding**. Mô hình
này biến câu ở nhiều ngôn ngữ thành vector số trong cùng một không gian. Hai câu
là bản dịch của nhau thường có vector nằm gần nhau.

LaBSE không trực tiếp dịch trong pipeline này. Nó được dùng như một **semantic
quality gate**: kiểm tra xem segment tiếng Anh và segment tiếng Việt có gần nhau
về nghĩa hay không.

```text
EN: The competent authority shall issue the decision.
VI: Cơ quan có thẩm quyền ban hành quyết định.
```

Cặp trên kỳ vọng có semantic similarity cao. Nếu bản Việt nói về điều khoản
khác, similarity thường thấp và cặp sẽ bị loại.

### Cosine similarity là gì?

Cosine similarity đo độ giống về hướng giữa hai vector:

- gần `1`: rất giống trong không gian embedding;
- gần `0`: ít liên quan;
- nhỏ hơn `0`: có xu hướng đối lập.

Ngưỡng `0.72` chỉ là điểm bắt đầu. Không được hiểu rằng mọi cặp trên ngưỡng đều
đúng. Nhóm phải lấy mẫu quanh ngưỡng, kiểm tra theo category rồi mới chốt.

### Vì sao cần hai lớp lọc?

- Structural alignment mạnh ở số điều, thứ tự, con số và độ dài.
- LaBSE giúp phát hiện hai đoạn có hình thức giống nhưng khác nghĩa.
- Structural score cao vẫn có thể sai nghĩa.
- Semantic score cao vẫn có thể bỏ sót một con số hoặc điều kiện pháp lý.
- Kết hợp hai lớp cùng kiểm tra thủ công an toàn hơn dùng một lớp duy nhất.

## Chạy pipeline

Từ project root:

```powershell
python -m unittest discover -s tests -v
python -m src.data.prepare `
  --project-root . `
  --output-dir artifacts/processed_sklearn_seed67 `
  --seed 67
```

Có thể chạy semantic filtering như một thí nghiệm riêng (nên dùng GPU):

```powershell
pip install -r requirements-semantic.txt
python -m src.data.finalize `
  --input-dir artifacts/processed_sklearn_seed67 `
  --output-dir artifacts/processed_clean_labse072_seed67_v3 `
  --dataset-id legal_envi_clean_labse072_seed67_v3 `
  --semantic-model sentence-transformers/LaBSE `
  --minimum-semantic-similarity 0.72
```

Ngưỡng `0.72` là điểm khởi đầu, không phải hằng số tối ưu. Hãy lấy mẫu thủ
công theo các khoảng similarity trước khi quyết định dùng dataset thử nghiệm
này. Nếu chốt dùng semantic filter, phải tạo dataset ID mới. Baseline hiện tại
train từ `artifacts/processed_clean_seed67_v2/`.

Chạy lại và thay các file được pipeline sinh ra:

```powershell
python -m src.data.prepare `
  --project-root . `
  --output-dir artifacts/processed_sklearn_seed67 `
  --seed 67 `
  --overwrite
```

Có thể điều chỉnh quality gate:

```powershell
python -m src.data.prepare `
  --project-root . `
  --output-dir artifacts/processed_sklearn_seed67 `
  --seed 67 `
  --dev-ratio 0.10 `
  --minimum-alignment-score 0.75 `
  --maximum-chunk-words 400 `
  --overwrite
```

## Kết quả preprocessing hiện tại

- Dữ liệu gốc: 854 document train và 50 document public test.
- Loại 17 cặp tài liệu trùng hoàn toàn.
- Còn 837 document, gồm 753 train và 84 dev.
- Sinh 18.802 segment train cho mỗi chiều dịch.
- Sinh 1.899 segment dev cho mỗi chiều dịch.
- Sinh 1.212 segment public test cho mỗi chiều dịch.
- Không phát hiện exact document overlap giữa train và public test.

## Ý nghĩa các file trong `artifacts/processed_sklearn_seed67`

### Dữ liệu document-level

| File | Mục đích |
|---|---|
| `documents_train.jsonl` | 753 cặp tài liệu train sau deduplicate và chuẩn hóa. Dùng để truy vết, tạo lại segment hoặc thử preprocessing khác. |
| `documents_dev.jsonl` | 84 cặp tài liệu dev được tách độc lập ở cấp document. Dùng để đánh giá trong quá trình phát triển. |
| `documents_public_test.jsonl` | 50 cặp tài liệu public test. Chỉ dùng đánh giá và chọn hệ thống, không dùng huấn luyện. |

Mỗi dòng JSONL chứa một document cùng `sample_id`, `category`, đường dẫn gốc,
nội dung Anh–Việt, hash và duplicate group.

### Dữ liệu segment-level

| File | Mục đích |
|---|---|
| `segments_train_en2vi.jsonl` | Segment train theo chiều English → Vietnamese. |
| `segments_train_vi2en.jsonl` | Cùng tập alignment train nhưng đảo thành Vietnamese → English. |
| `segments_dev_en2vi.jsonl` | Segment dev dùng đánh giá chiều English → Vietnamese. |
| `segments_dev_vi2en.jsonl` | Segment dev dùng đánh giá chiều Vietnamese → English. |
| `segments_public_test_en2vi.jsonl` | Segment public test cho chiều English → Vietnamese; không dùng cập nhật trọng số. |
| `segments_public_test_vi2en.jsonl` | Segment public test cho chiều Vietnamese → English; không dùng cập nhật trọng số. |

Mỗi segment chứa source, target, chiều dịch, category, số từ xấp xỉ, phạm vi
block và điểm alignment để có thể truy vết về document gốc.

### File split và duplicate

| File | Mục đích |
|---|---|
| `document_splits.csv` | Ghi mỗi `sample_id` thuộc train hay dev, cùng category, hash và duplicate group. Đây là split cố định cần dùng lại trong mọi thí nghiệm. |
| `duplicate_documents.csv` | Danh sách 17 document trùng đã bị loại và `sample_id` đại diện được giữ lại. |

### Báo cáo alignment

| File | Mục đích |
|---|---|
| `alignment_by_document.csv` | Thống kê theo document: số block Anh–Việt, alignment được nhận/bị loại, số segment và điểm trung bình. Dùng tìm document bất thường. |
| `alignment_by_category.csv` | Tổng hợp alignment theo split và lĩnh vực pháp lý. Dùng phát hiện category có chất lượng căn chỉnh thấp. |
| `rejected_alignments.jsonl` | Alignment không đạt quality gate hoặc block không có bản tương ứng. Dùng audit và cải tiến aligner; không dùng để train. |

### Metadata và báo cáo tổng hợp

| File | Mục đích |
|---|---|
| `quality_report.json` | Báo cáo số document trước/sau deduplicate, phân bố split, overlap train–test, số segment và thống kê alignment. |
| `manifest.json` | Ghi thời điểm chạy, input/output, phiên bản Python/pandas/numpy, cấu hình preprocessing và số record. Dùng tái lập một lần chạy. |

## File được dùng ở từng bước

```text
Kiểm toán dữ liệu:
  document_splits.csv
  duplicate_documents.csv
  alignment_by_document.csv
  alignment_by_category.csv
  rejected_alignments.jsonl

Chạy semantic filtering tùy chọn:
  artifacts/processed_sklearn_seed67/segments_<split>_en2vi.jsonl

Fine-tuning:
  artifacts/processed_sklearn_seed67/segments_train_en2vi.jsonl
  artifacts/processed_sklearn_seed67/segments_train_vi2en.jsonl

Validation:
  artifacts/processed_sklearn_seed67/segments_dev_en2vi.jsonl
  artifacts/processed_sklearn_seed67/segments_dev_vi2en.jsonl

Public evaluation:
  artifacts/processed_sklearn_seed67/segments_public_test_en2vi.jsonl
  artifacts/processed_sklearn_seed67/segments_public_test_vi2en.jsonl
```

## Lưu ý trước khi huấn luyện

- `maximum_chunk_words` dùng whitespace word count, chưa phải tokenizer count.
- Phải chạy tokenizer của model và lọc/truncate lại theo token budget.
- Không đưa `rejected_alignments.jsonl` vào train.
- Không dùng public test để cập nhật trọng số model.
- Public test có target chỉ phục vụ đánh giá và chọn hệ thống.

## Checklist trước khi fine-tune

- [ ] Train/dev không có document hoặc duplicate group giao nhau.
- [ ] Public test không được đưa vào train.
- [ ] Đã xem phân bố document và segment theo category.
- [ ] Đã kiểm tra các document có rejection rate cao nhất.
- [ ] Đã lấy mẫu alignment ở nhiều khoảng structural score.
- [ ] Nếu dùng biến thể semantic: đã chạy lọc và lấy mẫu thủ công quanh threshold.
- [ ] Đã phân tích tokenizer của model được chọn.
- [ ] Không có target bị truncate âm thầm.
- [ ] Đã lưu manifest, config, seed và checksum của dataset version.

## Giới hạn cần hiểu đúng

1. Structural score cao không đảm bảo hai đoạn đồng nghĩa.
2. Semantic score cao không đảm bảo mọi con số hoặc điều kiện đều đúng.
3. Word count chỉ là ước lượng; mỗi tokenizer tạo số token khác nhau.
4. Alignment tự động không thay thế hoàn toàn kiểm tra thủ công.
5. Tối ưu lặp đi lặp lại trên public test có thể làm hệ thống overfit public
   test và tổng quát kém trên private test.

## Thuật ngữ nhanh

| Thuật ngữ | Nghĩa và mục đích |
|---|---|
| Document-level | Dữ liệu ở cấp toàn bộ văn bản pháp luật. |
| Segment | Đoạn song ngữ đủ nhỏ để model xử lý. |
| Chunk | Một hoặc nhiều block được đóng gói trong giới hạn độ dài. |
| Logical block | Khối nội dung được nối từ dòng vật lý và tách theo cấu trúc pháp lý. |
| Alignment | Xác định phần tiếng Anh tương ứng với phần tiếng Việt. |
| Anchor | Mốc cấu trúc đáng tin như `Article 5 ↔ Điều 5`. |
| Dynamic programming | Kỹ thuật tìm chuỗi quyết định có tổng chi phí tốt nhất. |
| Quality gate | Điều kiện tối thiểu để record được đi tiếp. |
| Threshold | Ngưỡng điểm dùng nhận hoặc loại record. |
| Duplicate | Bản ghi trùng toàn bộ hoặc trùng một phía. |
| Data leakage | Dữ liệu dev/test xuất hiện trong train, làm metric cao giả tạo. |
| Stratified split | Chia dữ liệu sao cho tỷ lệ category giữa các split gần nhau. |
| `random_state` | Seed truyền cho scikit-learn để phép chia có thể tái lập. |
| Hash | Dấu vân tay số của nội dung, dùng phát hiện trùng và kiểm tra toàn vẹn. |
| Unicode NFC | Dạng chuẩn Unicode giúp cùng một chữ có biểu diễn nhất quán. |
| JSONL | Mỗi dòng là một JSON object, phù hợp xử lý tuần tự dữ liệu lớn. |
| LaBSE | Model embedding đa ngôn ngữ dùng đo mức gần nghĩa, không trực tiếp dịch. |
| Embedding | Vector số biểu diễn nội dung/ngữ nghĩa của văn bản. |
| Cosine similarity | Chỉ số đo độ giống về hướng giữa hai embedding. |
| Tokenizer | Bộ chuyển văn bản thành token ID cho model. |
| Token budget | Số token tối đa cho source hoặc target. |
