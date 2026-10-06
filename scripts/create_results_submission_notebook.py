"""Create the offline Kaggle notebook for document prediction submission."""
import json
from pathlib import Path
import textwrap


def main():
    cells = []
    def add(kind, source):
        cell = {"id": f"cell-{len(cells):02d}", "cell_type": kind, "metadata": {},
                "source": textwrap.dedent(source).strip().splitlines(keepends=True)}
        if kind == "code": cell.update(execution_count=None, outputs=[])
        cells.append(cell)
    def markdown(source): add("markdown", source)
    def code(source): add("code", source)
    markdown('''
    # Xuất prediction submission — Public / Private Test, offline

    Bật **GPU**, tắt **Internet**. Add Input gồm:
    1. `NLP_results_submission_kaggle.zip` — code, CSV public gốc, hai adapter đã train, config đã chốt.
    2. `vinai-translate-en2vi-v2.zip` hoặc thư mục snapshot đã dùng khi train.
    3. `vinai-translate-vi2en-v2.zip` hoặc thư mục snapshot đã dùng khi train.
    4. `vinai-training-wheelhouse-py313-linux.zip` hoặc thư mục wheel offline đã dùng khi train.

    Không cần LaBSE, dataset frozen hoặc chạy lại train/sweep. Dịch toàn bộ nguồn gốc;
    giữ cấu trúc Markdown bằng vị trí văn bản. Bản context v2 giữ nguyên EN→VI,
    nhưng ghép các dòng VI→EN bị hard-wrap để model nhận đủ ngữ cảnh câu.
    Output cuối **`submission.zip` chỉ chứa `results.csv`**, đủ 100 dòng.
    ZIP project ở bước 1 là Input cho notebook; file đó không phải bài nộp.
    ''')
    code('''
    import os, sys, json, hashlib, zipfile, subprocess
    from pathlib import Path
    INPUT_ROOT = Path('/kaggle/input')
    WORKING_ROOT = Path('/kaggle/working/results_submission')
    PROJECT_DIR = WORKING_ROOT / 'project'
    WORKING_ROOT.mkdir(parents=True, exist_ok=True)
    def safe_extract(path, destination):
        destination.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path) as archive:
            for member in archive.infolist():
                target = (destination / member.filename).resolve()
                if not target.is_relative_to(destination.resolve()) or '\\\\' in member.filename:
                    raise ValueError('Unsafe ZIP member')
            archive.extractall(destination)
    # Kaggle may expose the uploaded archive unchanged, or automatically unpack
    # it as a Dataset. Support both layouts and always copy into /kaggle/working.
    bundles = list(INPUT_ROOT.rglob('NLP_results_submission_kaggle*.zip'))
    manifests = []
    for path in INPUT_ROOT.rglob('bundle_manifest.json'):
        try:
            metadata = json.loads(path.read_text(encoding='utf-8'))
            if metadata.get('purpose', '').startswith('Kaggle input for original full-document prediction'):
                manifests.append(path)
        except (OSError, UnicodeError, json.JSONDecodeError):
            pass
    if PROJECT_DIR.exists() and not (PROJECT_DIR/'bundle_manifest.json').is_file():
        raise FileNotFoundError(f'Incomplete working project: {PROJECT_DIR}; remove it and rerun this cell')
    if not PROJECT_DIR.exists():
        if len(bundles) == 1:
            safe_extract(bundles[0], WORKING_ROOT)
        elif len(bundles) == 0 and len(manifests) == 1:
            import shutil
            source_project = manifests[0].parent
            shutil.copytree(source_project, PROJECT_DIR)
        else:
            raise FileNotFoundError(
                f'Expected exactly one project ZIP or unpacked bundle_manifest.json; '
                f'ZIPs={bundles}, manifests={manifests}'
            )
    manifest = json.loads((PROJECT_DIR/'bundle_manifest.json').read_text(encoding='utf-8'))
    for relative, metadata in manifest['files'].items():
        path = (PROJECT_DIR / relative).resolve()
        if not path.is_relative_to(PROJECT_DIR.resolve()): raise ValueError('Unsafe bundle manifest')
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != metadata['sha256']:
            raise ValueError(f'Project file checksum mismatch: {relative}')
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_DATASETS_OFFLINE='1',
                      HF_HUB_DISABLE_TELEMETRY='1', TOKENIZERS_PARALLELISM='false',
                      CUBLAS_WORKSPACE_CONFIG=':4096:8')
    sys.path.insert(0, str(PROJECT_DIR))
    print('Project verified:', PROJECT_DIR)
    print('Python:', sys.version)
    ''')
    markdown('''
    ## 1. Cài thư viện offline

    Wheelhouse hiện tại dành cho Linux Python 3.13. Nếu Kaggle đổi phiên bản Python,
    cần dùng wheelhouse tương ứng. Chạy cell này trước khi import torch/transformers;
    nếu đã import phiên bản khác trong session cũ, restart session rồi chạy từ đầu.
    ''')
    code('''
    wheel_dirs = sorted({p.parent for p in INPUT_ROOT.rglob('transformers-5.17.0-*.whl')})
    if not wheel_dirs:
        wheel_zips = [p for p in INPUT_ROOT.rglob('*.zip') if 'wheelhouse' in p.name.lower()]
        if len(wheel_zips) != 1: raise FileNotFoundError(f'Expected one offline wheelhouse: {wheel_zips}')
        safe_extract(wheel_zips[0], WORKING_ROOT/'wheels')
        wheel_dirs = sorted({p.parent for p in (WORKING_ROOT/'wheels').rglob('transformers-5.17.0-*.whl')})
    if len(wheel_dirs) != 1: raise ValueError(f'Ambiguous wheelhouse: {wheel_dirs}')
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--no-index', '--find-links', str(wheel_dirs[0]),
                    '-r', str(PROJECT_DIR/'submission/requirements-inference.txt')], check=True)
    # Kaggle's old torchao can fail while importing newer transformers.
    from importlib.metadata import version, PackageNotFoundError
    from packaging.version import Version
    try:
        if Version(version('torchao')) <= Version('0.16.0'):
            subprocess.run([sys.executable, '-m', 'pip', 'uninstall', '-y', 'torchao'], check=True)
    except PackageNotFoundError: pass
    import torch
    if not torch.cuda.is_available(): raise RuntimeError('Bật GPU ở Notebook Settings rồi restart session')
    print('GPU:', torch.cuda.get_device_name(0))
    ''')
    markdown('''
    ## 2. Tìm hai base model offline và kiểm tra adapter

    Dùng snapshot có `offline_model_manifest.json` đã chuẩn bị cho training.
    Không dùng một model khác cùng tên hoặc tự tải model qua Hugging Face.
    Khi chạy dịch, CLI sẽ kiểm tra SHA256 toàn bộ snapshot, có thể mất vài phút.
    ''')
    code('''
    MODEL_SPECS = {
        'en2vi': ('vinai/vinai-translate-en2vi-v2', '1e47495b5dac16097b1d9e7b4133c27e1f40504f'),
        'vi2en': ('vinai/vinai-translate-vi2en-v2', '4eb2219d447d4352861e71e371a6b6abcb0509c8'),
    }
    def find_base(direction):
        repo, revision = MODEL_SPECS[direction]
        def candidates(root):
            found = []
            for path in root.rglob('offline_model_manifest.json'):
                metadata = json.loads(path.read_text(encoding='utf-8'))
                if metadata.get('repo_id') == repo and metadata.get('revision') == revision:
                    found.append(path.parent)
            return found
        found = candidates(INPUT_ROOT)
        if not found:
            destination = WORKING_ROOT/'base_models'/direction
            found = candidates(destination) if destination.exists() else []
            if not found:
                archives = list(INPUT_ROOT.rglob(f'vinai-translate-{direction}-v2.zip'))
                if len(archives) != 1: raise FileNotFoundError(f'Thiếu snapshot/ZIP {direction}: {archives}')
                safe_extract(archives[0], destination)
                found = candidates(destination)
        if len(found) != 1: raise ValueError(f'Expected one correct offline {direction} snapshot: {found}')
        return found[0]
    BASE_DIRS = {direction: find_base(direction) for direction in MODEL_SPECS}
    ADAPTER_DIRS = {direction: PROJECT_DIR/'models'/direction for direction in MODEL_SPECS}
    for direction in MODEL_SPECS:
        os.environ[f'VINAI_{direction.upper()}_MODEL_DIR'] = str(BASE_DIRS[direction])
        for filename in ('adapter_config.json', 'adapter_model.safetensors'):
            if not (ADAPTER_DIRS[direction]/filename).is_file(): raise FileNotFoundError(filename)
    print('Offline bases:', BASE_DIRS)
    print('Adapters:', ADAPTER_DIRS)
    ''')
    markdown('''
    ## 3. Chọn phase và kiểm tra format

    Public: giữ mặc định CSV gốc, 50 cặp tài liệu → 100 dòng prediction.
    Private: đổi `PHASE='private'`, `INPUT_CSV` sang CSV ban tổ chức cung cấp,
    và `SOURCE_COLUMN` thành tên cột nguồn nếu cần. Private phải có 100 ID và
    cột `direction` chứa `en-vi` / `vi-en`. Không tự thêm chiều còn lại.
    Chưa có private input thực tế nên format của nó cần kiểm tra khi được phát hành.
    ''')
    code('''
    PHASE = 'public'
    INPUT_CSV = PROJECT_DIR/'data/test/en-vi-public_test.csv'
    SOURCE_COLUMN = None
    BATCH_SIZE = 8  # Nếu OOM, dùng 4 và chọn RUN_DIR mới vì thay đổi batch ảnh hưởng provenance.
    RUN_DIR = WORKING_ROOT/f'results_{PHASE}_context_v2'
    from src.vinai_baseline.results_submission import load_test, validate_archive
    documents = load_test(INPUT_CSV, PHASE, SOURCE_COLUMN, expected_documents=50 if PHASE=='public' else 100)
    print('Expected prediction rows:', len(documents))
    print('Per direction:', {d: sum(item.direction==d for item in documents) for d in ('en-vi', 'vi-en')})
    subprocess.run([sys.executable, '-m', 'unittest', 'tests.test_results_submission', '-q'], cwd=PROJECT_DIR, check=True)
    # Reuse the strong, already submitted EN-to-VI predictions when available.
    # The archive is validated against all 100 required public keys before reuse.
    REUSE_EN2VI_ZIP = None
    if PHASE == 'public':
        previous = WORKING_ROOT/'results_public'/'submission.zip'
        candidates = [previous] if previous.is_file() else list(INPUT_ROOT.rglob('submission.zip'))
        valid = []
        for candidate in candidates:
            try:
                if validate_archive(candidate, documents)['rows'] == 100: valid.append(candidate)
            except Exception:
                pass
        if len(valid) == 1: REUSE_EN2VI_ZIP = valid[0]
        elif len(valid) > 1: raise ValueError(f'Nhiều baseline submission ZIP hợp lệ; chọn thủ công một file: {valid}')
    print('Reuse locked EN-to-VI:', REUSE_EN2VI_ZIP or 'không có; sẽ sinh lại cả hai chiều')
    def command(output, *extra):
        result = [sys.executable, '-u', str(PROJECT_DIR/'scripts/build_results_submission.py'),
                  '--input', str(INPUT_CSV), '--phase', PHASE, '--output-dir', str(output),
                  '--en2vi-model', str(ADAPTER_DIRS['en2vi']), '--vi2en-model', str(ADAPTER_DIRS['vi2en']),
                  '--batch-size', str(BATCH_SIZE), '--resume', *extra]
        if SOURCE_COLUMN is not None: result += ['--source-column', SOURCE_COLUMN]
        if REUSE_EN2VI_ZIP is not None: result += ['--reuse-en2vi-zip', str(REUSE_EN2VI_ZIP)]
        return result
    ''')
    markdown('''
    ## 4. Smoke tùy chọn và dịch đủ test

    `RUN_SMOKE=True` chỉ kiểm tra một tài liệu mỗi chiều; không tạo ZIP bài nộp.
    Nếu tìm thấy submission cũ, full run giữ nguyên 50 output EN→VI và chỉ chạy
    VI→EN context v2; nếu không, nó chạy lần lượt cả hai chiều. Có log batch và lưu từng tài liệu.
    Nếu bị ngắt, chạy lại cell full với cùng `RUN_DIR`, Input và cấu hình để tiếp tục.
    Khi đổi model/code/Input/config, chọn `RUN_DIR` mới. Không chạy train hoặc sweep.
    ''')
    code('''
    RUN_SMOKE = False
    if RUN_SMOKE:
        subprocess.run(command(WORKING_ROOT/f'smoke_{PHASE}', '--smoke-documents', '1'), cwd=PROJECT_DIR, check=True)
    ''')
    code('''
    RUN_FULL = True
    if RUN_FULL:
        if (RUN_DIR/'submission.zip').is_file():
            print('Đã có ZIP; chuyển sang cell kiểm tra và tải bên dưới.')
        else:
            subprocess.run(command(RUN_DIR), cwd=PROJECT_DIR, check=True)
    else:
        print('Chưa dịch đầy đủ; không có bài nộp mới.')
    ''')
    markdown('''
    ## 5. Kiểm tra và tải bài nộp

    Nộp duy nhất **`submission.zip`** bên dưới. Trong ZIP có `results.csv` ở root.
    Report nằm bên ngoài ZIP. Public report dùng corpus BLEU 13a + exponential smoothing
    và chrF (`char_order=6`, `word_order=0`, `beta=2`), tính riêng từng chiều rồi macro-average.
    Các điểm này là báo cáo cuối; không dùng public/private test để chọn lại decoding/glossary/model.
    Kiểm tra format không chứng minh bản dịch hoàn hảo; đọc thử một số tài liệu dài trước khi nộp.
    ''')
    code('''
    from IPython.display import display, FileLink
    from src.vinai_baseline.results_submission import validate_archive
    ZIP_PATH = RUN_DIR/'submission.zip'
    validation = validate_archive(ZIP_PATH, documents)
    if validation['rows'] != 100: raise ValueError('Bài nộp phase hiện tại phải có đúng 100 dòng')
    print(json.dumps(validation, indent=2))
    report = json.loads((RUN_DIR/'evaluation_report.json').read_text(encoding='utf-8'))
    print(json.dumps(report['metrics'], ensure_ascii=False, indent=2))
    display(FileLink(str(ZIP_PATH)))
    display(FileLink(str(RUN_DIR/'evaluation_report.json')))
    display(FileLink(str(RUN_DIR/'results.csv')))
    print('UPLOAD:', ZIP_PATH)
    ''')
    notebook = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                            "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
    path = Path(__file__).resolve().parents[1]/'notebooks/06_results_submission_kaggle.ipynb'
    path.write_text(json.dumps(notebook, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(path)


if __name__ == '__main__': main()
