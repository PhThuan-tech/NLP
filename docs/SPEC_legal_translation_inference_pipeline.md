# 📘 SPEC: Lớp inference bảo toàn cấu trúc pháp lý cho dịch VI→EN

| Mục | Nội dung |
|---|---|
| Phiên bản | v1.0 (2026-10-05) |
| Đối tượng đọc | Codex (agent triển khai) |
| Mục tiêu | Giảm 3 lỗi đã quan sát: **dịch thiếu nội dung**, **mất cấu trúc Markdown**, **thuật ngữ/viện dẫn không nhất quán** |
| Cách tiếp cận | Thêm lớp xử lý quanh model hiện có (parse → chunk → glossary → dịch → kiểm tra → dịch lại có chọn lọc → ghép → report) |
| Quy ước ngôn ngữ | Spec bằng tiếng Việt. Tên module, biến, key trong config/report, log, comment trong code: **tiếng Anh** |

**Ký hiệu ưu tiên:** 🔴 P0 bắt buộc · 🟠 P1 nên có · 🟡 P2 tùy chọn · 🆕 bổ sung so với kế hoạch ban đầu của Codex · ✅ tiêu chí nghiệm thu · ⛔ cấm

> Hãy đọc hết tài liệu trước khi viết code. Mục 3 (cách làm việc) và mục 14 (checklist khám phá repo) cần làm trước tiên.

---

## 1. Bối cảnh và mục tiêu

Hệ thống hiện dịch Markdown pháp lý VI→EN bằng model VinAI kèm adapter đã train. Output hiện có ba lỗi chính:

| Lỗi | Biểu hiện | Nguyên nhân dự đoán (cần kiểm chứng ở M0) |
|---|---|---|
| Thiếu nội dung | Mất khoản, câu, hoặc output dừng sớm (ví dụ kết thúc ở `/ND`) | Đưa khối quá dài; hết `max_new_tokens`; EOS sớm; `no_repeat_ngram_size` cấm lặp pháp lý hợp lệ |
| Mất cấu trúc Markdown | Mất bullet, đổi thứ tự khoản, bảng thành đoạn văn | Để model tự tái tạo Markdown |
| Thuật ngữ/viện dẫn chưa nhất quán | `Điều`/`Khoản`/tên cơ quan dịch khác nhau giữa các nơi | Không có kiểm soát thuật ngữ khi inference |

Mục tiêu đo được:

1. 🔴 Bảo toàn cấu trúc: **100%** đơn vị nguồn có bản dịch và được ghép lại đúng vị trí (kiểm chứng bằng code).
2. 🔴 Giảm tỷ lệ đơn vị bị dịch thiếu, cụt, lặp suy biến so với baseline (đo ở M0 và M6).
3. 🟠 Tăng độ nhất quán thuật ngữ/viện dẫn.
4. 🟠 Không làm giảm BLEU/chrF++ so với baseline trên tập dev cố định.

---

## 2. Ràng buộc bất biến

- ⛔ Không train lại, không fine-tune thêm, không sửa weight hay file adapter.
- ⛔ Không sửa, không tạo lại dataset frozen. Glossary là tài nguyên inference **riêng**, nằm ngoài dataset.
- ⛔ Không đổi giao diện vào/ra của service Docker hiện tại (đường dẫn, định dạng file, tham số).
- ⛔ Không đổi cấu hình decoding chính thức khi chưa có số liệu A/B trên dev (mục 10).
- ⛔ Không tự thêm nội dung không có trong nguồn. Không xóa nội dung nguồn.
- ⛔ Không chèn thuật ngữ glossary vào cuối câu chỉ để tăng "term coverage". Không thay thế từ đa nghĩa trên toàn document.
- 🔴 Mọi bước chạy deterministic: cố định seed, beam search, không sampling.

---

## 3. Cách làm việc của agent

1. 🔴 Làm **M0** trước (mục 12): đọc repo, điền checklist mục 14, ghi vào `docs/ASSUMPTIONS.md`. Nếu thiếu thông tin quan trọng không suy ra được từ repo, ghi giả định hợp lý và tiếp tục, chỉ dừng hỏi người dùng với các mục đánh dấu **[HỎI]** ở mục 14.
2. 🔴 Mỗi milestone là một nhóm commit riêng, test xanh mới sang milestone sau.
3. 🔴 Mọi tham số (ngưỡng, token budget, bật/tắt từng tầng) nằm trong **một file config** (YAML/JSON). Không hardcode.
4. 🔴 Mỗi tầng có **feature flag** để tắt riêng, phục vụ ablation (mục 11).
5. 🔴 Khi spec mâu thuẫn với repo thực tế: ưu tiên ràng buộc mục 2, ghi lại mâu thuẫn trong `docs/ASSUMPTIONS.md`.
6. 🟠 Ngưỡng nào chưa có số trong spec thì **hiệu chỉnh từ dữ liệu train/dev** (percentile), lưu giá trị và cách tính vào config/report. Không đặt số tùy ý.

---

## 4. Kiến trúc tổng quan

```text
Markdown nguồn
      ↓
[S0] Baseline & phân loại lỗi (chạy một lần, offline)           🆕
      ↓
[S1] Parser: tách cấu trúc, giữ marker, placeholder inline      (mở rộng)
      ↓
[S2] Chunker: đơn vị pháp lý, giới hạn token                    (mở rộng)
      ↓
[S3] Glossary: nhận diện thuật ngữ theo cụm và miền
      ↓
[S4] Dịch: VinAI + adapter hiện có, decoding đã A/B
      ↓
[S5] Validator: đầy đủ, thuật ngữ, viện dẫn, số, lặp, cụt
      ↓
[S6] Retry có chọn lọc: dịch lại đúng đơn vị lỗi, chọn ứng viên tốt hơn   (mở rộng)
      ↓
[S7] Reassembler: ghép vào cấu trúc Markdown gốc + kiểm tra bất biến
      ↓
[S8] Output + report kiểm tra
```

| Stage | Module gợi ý | Ưu tiên | Milestone |
|---|---|---|---|
| S0 | `eval/error_taxonomy` | 🔴 🆕 | M0 |
| S1 | `pipeline/md_parser` | 🔴 | M1 |
| S7 | `pipeline/reassembler` | 🔴 | M1 |
| S2 | `pipeline/chunker` | 🔴 | M2 |
| S4 | `pipeline/translator` | 🔴 | M3 |
| S5 | `pipeline/validator` | 🔴 | M3 |
| S3 | `pipeline/glossary` | 🟠 | M4 |
| S6 | `pipeline/retry` | 🟠 | M4 |
| S8 | `pipeline/report` | 🔴 | M5 |
| Tích hợp | service Docker | 🔴 | M5 |
| Đánh giá | `eval/ablation` | 🔴 | M6 |

Cấu trúc thư mục chỉ là gợi ý. Nếu repo đã có quy ước thì theo repo.

---

## 5. Mô hình dữ liệu dùng chung

### 5.1 TranslationUnit (đơn vị dịch)

| Trường | Ý nghĩa |
|---|---|
| `unit_id` | ID ổn định, ví dụ `{doc_id}:{số thứ tự}` |
| `doc_id`, `order_index` | Tài liệu và vị trí trong tài liệu, không đổi sau khi gán |
| `kind` | `title`, `heading`, `preamble` (Căn cứ…), `article_heading`, `clause`, `point`, `list_item`, `paragraph`, `table_cell`, `signature`, `other` |
| `prefix` | Marker giữ nguyên: `## `, `2. `, `a) `, `- `… |
| `src_text` | Nội dung nguồn cần dịch (không gồm prefix) |
| `src_masked` | `src_text` sau khi thay span inline bằng placeholder |
| `placeholders` | Bản đồ placeholder → nội dung gốc (URL, code, markup) |
| `context` | Ngữ cảnh phụ không được dịch ra output (tiêu đề cột, tên Điều cha) |
| `domain` | Miền được chọn cho unit/document |
| `glossary_hits` | Các entry glossary khớp trong `src_text` |
| `src_tokens` | Số token nguồn theo tokenizer của model |
| `translations` | Danh sách ứng viên: `{text, stage (first/retry), strategy, gen_finished_by_eos, checks}` |
| `final` | Ứng viên được chọn |
| `status` | `OK`, `RETRIED_FIXED`, `RETRIED_UNFIXED`, `SOURCE_KEPT` |

### 5.2 Mức nghiêm trọng của lỗi kiểm tra

| Mức | Dùng cho | Trọng số chọn ứng viên |
|---|---|---|
| `error` | Rỗng, sai ngôn ngữ, mất mã văn bản/số, placeholder hỏng, cụt do hết token | 3 |
| `warning` | Ngắn bất thường, thiếu thuật ngữ, lặp nghi ngờ, ngoại lệ định dạng số | 1 |
| `info` | Chỉ ghi nhận | 0 |

---

## 6. S0 – Baseline và phân loại lỗi 🔴 🆕

**Mục đích:** biết lỗi nào chiếm nhiều nhất để ưu tiên và để có mốc so sánh. Spec ban đầu chưa định lượng ba lỗi.

**Đầu vào:** tập dev cố định (xem mục 14), output hiện tại của hệ thống (baseline).

**Việc cần làm:**
1. Chạy hệ thống hiện tại trên toàn bộ dev, lưu output nguyên trạng làm `baseline`.
2. Với mỗi cặp (nguồn, baseline), gán nhãn tự động theo taxonomy dưới đây (dùng các hàm kiểm tra của S5 khi đã có, hoặc heuristic tạm thời).
3. Xuất bảng thống kê và danh sách ví dụ lỗi cụ thể (tối thiểu 20 ví dụ mỗi loại nếu có) vào `reports/baseline_error_taxonomy.md`.
4. Tính BLEU và chrF++ baseline bằng sacreBLEU, ghi lại signature.

**Taxonomy lỗi:**

| Mã | Lỗi | Cách phát hiện |
|---|---|---|
| E1 | Output rỗng / sai ngôn ngữ | Rỗng; tỷ lệ ký tự tiếng Việt có dấu cao |
| E2 | Thiếu khoản/câu/list item | So số đơn vị cấu trúc và số câu nguồn với output |
| E3 | Cụt/dừng sớm | Kết thúc ở cụm dang dở (`/ND`, `of the`, `and`) hoặc không có dấu kết thúc khi nguồn có |
| E4 | Lặp suy biến | n-gram lặp liên tiếp ngoài nguồn |
| E5 | Mất cấu trúc Markdown | Số heading/bullet/hàng bảng khác nguồn |
| E6 | Sai/mất mã văn bản, viện dẫn, số | So khớp thực thể (mục 9.3) |
| E7 | Thuật ngữ không nhất quán | Entry glossary đã duyệt không xuất hiện đúng |

**Điều tra nguyên nhân output cụt `/ND` (bắt buộc ở M0):** chọn tối thiểu 10 unit bị cụt, chạy lại từng unit và ghi: (a) token cuối có phải EOS không; (b) có chạm `max_new_tokens` không; (c) có phụ thuộc `no_repeat_ngram_size` không. Kết quả quyết định thứ tự thử nghiệm ở mục 10. Không giả định nguyên nhân.

✅ **Nghiệm thu:** có `baseline_error_taxonomy.md` với số liệu từng mã lỗi, có file output baseline, có BLEU/chrF++ baseline, có kết luận về nguyên nhân cụt.

---

## 7. S1 – Parser cấu trúc Markdown 🔴

**Mục đích:** model chỉ nhận nội dung chữ; code giữ toàn bộ cấu trúc.

### 7.1 Thành phần phải xử lý

| Thành phần | Cách xử lý |
|---|---|
| Heading `#`…`######` | Giữ prefix, dịch phần chữ |
| Số thứ tự/list: `1.`, `a)`, `-`, `*`, `+`, lồng nhau | Giữ prefix và mức thụt lề, dịch phần chữ |
| Bảng pipe | Giữ hàng, cột, hàng căn lề (`---`, `:---:`); dịch từng ô (xem 8.4) |
| Code block, inline code | Giữ nguyên, không dịch |
| URL, link destination, ảnh | Giữ nguyên URL; dịch nhãn hiển thị và alt text |
| Block quote `>` | Giữ prefix, dịch nội dung |
| HTML block, front matter, đường kẻ `---` | Giữ nguyên |
| Dòng trống, xuống dòng cứng, CRLF/LF, khoảng trắng cuối dòng | Giữ nguyên |

Tự chọn thư viện parse hoặc parser dòng riêng, miễn đạt tiêu chí nghiệm thu bên dưới. Ưu tiên cách giữ được vị trí nguồn.

### 7.2 Inline markup trong câu 🆕 🔴

Spec ban đầu chỉ nói cấu trúc đầu dòng. Thực tế có `**đậm**`, `*nghiêng*`, link giữa câu, chú thích `[^1]`. Tách các span này ra dịch riêng sẽ mất ngữ cảnh và đảo trật tự từ.

**Cách làm:**
1. Thay mỗi span inline bằng **placeholder** trong `src_masked`; lưu nội dung gốc trong `placeholders`.
2. Với span có chữ cần dịch (đậm, nghiêng, nhãn link), để placeholder dạng cặp mở/đóng bao quanh chữ, để model dịch chữ bên trong. Với span không dịch (inline code, URL) dùng placeholder đơn.
3. Định dạng placeholder là tham số cần chọn bằng dữ liệu: thử tối thiểu 3 dạng (ví dụ thẻ kiểu `<1>…</1>`, ngoặc `[[1]]`, ngoặc nhọn `{1}`) trên 200 unit dev có markup, đo **tỷ lệ sống sót** (mỗi placeholder xuất hiện đúng một lần, đúng thứ tự cặp), chọn dạng tốt nhất, lưu kết quả vào `reports/placeholder_survival.md`.
4. Sau dịch, kiểm tra sống sót. Nếu hỏng, đây là lỗi `error` và kích hoạt retry (mục 9.5, chiến lược `strip_spans`).
5. Chiến lược fallback `strip_spans`: dịch lại bản đã bỏ markup, rồi chỉ khôi phục markup khi span bao trùm toàn bộ unit (ví dụ cả câu in đậm). Với span một phần mà không khôi phục chắc chắn được thì bỏ markup của span đó và ghi `warning` trong report. Không đoán vị trí.

### 7.3 Bất biến bắt buộc

- 🔴 **Round-trip nhận dạng:** parse rồi serialize **không dịch** phải cho ra nội dung giống nguồn **từng byte**.
- 🔴 Số lượng và thứ tự các khối cấu trúc trong output bằng nguồn.
- 🔴 URL, code, mã trong placeholder không bị thay đổi.

✅ **Nghiệm thu:** round-trip 100% trên toàn bộ dev; test cho từng thành phần ở bảng 7.1; test ca khó (list lồng 3 cấp, bảng có ô trống, ô chứa `|` thoát, link trong ô bảng, ảnh, dòng CRLF, code fence chứa dấu `#`).

---

## 8. S2 – Chunker theo đơn vị pháp lý 🔴

**Mục đích:** mỗi lần gọi model nhận một đơn vị đủ ngắn để không bỏ sót, đủ dài để giữ ngữ cảnh.

### 8.1 Quy tắc chia

1. Đơn vị cơ sở là một đoạn, Điều (tiêu đề), khoản, điểm, list item, hoặc ô bảng hoàn chỉnh.
2. Phần tiêu đề dài, phần căn cứ (`Căn cứ …;`) và phần nội dung được nhận diện thành kind riêng.
3. Nếu một đơn vị vượt token budget, tách tiếp tại ranh giới câu. Với văn bản pháp lý Việt Nam, câu kết thúc bằng `.`, `;`, `:` hoặc xuống dòng, nhưng **không tách** tại: dấu chấm trong số (`1.000.000`), viết tắt (`TP.`, `Đ.`), mã văn bản (`12/2020/NĐ-CP`).
4. 🔴 **Không bao giờ cắt giữa:** cụm viện dẫn (`Điều 5 Khoản 2 Điểm a`, `Nghị định số … ngày …`), entry glossary, số, ngày, cặp ngoặc nếu còn chỗ.
5. Các đơn vị liên quan chặt (khoản ngắn liên tiếp cùng một Điều) được ghép nếu tổng vẫn dưới budget, vì chia quá nhỏ làm mất ngữ cảnh. Ghép chỉ ở mức batch gọi model; `unit_id` và vị trí ghép lại vẫn tách riêng.
6. Mỗi đơn vị có ID và vị trí cố định ngay từ lúc chunk.

### 8.2 Token budget theo phân phối train 🆕 🟠

Adapter học trên đoạn có độ dài nhất định. Inference nên gần phân phối đó.
1. Thống kê độ dài token nguồn của train (percentile 50/90/95/99) bằng tokenizer của model. Ghi vào `reports/train_length_stats.md`.
2. Đặt `target_budget` quanh p90–p95 train và không vượt giới hạn model. Lưu giá trị và lý do trong config.
3. Có `hard_budget` (giới hạn trên tuyệt đối) và `retry_budget` (nhỏ hơn, dùng khi dịch lại, mặc định bằng một nửa `target_budget`).

### 8.3 Bất biến

```text
Mọi đơn vị nguồn → có đúng một bản dịch final → được ghép lại đúng vị trí
```

Đây chỉ bảo đảm độ phủ **cấu trúc**. Việc model có dịch đủ nội dung **bên trong** từng đơn vị do S5 kiểm tra.

### 8.4 Ô bảng ngắn 🆕 🟠

Ô như "Có", "Không", "Đạt" rất mơ hồ khi dịch riêng.
- Ô dài (trên `short_cell_tokens`, mặc định 4 token): dịch riêng.
- Ô ngắn: thử hai cách trên dev và chọn bằng số liệu (đưa vào ablation):
  - (a) Dịch ô riêng, có bảng tra từ ngắn lấy từ train (ví dụ `Có→Yes`, `Không→No`) cho các giá trị lặp nhiều.
  - (b) Dịch chuỗi ghép `{tiêu đề cột} : {ô}` rồi tách theo dấu phân cách; nếu mất dấu phân cách thì quay về (a).
- Tuyệt đối không đổi số hàng/cột.

✅ **Nghiệm thu:** test không cắt giữa viện dẫn/số/ngày; test tổng số đơn vị trước và sau chunk khớp; có báo cáo thống kê độ dài train và giá trị budget được chọn.

---

## 9. S3 → S6: Glossary, dịch, kiểm tra, dịch lại

### 9.1 S3 – Glossary theo cụm và miền 🟠

**Hai lớp:**

| Lớp | Nội dung | Khi áp dụng |
|---|---|---|
| Chung | Tên cơ quan, thuật ngữ pháp lý, cách gọi Điều/Khoản/Điểm/Chương/Mục/Luật | Khi khớp cụm nguồn đúng ranh giới từ |
| Theo miền | Đất đai, sở hữu trí tuệ, tố tụng, y tế, … | Chỉ bật khi xác định miền đủ chắc chắn |

**Schema một entry** (lưu CSV hoặc YAML, có cột trạng thái duyệt):

| Trường | Ý nghĩa |
|---|---|
| `id` | Mã entry |
| `src_phrase` | Cụm nguồn (nhạy dấu tiếng Việt) |
| `direction` | `vi2en` |
| `domain` | `general` hoặc tên miền |
| `preferred` | Bản dịch ưu tiên |
| `accepted_variants` | Biến thể chấp nhận được |
| `match_mode` | `exact_phrase` (mặc định) hoặc `token_boundary` |
| `priority` | Dùng khi hai entry chồng nhau |
| `evidence` | Nguồn xác nhận: số lần xuất hiện trong train hoặc "người dùng duyệt" |
| `status` | `approved` hoặc `pending`. **Chỉ `approved` được dùng khi dịch.** |

**Quy tắc khớp:**
1. Khớp cụm dài nhất trước. Khi `Bộ Y tế` đã khớp thì không khớp thêm `y tế` bên trong.
2. Entry phải khớp đúng ranh giới từ (âm tiết tiếng Việt cách nhau bởi khoảng trắng).
3. Tên cơ quan phải khớp như một thực thể hoàn chỉnh. Từ như `medical`/`y tế`/`y khoa` đa nghĩa, không thay đồng loạt.
4. Cách gọi Điều/Khoản/Điểm/Chương/Mục: **lấy dạng đa số trong train** (ví dụ `Article`, `Clause` hay `Paragraph`), không hardcode từ trí nhớ. Ghi phân phối vào `reports/citation_convention.md`.

**Nhận diện miền:** chấm điểm theo bộ từ khóa của mỗi miền trên tiêu đề tài liệu và nội dung. Chỉ bật miền khi điểm vượt ngưỡng **và** cách miền thứ hai một khoảng (margin). Ngược lại chỉ dùng lớp chung. Ghi miền được chọn và điểm vào report.

**Khai thác glossary từ train 🆕 🟠:**
1. Với các mẫu cụm có cấu trúc rõ (tên cơ quan bắt đầu bằng `Bộ`, `Ủy ban nhân dân`, `Tòa án`, `Sở`…, các từ chỉ đơn vị văn bản), tìm bản dịch tiếng Anh xuất hiện nhiều nhất trong các cặp train chứa cụm đó.
2. Xuất `glossary_candidates.csv` gồm số lần, phân phối bản dịch, mâu thuẫn (cùng cụm nguồn nhiều bản dịch).
3. Tất cả mặc định `pending`. Người dùng duyệt thì mới thành `approved`. Agent không tự duyệt.

### 9.2 S4 – Dịch 🔴

- Dùng VinAI + adapter hiện có, không đổi weight.
- Cấu hình xuất phát cho VI→EN: `num_beams=4`, `length_penalty=1.1`, `repetition_penalty=1.0`, `no_repeat_ngram_size=0`.
- 🔴 Lưu cho mỗi lần sinh: token cuối có phải EOS không, có chạm `max_new_tokens` không. Đây là tín hiệu cụt chính xác nhất.
- 🟠 `max_new_tokens` đặt **động** theo độ dài nguồn (hàm tuyến tính của `src_tokens` cộng biên an toàn), hiệu chỉnh từ phân phối tỷ lệ độ dài train. Không đặt một hằng số chung cho mọi unit.
- 🟠 Gom batch theo độ dài (sắp xếp unit) để chạy nhanh, nhưng giữ `unit_id` để ghép lại đúng chỗ.
- 🟠 Cache theo hash của `(src_masked, config, glossary_version)` để unit lặp (ô bảng, câu chuẩn) không dịch lại.
- Thay đổi decoding chỉ theo kết quả A/B ở mục 10.

### 9.3 S5 – Validator 🔴

Chạy trên **từng ứng viên** của từng unit, trả về danh sách `{check, severity, detail}`.

| Check | Mức | Cách làm |
|---|---|---|
| Rỗng | error | Sau khi bỏ khoảng trắng |
| Sai ngôn ngữ | error | Tỷ lệ ký tự tiếng Việt có dấu trong output vượt ngưỡng (đã loại tên riêng nằm trong danh sách giữ nguyên) |
| Cụt do hết token | error | `max_new_tokens` bị chạm hoặc không kết thúc bằng EOS |
| Cụm dang dở | warning | Kết thúc bằng mảnh kiểu `/ND`, `of the`, `and`, hoặc nguồn có dấu kết thúc mà output không có |
| Ngắn bất thường | warning | Tỉ lệ độ dài output/nguồn thấp hơn ngưỡng. **Chỉ là tín hiệu**, không kết luận tự động là sai |
| Mất mã văn bản/viện dẫn | error | So thực thể (bên dưới) |
| Mất/sai số | error nếu số nguyên khác, warning nếu chỉ khác định dạng | So tập số đã chuẩn hóa |
| Thiếu thuật ngữ glossary | warning | Entry `approved` đã khớp trong nguồn mà không có `preferred` hay biến thể chấp nhận trong output |
| Lặp suy biến | warning | n-gram lặp liên tiếp nhiều lần ngoài số lần lặp tương ứng trong nguồn |
| Thiếu câu | warning | Số câu/ranh giới `;` của nguồn lớn hơn rõ rệt output |
| Placeholder hỏng | error | Mỗi placeholder phải xuất hiện đúng một lần, cặp mở/đóng đúng thứ tự |

**So khớp số và mã văn bản 🆕 🔴 (nguồn lỗi báo giả thường gặp):**
- Chuẩn hóa số trước khi so: số Việt `1.000.000` và `1,5` khác số Anh `1,000,000` và `1.5`. Quy tắc: trong nguồn, dấu chấm theo sau bởi đúng ba chữ số là phân cách nghìn; trong output, dấu phẩy theo sau bởi đúng ba chữ số là phân cách nghìn.
- Ngày: nguồn `ngày 5 tháng 3 năm 2020` có thể thành `March 5, 2020`, `5 March 2020` hoặc `05/03/2020`. Chuẩn hóa về bộ ba (ngày, tháng, năm) rồi so.
- Mã văn bản: trích bằng regex (ví dụ `12/2020/NĐ-CP`, `Điều 5`, `Khoản 2`, `Điểm a`). Khi so, **bỏ dấu tiếng Việt và đổi `Đ→D`**, vì output tiếng Anh có thể viết `ND-CP`. Số hiệu phải khớp đúng.
- Số viết bằng chữ hoặc đơn vị đo lệch định dạng chỉ hạ xuống `warning`.

**Ngưỡng:** hiệu chỉnh từ train/dev theo percentile, lưu cách tính (ví dụ ngưỡng "ngắn bất thường" theo tỷ lệ độ dài p1–p2 của train, tính riêng theo `kind` nếu phân phối khác nhau). Không đặt cứng một con số cho mọi loại văn bản.

**Nhất quán viện dẫn trong tài liệu 🆕 🟠:** sau khi dịch xong, thống kê các dạng viết của cùng một viện dẫn (`Article 5` / `Art. 5`) và tên cơ quan trong output. Chỉ **báo cáo** biến thể, không tự sửa.

**Kiểm tra dịch ngược 🆕 🟡:** nếu có adapter chiều EN→VI và còn ngân sách thời gian, dịch ngược **chỉ** các unit đã bị đánh dấu, so với nguồn bằng chrF và thực thể. Chỉ làm tín hiệu bổ sung, không tự quyết định.

### 9.4 Chọn ứng viên 🆕 🔴

Điểm phạt của ứng viên = tổng trọng số của các check lỗi (error=3, warning=1). Điểm thấp hơn thì tốt hơn.

### 9.5 S6 – Dịch lại có chọn lọc 🔴

Chỉ unit có ít nhất một check ở mức `error`, hoặc từ hai `warning` trở lên, hoặc có `warning` thuộc nhóm thuật ngữ, mới được dịch lại. **Chỉ một vòng dịch lại**, không lặp.

Chiến lược theo loại lỗi:

| Lỗi chính | Chiến lược | Mô tả |
|---|---|---|
| Cụt, ngắn, thiếu câu | `split_smaller` | Tách unit theo ranh giới câu với `retry_budget`, dịch từng phần, ghép lại |
| Thiếu thuật ngữ | `nbest_rerank` (chính) | Sinh `k` ứng viên (beam `k`, trả về `k`), chọn ứng viên có nhiều entry `approved` khớp nhất và điểm phạt thấp nhất |
| Thiếu thuật ngữ mà n-best không có | `constrained` (phụ) | Ép từ khóa cho **đúng entry thiếu** (ví dụ `force_words_ids`). Chạy chậm, dùng hạn chế, kiểm tra ngữ pháp bằng validator sau đó |
| Lặp suy biến | `anti_repeat` | Chạy lại với `no_repeat_ngram_size` lớn (ví dụ 4 trở lên) hoặc `repetition_penalty` hơi trên 1 cho riêng unit đó. Giá trị cụ thể chốt bằng A/B |
| Placeholder hỏng | `strip_spans` | Mục 7.2 |

⛔ Không dùng thay thế chuỗi sau dịch cho từ đa nghĩa. Chỉ cho phép thay cho tên thực thể đầy đủ khi: entry `approved`, khớp tên cơ quan hoàn chỉnh, đúng một vị trí nghi ngờ, và validator sau thay thế không tăng điểm phạt.

**Quy tắc chọn:** giữ **cả hai** ứng viên (lần đầu và retry). Chọn ứng viên có điểm phạt thấp hơn. Hòa thì giữ ứng viên lần đầu. Retry chỉ thắng khi không tệ hơn và sửa được ít nhất một `error`. Trạng thái `RETRIED_FIXED` hoặc `RETRIED_UNFIXED`.

**Khi cả hai đều tệ:** giữ ứng viên điểm phạt thấp nhất, gắn cảnh báo trong report. Nếu mọi ứng viên rỗng thì xuất **nguồn nguyên văn** với `status=SOURCE_KEPT` và `error` trong report. Không bao giờ bỏ trống lặng lẽ, không bao giờ tự bịa nội dung.

✅ **Nghiệm thu (S3–S6):**
- Test cho mỗi check với ví dụ đúng và sai, gồm số kiểu Việt/Anh, ngày, `NĐ-CP`/`ND-CP`.
- Test glossary: `Bộ Y tế` khớp thực thể; `y tế` không bị thay bên trong; entry `pending` không được dùng.
- Test retry: một vòng duy nhất; ứng viên tốt hơn được chọn; không có vòng vô hạn.
- Ví dụ lỗi `/ND` từ M0 được xử lý hoặc gắn cảnh báo.

---

## 10. Decoding A/B 🔴

Mục đích: chọn cấu hình bằng số liệu, không bằng suy đoán.

**Tập thử nghiệm:** (a) toàn bộ unit lỗi từ M0 (E2, E3, E4); (b) một mẫu ngẫu nhiên cố định các unit không lỗi (để phát hiện suy giảm).

**Quy tắc:** mỗi lần chỉ đổi **một** tham số so với baseline.

| Thí nghiệm | Thay đổi |
|---|---|
| A0 | Cấu hình hiện tại (baseline) |
| A1 | `no_repeat_ngram_size=0`, còn lại giữ |
| A2 | A0 với `max_new_tokens` động theo độ dài nguồn |
| A3 | A1 + A2 |
| A4 | A3 với `length_penalty` lân cận (ví dụ 1.0 và 1.2) |

Mỗi thí nghiệm ghi: tỷ lệ E2/E3/E4, chrF++, BLEU, thời gian/unit. Chọn cấu hình tốt nhất theo tỷ lệ lỗi giảm mà chrF++ không giảm. Kết quả vào `reports/decoding_ab.md`. Đây là A/B nhỏ trên tập hẹp, không phải sweep rộng.

---

## 11. Ablation và đánh giá 🔴 🆕

Tắt/bật từng tầng bằng feature flag trên **cùng một tập dev cố định**:

| Cấu hình | Parser | Chunker | Decoding mới | Glossary | Retry |
|---|:-:|:-:|:-:|:-:|:-:|
| R0 baseline hệ thống cũ | | | | | |
| R1 | ✔ | | | | |
| R2 | ✔ | ✔ | | | |
| R3 | ✔ | ✔ | ✔ | | |
| R4 | ✔ | ✔ | ✔ | ✔ | |
| R5 đầy đủ | ✔ | ✔ | ✔ | ✔ | ✔ |

**Chỉ số cần báo cáo cho mỗi dòng:**
- Cấu trúc: % round-trip đạt, % unit có bản dịch, số khối cấu trúc khác nguồn (kỳ vọng 0).
- Chất lượng: BLEU và chrF++ (sacreBLEU, ghi signature), tính cả tổng và theo tài liệu.
- Lỗi theo taxonomy S0: tỷ lệ E1–E7.
- Vận hành: tỷ lệ unit bị retry, tỷ lệ retry sửa được, thời gian trung bình/tài liệu.

**Điều kiện đưa vào submission (đề xuất, chỉnh trong config):**
1. Bất biến cấu trúc đạt 100%.
2. Không giảm chrF++ tổng so với R0 quá một biên nhỏ đã định, trừ khi có lý do ghi rõ.
3. Thời gian trong ngân sách đã khai báo ở M0.

🟠 **Rà soát tay:** xuất file `manual_review.md` gồm 30 unit chọn ngẫu nhiên cố định, mỗi unit có nguồn, baseline, bản mới, các check bị kích hoạt, để người dùng đánh giá độ đúng pháp lý. Spec nêu rõ: BLEU/chrF++ không đo được độ đúng pháp lý.

---

## 12. Milestone và sản phẩm bàn giao

| M | Nội dung | Sản phẩm bàn giao | ✅ Nghiệm thu |
|---|---|---|---|
| **M0** 🔴 | Khám phá repo; S0 baseline + taxonomy | `docs/ASSUMPTIONS.md`, `reports/baseline_error_taxonomy.md`, file output baseline, BLEU/chrF++ baseline, kết luận nguyên nhân cụt | Có số liệu từng mã lỗi; checklist mục 14 điền xong |
| **M1** 🔴 | Parser (có placeholder), reassembler | Module + unit test; `reports/placeholder_survival.md` | Round-trip 100% trên dev; test mọi thành phần ở 7.1 |
| **M2** 🔴 | Chunker, thống kê độ dài train | Module + test; `reports/train_length_stats.md` | Không cắt giữa viện dẫn/số/ngày; đếm đơn vị khớp |
| **M3** 🔴 | Translator, validator, decoding A/B | Module; `reports/decoding_ab.md`; report theo unit | Mỗi check có test; chọn cấu hình bằng số liệu |
| **M4** 🟠 | Glossary, retry, khai thác candidate | `glossary.*` (approved + pending), `glossary_candidates.csv`, module retry | Test glossary và retry ở mục 9 |
| **M5** 🔴 | Tích hợp service Docker, report, runtime | Image chạy được; report JSON + Markdown mỗi tài liệu | Giao diện vào/ra không đổi; có fallback; chạy trong ngân sách |
| **M6** 🔴 | Ablation đầy đủ, rà soát tay | `reports/ablation.md`, `manual_review.md` | Bảng R0–R5 đầy đủ; điều kiện mục 11 được đánh giá |

---

## 13. Tích hợp service Docker và vận hành (M5) 🔴

1. 🔴 **Giữ nguyên giao diện vào/ra** của service hiện tại. Mọi lớp mới nằm sau giao diện đó.
2. 🔴 **Fallback an toàn 🆕:** nếu pipeline mới ném lỗi hoặc vượt giới hạn thời gian trên một tài liệu, quay về đường dịch cũ cho tài liệu đó và ghi log/report. Service không được trả output trống hay crash chỉ vì lớp mới.
3. 🔴 Mọi tham số qua file config, mount được từ ngoài. Có thể đổi bằng biến môi trường cho các cờ bật/tắt.
4. 🟠 **Ngân sách thời gian 🆕:** đo thời gian mỗi tài liệu theo từng stage. Có `time_budget_per_doc` trong config. Khi gần hết ngân sách thì **bỏ các bước retry**, nhưng **không bao giờ bỏ lần dịch đầu**. Ghi vào report rằng retry bị bỏ do hết thời gian.
5. 🟠 Log có cấu trúc (JSON dòng) cho từng stage, không in nội dung tài liệu nhạy cảm ngoài mức cần thiết.
6. 🟡 Kiểm tra sức khỏe (health check) và thông báo phiên bản glossary/config khi khởi động.

---

## 14. Checklist khám phá repo (làm ở M0, ghi vào `docs/ASSUMPTIONS.md`)

Mỗi mục phải có câu trả lời kèm đường dẫn/dòng trong repo, hoặc ghi "không tìm thấy" kèm giả định.

| # | Câu hỏi | Ghi chú |
|---|---|---|
| 1 | Tên model và tokenizer VinAI đang dùng; giới hạn độ dài tối đa | |
| 2 | Hai adapter nằm ở đâu, mỗi cái cho chiều nào (VI→EN, EN→VI hay khác); cách nạp | Quyết định có dùng được dịch ngược 🟡 không |
| 3 | Script/hàm inference hiện tại và cấu hình generate đang dùng | Điểm cần bọc lại |
| 4 | Giao diện service Docker: đầu vào, đầu ra, tham số, cách gọi | **Không được đổi** |
| 5 | Vị trí và định dạng tập dev; mỗi tài liệu một file Markdown hay gộp | Cố định tập dev cho ablation |
| 6 | Định dạng train corpus; có căn chỉnh theo câu/đoạn không | Cần cho thống kê độ dài và glossary |
| 7 | Script đánh giá hiện có (BLEU/chrF++) và phiên bản sacreBLEU | Dùng lại để so sánh được |
| 8 | **[HỎI]** Giới hạn thời gian, GPU/CPU, bộ nhớ của submission | Quyết định `time_budget_per_doc` |
| 9 | **[HỎI]** Ai duyệt glossary, định dạng muốn nhận (CSV/Sheet) | Entry `pending` chờ duyệt |
| 10 | Môi trường chạy (Python, thư viện, có cài thêm thư viện được không) | Chọn thư viện parse cho phù hợp |

---

## 15. Rủi ro và cách giảm

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Placeholder bị model làm hỏng | 🔴 | Đo tỷ lệ sống sót, chọn dạng tốt nhất, fallback `strip_spans` |
| Retry làm bản dịch tệ hơn | 🟠 | Giữ hai ứng viên, chọn theo điểm phạt, hòa thì giữ bản đầu |
| Chunk lệch phân phối train làm giảm chất lượng | 🟠 | Budget theo percentile train, kiểm tra bằng ablation R2 |
| Báo lỗi giả do khác định dạng số/ngày/`Đ`→`D` | 🟠 | Chuẩn hóa trước khi so; hạ mức `warning` cho lệch định dạng |
| Glossary sai hoặc thiếu ngữ cảnh gây dịch tệ | 🟠 | Chỉ dùng entry `approved`; không thay toàn document; ablation R4 |
| Thời gian chạy vượt giới hạn | 🔴 | Ngân sách thời gian, bỏ retry khi gần hết, cache, batch theo độ dài |
| Lớp mới gây crash hoặc output rỗng | 🔴 | Fallback về đường dịch cũ, không bao giờ bỏ trống lặng lẽ |

---

## 16. Báo cáo kiểm tra (S8) 🔴

Với mỗi tài liệu xuất hai file cạnh output: `*.report.json` (máy đọc) và `*.report.md` (người đọc).

**Nội dung bắt buộc:**

| Mục | Chi tiết |
|---|---|
| Tóm tắt | Số đơn vị, số unit OK, `RETRIED_FIXED`, `RETRIED_UNFIXED`, `SOURCE_KEPT` |
| Bất biến | Kết quả round-trip và độ phủ cấu trúc (đạt/không đạt) |
| Đơn vị có cảnh báo | `unit_id`, kind, check bị kích hoạt, mức, ứng viên đã chọn |
| Đơn vị đã sửa | Chiến lược retry, điểm phạt trước và sau |
| Thuật ngữ | Entry đã áp dụng, miền được chọn và điểm, entry thiếu |
| Viện dẫn | Các dạng viết khác nhau của cùng một viện dẫn trong tài liệu |
| Vận hành | Thời gian từng stage, tổng thời gian, retry có bị bỏ do hết thời gian không |
| Phiên bản | Hash config, phiên bản glossary, phiên bản code, seed |

---

## 17. Danh sách việc cần làm cuối cùng (tóm tắt thứ tự)

1. 🔴 M0: khám phá repo, baseline, taxonomy, nguyên nhân cụt.
2. 🔴 M1: parser + reassembler, round-trip 100%.
3. 🔴 M2: chunker theo phân phối train.
4. 🔴 M3: translator, validator, A/B decoding.
5. 🟠 M4: glossary có điều kiện, retry có chọn lọc.
6. 🔴 M5: tích hợp Docker, report, fallback, ngân sách thời gian.
7. 🔴 M6: ablation R0–R5, rà soát tay, quyết định đưa vào submission.

**Điểm bổ sung so với kế hoạch ban đầu của Codex (🆕):** S0 baseline và taxonomy; placeholder cho inline markup; token budget theo phân phối train; xử lý ô bảng ngắn; chuẩn hóa số/ngày/mã `NĐ-CP`; chọn ứng viên theo điểm phạt; cơ chế glossary cụ thể (n-best rerank trước, constrained sau); khai thác glossary từ train; `max_new_tokens` động và tín hiệu EOS; A/B decoding từng tham số; ablation theo feature flag; fallback đường cũ; ngân sách thời gian; rà soát tay.
