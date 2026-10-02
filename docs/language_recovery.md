# Khôi phục baseline EN→VI sau lỗi language token

Run ngày 01/10 có BLEU 3.37, chrF++ 19.75 và bản dịch lặp. Tokenizer đã lưu
`tgt_lang=en_XX` dù task EN→VI. Code mới khai báo cả source/target language,
kiểm tra token cuối thực tế, và đặt decoder start đúng `vi_VN` (EN→VI) hoặc
`en_XX` (VI→EN). Không coi đây là bằng chứng duy nhất của mọi lỗi chất lượng;
các lượt GPU dưới đây dùng để kiểm chứng nguyên nhân.

## Chạy trên Kaggle

1. Upload **NLP_colab.zip mới**, cập nhật Input và import lại notebook
   `notebooks/03_vinai_kaggle.ipynb`. Bật GPU và Internet. Dùng session mới để
   tránh giữ module Python từ ZIP cũ trong bộ nhớ.
2. Giữ `DATASET_PROFILE="v2"`, `DIRECTION="en2vi"`, `MODE="lora"`,
   `CONFIG_OVERRIDE=""`, `RUN_FULL=False`, `RESUME_FROM_CHECKPOINT=""`.
   Tag mới mặc định `baseline_v2_langfix1`. Dataset, seed 67, LoRA rank, LR,
   batch và decoding giữ nguyên để đo tác động language control.
3. Chạy tới **7b**: model gốc chấm **256 mẫu sau token audit**, chọn cố định theo
   seed/category/document. Không có training. Đọc `gate_report.json`,
   `predictions.jsonl` và `subset.json` trong `/kaggle/working/diagnostics/`.
   Cell chỉ pass nếu không phát hiện mẫu suy biến. Gate là kiểm tra heuristic;
   vẫn cần đọc bản dịch và BLEU/chrF++. Nếu bị ngắt giữa chừng, tăng
   `DIAGNOSTIC_ATTEMPT` để chạy vào thư mục mới. Nếu gate fail, dừng và xem
   `quality.failures`. Từ gate v2, lỗi suy biến (rỗng, lặp/token collapse,
   quá dài, sai ngôn ngữ) chặn train; `quality.warnings` ghi các trường hợp
   dịch thiếu để LoRA có thể tiếp tục nhưng phải được so sánh lại sau train.
4. **7c**: attach kết quả LoRA cũ làm Input; điền `OLD_ADAPTER_DIR` trỏ đến
   `best_model` có `adapter_config.json`, đặt `RUN_OLD_ADAPTER_CHECK=True`.
   Bước này chấm adapter cũ với language control đã sửa trên cùng 256 mẫu;
   không sửa hoặc ghi đè adapter. Mã 2 là hard quality fail đã lưu report, không
   phải lỗi CUDA. Các mã khác cần đọc traceback trước khi tiếp tục.
5. So sánh zero-shot và adapter trên cùng segment IDs, BLEU/chrF++, lỗi lặp,
   độ dài và bảo toàn số. Adapter pass chưa có nghĩa hơn zero-shot. Nếu adapter
   vẫn suy biến hoặc kém rõ rệt, chạy **8: smoke LoRA mới**. Smoke khởi tạo
   từ model gốc, không tải adapter cũ.
6. Khi smoke và verify pass, đặt `START_FULL_NOW=True` ở **9**. Chạy lại riêng
   cell Full run. Giữ checkpoint cũ để phân tích; không resume run được train
   trước language fix. Runner chặn resume/audit run cũ thiếu language marker.
7. Chạy cell **10** để tải kết quả. `reports/quality_gate.json` kiểm tra toàn
   bộ dev cuối; `reports/reload_smoke.json` và `reload_predictions.jsonl`
   kiểm tra tải lại trên tối đa 16 mẫu. Kiểm tra cả hai report. Full training
   lưu model/metrics trước verify, nên verify fail không làm mất model.

Nếu adapter cũ pass ở **7c**, chưa cần chạy lại training: bỏ qua **8–10**, bật
`RUN_GENERATION_SWEEP=True` ở **11**, duyệt bảng và điền candidate thắng vào
`SELECTED_GENERATION_NAME` ở **12**. Sau đó bật `RUN_FULL_ADAPTER_EVAL=True`
để chấm đủ 1.821 mẫu dev và tải ZIP report. Nhánh 11–12 không sửa trọng số.

Nếu Input kết quả cũ vẫn là ZIP, dùng cell riêng này (không cần giải nén optimizer):

```python
import tempfile, zipfile, shutil
from pathlib import Path, PurePosixPath
old_zip = Path("/kaggle/input/ten-dataset/ten-run_result.zip")
destination = Path(tempfile.mkdtemp(prefix="old_adapter_", dir="/kaggle/working"))
with zipfile.ZipFile(old_zip) as archive:
    for entry in archive.infolist():
        relative = PurePosixPath(entry.filename.replace("\\", "/"))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Unsafe ZIP path")
        if not relative.parts or relative.parts[0] != "best_model" or entry.is_dir():
            continue
        target = destination.joinpath(*relative.parts)
        if not target.resolve().is_relative_to(destination.resolve()):
            raise ValueError("Unsafe ZIP path")
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(entry) as src, target.open("wb") as dst:
            shutil.copyfileobj(src, dst)
print("OLD_ADAPTER_DIR =", str(destination / "best_model"))
```

## Quality gate và thời gian

Gate fail trên output rỗng, lặp trigram quá mức so với reference, token chiếm
hơn 25% output từ 20 token, output dài hơn 3 lần reference, gần như rỗng so
với reference (dưới 2%), hoặc output EN→VI dài gần như không có dấu. Tỷ lệ
dưới 25% được ghi thành cảnh báo `under_translation`, không tự động chặn một
LoRA mới vì fine-tuning có thể cải thiện nó. Cụm pháp lý lặp đơn lẻ không đủ
để kết luận lỗi. Đây không phải language detector hoàn chỉnh hay chứng nhận
chất lượng; văn bản tên riêng/đầu trang có thể cần xem thủ công.

Zero-shot và adapter diagnostic chạy FP32 inference theo đường document
inference để tránh thay đổi độ chính xác số; tốc độ khác Trainer FP16 của run
cũ. Dùng log throughput trên máy thật để dự báo. Chỉ hai diagnostic 256 mẫu,
smoke và full training cần GPU; không chạy full ở local. Giữ V3 semantic tắt
đến khi có zero-shot và LoRA V2 không còn suy biến.

## CLI tương đương

Chạy từ project root trên Kaggle; dùng thư mục output mới cho mỗi lần:

```bash
python -m src.vinai_baseline.preflight_cli --config configs/vinai/en2vi_lora.json --output-dir /kaggle/working/zero256 --samples 256
python -m src.vinai_baseline.preflight_cli --config configs/vinai/en2vi_lora.json --saved-model-dir /kaggle/input/old-run/best_model --output-dir /kaggle/working/adapter256 --samples 256
```

Notebook chặn train khi zero-shot gate thiếu, fail hoặc khác model/data/decoding/code.
Giữ các báo cáo fail làm bằng chứng; không chỉnh tay trạng thái `passed`.
Đây là nhánh sửa lỗi nền tảng, chưa có kết quả GPU chứng minh mức tăng điểm.
