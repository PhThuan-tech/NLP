# VLSP 2026 Legal Machine Translation Challenge

Tài liệu này tóm tắt yêu cầu của bài thi và checklist đóng gói hệ thống. Nguồn
chính thức: <https://vlsp.org.vn/vlsp2026/eval/mt_challenge> (đối chiếu lần cuối
ngày 2026-10-04). Nếu trang chính thức được cập nhật, nội dung mới trên trang đó
được ưu tiên hơn tài liệu nội bộ này.

## 1. Bài toán

- Dịch tài liệu pháp lý theo cả hai chiều English → Vietnamese và Vietnamese →
  English.
- Input là tài liệu Markdown mã hóa UTF-8.
- Output là toàn bộ tài liệu đã dịch, cũng ở dạng Markdown UTF-8.
- Mô hình cuối cùng phải nhỏ hơn 3B tham số.
- Được dùng pretrained model, public dataset, additional pre-training,
  fine-tuning và data augmentation.
- Inference phải chạy local bằng model đã nộp; không được gọi API/dịch vụ online.

Với dữ liệu pháp lý, cần ưu tiên độ trung thành về quyền, nghĩa vụ, điều kiện và
ngoại lệ; bảo toàn Điều/Khoản, số hiệu, con số và tính nhất quán thuật ngữ trên
toàn document.

## 2. Dữ liệu và mốc thời gian do ban tổ chức công bố

| Ngày | Mốc |
|---|---|
| 18/09/2026 | Training data |
| 25/09/2026 | Public test |
| 09/10/2026 | Private test |
| 15/10/2026 | Công bố kết quả |
| 25/10/2026 | Nộp paper |
| 05/11/2026 | Thông báo chấp nhận |
| 12/11/2026 | Camera-ready/proceedings |
| 15/11/2026 | Workshop |

Development, public test và private test đều thuộc legal domain. Private test
chỉ có document nguồn English hoặc Vietnamese; bản dịch tham chiếu được giữ kín.
Trang chính thức cho phép dùng automatic metric trên public test để quyết định hệ
thống nào sẽ nộp. Không dùng private test để chọn checkpoint hoặc decoding.

## 3. Đánh giá

Hệ thống được đánh giá bằng automatic metrics và LLM-based evaluation. Các tiêu
chí đã công bố gồm:

1. Chất lượng dịch, ví dụ SacreBLEU.
2. Độ đúng của thuật ngữ pháp lý.
3. Tính nhất quán thuật ngữ.
4. Độ chính xác/trung thành về ý nghĩa pháp lý.
5. Thời gian inference/response trong môi trường chuẩn hóa.
6. Peak memory khi inference.

Ban tổ chức chưa công bố trọng số chi tiết. Trong repo này, BLEU/chrF++ chỉ là
proxy; quality gate cho lặp, độ dài, số và legal identifier không thay thế điểm
chính thức.

## 4. Yêu cầu nộp hệ thống chính thức

### 4.1 Docker image

Phải nộp một Docker image hoạt động được, thỏa các điều kiện:

- self-contained;
- chứa cả model và mọi dependency;
- chạy offline;
- code inference không dùng dịch vụ/API online.

### 4.2 Bash wrapper

Bài nộp phải kèm Bash script để đọc input, gửi tài liệu vào Docker service,
nhận bản dịch và ghi output. Script nhận đúng ba tham số theo thứ tự:

```text
1. Host:port web path của Docker image
2. Đường dẫn file input
3. Đường dẫn file output
```

Ban tổ chức khuyến khích in ra stdout các thống kê như tổng thời gian, số câu
trung bình/giây và số từ trung bình/giây.

### 4.3 Lưu trữ và checksum

- Nén hệ thống bằng định dạng phổ biến: `.tar.gz`, `.tar.bz2`, `.7z`, `.rar`
  hoặc `.zip`.
- Cung cấp MD5 checksum của file đã nén.
- Đặt file trên cloud storage và cấp đúng quyền để ban tổ chức tải được.
- Có thể nộp nhiều lần; chỉ lần nộp cuối cùng được đánh giá.

## 5. Hiện thực đã chuẩn bị trong repo

| Thành phần | Vai trò |
|---|---|
| `submission/Dockerfile` | Image CUDA chứa source, dependency và hai model |
| `submission/translate.sh` | Wrapper đúng ba tham số, ghi output nguyên tử và log tốc độ |
| `src/vinai_baseline/service.py` | HTTP service offline, hỗ trợ cả hai chiều |
| `submission/configs/*.json` | Cấu hình generation dành riêng cho image |
| `scripts/package_submission.ps1` | Tạo build context chuẩn Linux và MD5 |
| `submission/export_image.sh` | Xuất image `tar.gz` và tạo `MD5SUMS` |
| `submission/README.md` | Quy trình merge, build, test và export cụ thể |

Service có các endpoint:

- `GET /health`
- `POST /translate`
- `POST /translate/en2vi`
- `POST /translate/vi2en`

`/translate` tự nhận diện ngôn ngữ nguồn trên toàn document. Endpoint tường
minh hoặc biến `TRANSLATION_DIRECTION` nên được dùng khi protocol chính thức cho
biết chiều dịch. Image lazy-load một chiều tại một thời điểm để giới hạn VRAM.

## 6. Việc cần làm trước khi nộp

### Sau khi train VI→EN

1. Chạy quality gate trên subset, sau đó full dev.
2. Chọn checkpoint/decoding bằng dev, không chọn theo private test.
3. Merge adapter EN→VI epoch 2 đã chọn thành model hoàn chỉnh.
4. Merge adapter VI→EN đã chọn thành model hoàn chỉnh.
5. Chạy `scripts/package_submission.ps1` với hai thư mục merged model.
6. Build Docker image và smoke test cả hai chiều bằng Markdown có tiêu đề, danh
   sách, bảng, số và Điều/Khoản.
7. Kiểm tra khi offline; log không được tải Hugging Face hoặc gọi Internet.
8. Đo tổng runtime, throughput và peak VRAM trên hardware gần môi trường chấm.
9. Xuất đúng image đã test, tạo/kiểm tra lại MD5 sau khi tải từ cloud.
10. Xác minh link có thể tải khi không đăng nhập trước khi gửi form.

Không đưa vào image cuối: dataset train/dev, optimizer checkpoint, notebook,
log, prediction có reference, cache hoặc virtual environment.

## 7. Những chi tiết trang chính thức chưa xác định

Tính đến 2026-10-02, trang chưa nêu rõ:

- schema HTTP và endpoint chính xác;
- chiều dịch được truyền bằng URL, header, tham số hay suy ra từ input;
- cổng bắt buộc;
- cấu hình GPU/RAM và timeout chấm;
- ban tổ chức muốn image archive hay Docker build context;
- giới hạn kích thước archive;
- quy tắc bắt buộc để bảo toàn Markdown.

Vì vậy không giả định các chi tiết này là luật thi. Hiện thực trong repo hỗ trợ
nhiều cách chỉ định chiều, nhưng cần cập nhật wrapper/service nếu ban tổ chức
phát hành protocol cuối cùng. Thay đổi protocol triển khai không yêu cầu train
lại model.
