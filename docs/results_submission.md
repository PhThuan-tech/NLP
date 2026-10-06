# Tạo bài nộp results.csv — Public / Private Test

Quy trình này thực hiện theo hướng dẫn CSV/ZIP bạn cung cấp ngày 05/10/2026.
Không cần huấn luyện lại, tạo dataset mới hoặc merge adapter trước khi dịch.

## 1. File nào cần nộp?

```text
submission.zip
└── results.csv
```

CSV UTF-8 có đúng ba cột `sample_id,direction,translation`. Giữ nguyên ID;
direction dùng `en-vi` hoặc `vi-en`. Public có 50 cặp tài liệu, dịch cả hai chiều
để tạo **100 dòng**. Private có 100 tài liệu, mỗi tài liệu chỉ dịch chiều được
cung cấp, cũng tạo **100 dòng**. Không thêm index hoặc metadata vào CSV.

Code kiểm tra số dòng, tập ID/chiều, trùng ID/chiều, prediction rỗng, encoding,
quoting và vị trí `results.csv` trong ZIP. Dấu phẩy, dấu ngoặc kép và xuống dòng
được ghi bằng thư viện CSV, không nối chuỗi thủ công.

## 2. Chuẩn bị Kaggle: bốn Input

Gói project đã tạo: `dist/NLP_results_submission_kaggle.zip`. Gói này chứa code,
notebook, **CSV public gốc** và hai adapter `best_model` lấy từ `modelAI/`.
Không chứa base weights, checkpoint/optimizer hoặc dữ liệu train/dev.

Add Input gồm:

| File trên máy local | Nội dung |
|---|---|
| `dist/NLP_results_submission_kaggle.zip` | Project mới, CSV nguồn, hai adapter đã train |
| `offline_training_assets/vinai-translate-en2vi-v2.zip` | Base EN→VI offline đã dùng khi train |
| `offline_training_assets/vinai-translate-vi2en-v2.zip` | Base VI→EN offline đã dùng khi train |
| `offline_training_assets/vinai-training-wheelhouse-py313-linux.zip` | Thư viện Linux Python 3.13 offline |

Nếu ba asset offline cuối đã nằm trong Kaggle Dataset, thêm lại các Input đó;
không cần upload lần nữa. Có thể dùng thư mục đã giải nén thay cho ZIP.
Base snapshot phải có `offline_model_manifest.json` đúng repo/revision/SHA256.
Không cần LaBSE hoặc `NLP_v3_frozen.zip` cho bước dịch bài nộp.

## 3. Chạy Public Test

1. Import `notebooks/06_results_submission_kaggle.ipynb` vào Kaggle.
2. Bật GPU; Internet OFF. Add đủ bốn Input phía trên.
3. Chạy các cell theo thứ tự từ đầu, trong session mới.
4. Giữ `PHASE='public'`, `SOURCE_COLUMN=None`, `BATCH_SIZE=8`.
5. Giữ `RUN_FULL=True`; smoke một tài liệu mỗi chiều là tùy chọn.
6. Chờ log lần lượt `DOCUMENT en-vi ...`, `DOCUMENT vi-en ...`; mỗi tài liệu
   hoàn thành được lưu riêng. Không có bước train, preflight training hoặc sweep.
7. Cell cuối phải báo `status: passed`, `rows: 100`, mỗi chiều 50 dòng.
8. Tải **`/kaggle/working/results_submission/results_public/submission.zip`**.
   Upload chính file này lên trang chấm. Có thể tải thêm `evaluation_report.json`
   và `results.csv` để lưu và đọc bản dịch; report không nằm trong ZIP bài nộp.

Thời gian phụ thuộc GPU và chiều dài nguồn. Notebook không cung cấp ước lượng
chưa đo. Nếu session bị ngắt, giữ thư mục output và chạy lại cell full với cùng
Input/model/config/code/batch size: tài liệu đã xong được đọc từ cache đã kiểm
checksum. Nếu Kaggle mất `/kaggle/working`, cần giữ bản backup thư mục output;
cache không tự tồn tại qua session bị xóa. Nếu OOM, đổi `BATCH_SIZE=4` và chọn
`RUN_DIR` mới; không trộn cache của các cấu hình khác nhau.

Khi ZIP cuối đã có, chạy lại cell full sẽ chuyển đến phần kiểm tra/tải, không ghi
đè bài nộp. Khi chủ động tạo một run mới, chọn đường dẫn output mới.

## 4. Model, cấu trúc tài liệu và phạm vi kiểm tra

Sử dụng hai adapter đã chốt, base revision cố định và config trong
`submission/configs/en2vi.json`, `submission/configs/vi2en.json`:

| Chiều | Beam | Length penalty | Max length |
|---|---:|---:|---:|
| EN→VI | 2 | 1.1 | 512 |
| VI→EN | 4 | 1.1 | 512 |

Không bật glossary hoặc các nhánh pipeline thử nghiệm chưa có bằng chứng full-dev.
Không dùng điểm public/private để chọn lại checkpoint, decoding hoặc thuật ngữ.

Đầu vào là **toàn bộ CSV public gốc**, không phải các segment v3 đã lọc semantic.
Parser giữ vị trí heading, list, bảng, emphasis, URL, code inline và xuống dòng.
Các phần văn bản được dịch riêng và ráp lại vào vị trí nguồn; nội dung model sinh
không được phép trở thành cú pháp Markdown mới. Những dòng legal header thụt lề
được dịch và giữ thụt lề. Code fence, HTML và front matter được giữ nguyên như
khối cú pháp; public hiện tại không có các khối này. Nếu private chứa văn xuôi
pháp lý trong HTML/front matter, cần kiểm tra parser trước khi chạy để tránh giữ
nguyên nội dung cần dịch. Span dài được chia theo token, không truncation; output
rỗng hoặc chạm giới hạn token được thử chia nhỏ một lần, thất bại sẽ dừng run.

Log và checksum giúp kiểm tra đủ các span nguồn và file đầu ra. Các kiểm tra đó
không chứng minh mọi điều khoản đã dịch chính xác; đọc thử tài liệu dài và bảng
trước khi nộp. Việc dịch từng span có thể ảnh hưởng ngữ cảnh giữa các dòng hoặc
các phần có emphasis; không có cam kết điểm số trước khi chạy đầy đủ trên GPU.

Prediction public cũ gồm 1.837 segment mỗi chiều **không dùng để tạo ZIP này**:
lọc semantic đã loại một số cặp nguồn. Các ZIP sweep dev cũng không phải bài nộp.

## 5. Metric theo yêu cầu mới

`evaluation_report.json` tính trên tài liệu hoàn chỉnh:

- Corpus BLEU: tokenizer `13a`, smoothing `exp`.
- chrF: character order 6, beta 2, **word order 0**. Đây là chrF, khác chrF++
  (`word_order=2`) trong report thực nghiệm trước đây.
- Tính riêng `en-vi` và `vi-en`, sau đó lấy trung bình cộng hai điểm cho từng metric.
  Report có signature SacreBLEU và phiên bản thư viện.

Không so trực tiếp điểm segment đã lọc với điểm toàn tài liệu. Điểm local là
ước lượng theo cấu hình metric được cung cấp; điểm chính thức do trang chấm quyết
định. Private không có reference nên code chỉ kiểm tra submission, không bịa điểm.

## 6. Khi nhận Private Test

Trong notebook đổi:

```python
PHASE = 'private'
INPUT_CSV = Path('/kaggle/input/<private-dataset>/<private-file>.csv')
SOURCE_COLUMN = 'source'  # thay bằng đúng tên cột văn bản nguồn nếu khác
RUN_DIR = WORKING_ROOT/'results_private'
```

Đầu vào phải có `sample_id`, `direction` và cột nguồn. Code có thể tự nhận đúng
một trong `source`, `source_markdown`, `text`, `markdown`, `input`; nếu schema khác
hoặc có nhiều cột ứng viên, chỉ rõ `SOURCE_COLUMN`. Giữ nguyên direction được
cung cấp. Schema private thực tế chưa được phát hành; cần đối chiếu file khi có.
Chạy cell chọn phase và full lại, không reuse cache public. File nộp là
`results_private/submission.zip`, đủ 100 dòng theo chiều trong private input.

## 7. CLI và kiểm tra lại ZIP

Chạy từ gốc project, sau khi đặt `VINAI_EN2VI_MODEL_DIR` và
`VINAI_VI2EN_MODEL_DIR` tới hai snapshot offline:

```bash
python scripts/build_results_submission.py \
  --input data/test/en-vi-public_test.csv --phase public \
  --en2vi-model /path/to/en2vi/best_model \
  --vi2en-model /path/to/vi2en/best_model \
  --output-dir dist/public_results --resume

python scripts/build_results_submission.py \
  --input data/test/en-vi-public_test.csv --phase public \
  --validate-zip dist/public_results/submission.zip
```

Lệnh validate không cần GPU hoặc load weights. Đóng gói lại Input project sau
khi sửa code:

```powershell
python scripts/create_results_submission_notebook.py
python scripts/package_results_submission.py --output dist/NLP_results_submission_kaggle_v2.zip
```

Notebook tìm `NLP_results_submission_kaggle*.zip`; nếu Kaggle tự giải nén Dataset,
notebook tự tìm `bundle_manifest.json` đúng loại rồi copy project vào working.
Docker/export model vẫn có trong repo để phục vụ protocol service nếu cần;
file Docker, ZIP model hoặc ZIP project không phải file upload của phase CSV này.
