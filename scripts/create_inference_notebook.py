"""Generate the offline inference evaluation notebook without model execution."""
from pathlib import Path
import json
import textwrap


def main():
    cells=[]
    def markdown(text): cells.append({"id":f"cell-{len(cells):02d}","cell_type":"markdown","metadata":{},"source":textwrap.dedent(text).strip().splitlines(keepends=True)})
    def code(text): cells.append({"id":f"cell-{len(cells):02d}","cell_type":"code","metadata":{},"execution_count":None,"outputs":[],"source":textwrap.dedent(text).strip().splitlines(keepends=True)})
    markdown("""
    # Legal VI→EN inference pipeline — offline dev evaluation

    **Không train lại, không tạo dataset mới, không dùng public/private test để chọn config.**
    Bật GPU; Internet OFF. Add Input:
    1. `NLP_inference_pipeline.zip` do `scripts/package_inference_pipeline.py` tạo.
    2. Snapshot offline `vinai-translate-vi2en-v2` (asset đã dùng train).
    3. `vinai-training-wheelhouse` (asset wheel đã dùng train).

    Model EN→VI không cần cho quy trình này; dịch ngược là tùy chọn và đang tắt.
    Chạy theo thứ tự. Các kết quả được lưu dưới `/kaggle/working/inference_evaluation`.
    Nếu glossary chưa duyệt, R4 có thể giống R3; không tự ghi nhận hiệu quả glossary.
    """)
    code("""
    import os, sys, json, hashlib, zipfile, subprocess
    from pathlib import Path
    from datetime import datetime, timezone
    INPUT_ROOT = Path('/kaggle/input')
    WORKING_ROOT = Path('/kaggle/working/inference_evaluation')
    WORKING_ROOT.mkdir(parents=True, exist_ok=True)
    PROJECT_DIR = WORKING_ROOT / 'project'
    def safe_extract(archive, destination):
        destination.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive) as z:
            for member in z.infolist():
                target = (destination / member.filename).resolve()
                if not target.is_relative_to(destination.resolve()) or '\\\\' in member.filename:
                    raise ValueError('Unsafe ZIP path')
            z.extractall(destination)
    projects = list(INPUT_ROOT.rglob('NLP_inference_pipeline.zip'))
    if len(projects) != 1:
        raise FileNotFoundError(f'Expected one NLP_inference_pipeline.zip: {projects}')
    if not PROJECT_DIR.exists(): safe_extract(projects[0], WORKING_ROOT)
    manifest = json.loads((PROJECT_DIR / 'bundle_manifest.json').read_text())
    for relative, metadata in manifest['files'].items():
        actual = hashlib.sha256((PROJECT_DIR / relative).read_bytes()).hexdigest()
        if actual != metadata['sha256']: raise ValueError(f'Bundle hash mismatch: {relative}')
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_DATASETS_OFFLINE='1',
                      HF_HUB_DISABLE_TELEMETRY='1', TOKENIZERS_PARALLELISM='false',
                      CUBLAS_WORKSPACE_CONFIG=':4096:8')
    sys.path.insert(0, str(PROJECT_DIR))
    print('Project verified:', PROJECT_DIR)
    """)
    markdown("""
    ## 1. Cài thư viện từ wheel offline và tìm snapshot model

    Cell này không gọi Hub. Nếu thiếu Input, bổ sung asset đã dùng trong notebook train.
    """)
    code("""
    wheel_dirs = sorted({p.parent for p in INPUT_ROOT.rglob('transformers-5.17.0-*.whl')})
    if not wheel_dirs:
        wheel_zips = [p for p in INPUT_ROOT.rglob('*.zip') if 'wheelhouse' in p.name.lower()]
        if len(wheel_zips) != 1: raise FileNotFoundError(f'Expected one wheelhouse: {wheel_zips}')
        safe_extract(wheel_zips[0], WORKING_ROOT / 'wheels')
        wheel_dirs = sorted({p.parent for p in (WORKING_ROOT / 'wheels').rglob('transformers-5.17.0-*.whl')})
    if len(wheel_dirs) != 1: raise ValueError(f'Ambiguous wheelhouse: {wheel_dirs}')
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '--no-index', '--find-links',
                    str(wheel_dirs[0]), '-r', str(PROJECT_DIR / 'submission/requirements-inference.txt')], check=True)
    from importlib.metadata import version, PackageNotFoundError
    from packaging.version import Version
    try:
        torchao = version('torchao')
    except PackageNotFoundError:
        torchao = None
    if torchao and Version(torchao) <= Version('0.16.0'):
        subprocess.run([sys.executable, '-m', 'pip', 'uninstall', '-y', 'torchao'], check=True)
    candidates = [p.parent for p in INPUT_ROOT.rglob('offline_model_manifest.json')
                  if json.loads(p.read_text()).get('repo_id') == 'vinai/vinai-translate-vi2en-v2']
    if not candidates:
        model_zips = [p for p in INPUT_ROOT.rglob('*.zip') if 'vinai-translate-vi2en-v2' in p.name]
        if len(model_zips) != 1: raise FileNotFoundError(f'Expected VI2EN offline snapshot: {model_zips}')
        safe_extract(model_zips[0], WORKING_ROOT / 'base')
        candidates = [p.parent for p in (WORKING_ROOT / 'base').rglob('offline_model_manifest.json')]
    if len(candidates) != 1: raise ValueError(f'Ambiguous VI2EN base: {candidates}')
    BASE_DIR = candidates[0]
    metadata = json.loads((BASE_DIR / 'offline_model_manifest.json').read_text())
    if metadata.get('repo_id') != 'vinai/vinai-translate-vi2en-v2' or metadata.get('revision') != '4eb2219d447d4352861e71e371a6b6abcb0509c8':
        raise ValueError('Wrong model snapshot identity')
    if not metadata.get('files'): raise ValueError('Offline model manifest has no file checksums')
    for relative, expected in metadata['files'].items():
        path = (BASE_DIR / relative).resolve()
        if not path.is_relative_to(BASE_DIR.resolve()): raise ValueError('Unsafe model manifest path')
        if not path.is_file() or path.stat().st_size != expected['bytes']:
            raise ValueError(f'Missing or incomplete model file: {relative}')
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''): digest.update(block)
        if digest.hexdigest() != expected['sha256']: raise ValueError(f'Model checksum mismatch: {relative}')
    os.environ['VINAI_VI2EN_MODEL_DIR'] = str(BASE_DIR)
    import torch
    if not torch.cuda.is_available(): raise RuntimeError('Bật Kaggle GPU trước khi chạy tiếp')
    print('GPU:', torch.cuda.get_device_name())
    print('Libraries:', {name: version(name) for name in ('torch', 'transformers', 'peft', 'sacrebleu')})
    """)
    markdown("""
    ## 2. Test code và cấu trúc

    Dataset và adapter vẫn là bản đã chốt. Budget đã được hiệu chỉnh trên train;
    không cần chạy lại LaBSE, freeze hoặc train.
    """)
    code("""
    DEV = PROJECT_DIR / 'artifacts/processed_clean_semantic_seed67_v3/segments_dev_vi2en.jsonl'
    ADAPTER = PROJECT_DIR / 'attached_runs/vi2en/best_model'
    SNAPSHOT = PROJECT_DIR / 'attached_runs/vi2en/predictions/validation_predictions.jsonl'
    PIPELINE = PROJECT_DIR / 'submission/configs/inference_pipeline.json'
    EXPERIMENT = PROJECT_DIR / 'submission/configs/vi2en.json'
    EVAL_DIR = WORKING_ROOT / 'reports'
    EVAL_DIR.mkdir(exist_ok=True)
    tests = ['tests.test_legal_parser', 'tests.test_legal_chunker', 'tests.test_legal_validator',
             'tests.test_legal_translator', 'tests.test_legal_glossary_retry', 'tests.test_legal_pipeline',
             'tests.test_legal_service', 'tests.test_legal_evaluation', 'tests.test_submission']
    subprocess.run([sys.executable, '-m', 'unittest', *tests, '-q'], cwd=PROJECT_DIR, check=True)
    subprocess.run([sys.executable, 'scripts/check_inference_roundtrip.py', '--dev', str(DEV),
                    '--output', str(EVAL_DIR / 'roundtrip.json')], cwd=PROJECT_DIR, check=True)
    def run_eval(mode, output_name=None, selection=None, experiment=EXPERIMENT, limit=None, pipeline=PIPELINE):
        output = EVAL_DIR / ((output_name or mode) + '_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
        command = [sys.executable, '-u', '-m', 'src.vinai_baseline.pipeline.evaluation', 'run',
                   '--mode', mode, '--dev', str(DEV), '--adapter', str(ADAPTER),
                   '--experiment-config', str(experiment), '--pipeline-config', str(pipeline),
                   '--baseline-snapshot', str(SNAPSHOT), '--output', str(output)]
        if selection: command.extend(['--selection', str(selection)])
        if limit: command.extend(['--limit', str(limit)])
        subprocess.run(command, cwd=PROJECT_DIR, check=True)
        return output
    print('Ready; no training command is used.')
    """)
    markdown("""
    ## 3. Nguyên nhân cụt và placeholder

    Probe dùng config của run đã tạo snapshot để điều tra đúng hiện tượng cũ.
    A0/A1 chỉ khác ngram. EOS ở đúng cap vẫn là chạm cap, không coi là dừng sạch.
    Dev hiện có 0 unit chứa markup dạng cặp; placeholder report sẽ ghi thiếu dữ liệu.
    """)
    code("""
    CAUSE_DIR = run_eval('causes', experiment=PROJECT_DIR / 'attached_runs/vi2en/resolved_config.json')
    PLACEHOLDER_DIR = run_eval('placeholder')
    print((CAUSE_DIR / 'cutoff_cause_probe.md').read_text())
    print((PLACEHOLDER_DIR / 'placeholder_survival.md').read_text())
    """)
    markdown("""
    ## 4. Decoding A/B trên dev cố định

    Dùng config hiện hành của service làm A0. Giữ A0 nếu các cấu hình mới không
    giảm lỗi mà vẫn giữ chrF++. `selection.json` không thay config submission.
    """)
    code("""
    AB_DIR = run_eval('ab')
    SELECTION = AB_DIR / 'selection.json'
    print(SELECTION.read_text())
    print((AB_DIR / 'decoding_ab.md').read_text())
    """)
    markdown("""
    ## 5. Glossary do bạn duyệt, rồi ablation R0–R5

    Mở `project/submission/resources/glossary_candidates.csv`, chọn cụm có bằng
    chứng đúng, sửa preferred/accepted_variants/domain nếu cần và chép vào
    `glossary.csv` với `status=approved`. Không đổi trạng thái hàng loạt.
    Nếu chưa duyệt thì cứ giữ glossary.csv rỗng; báo cáo sẽ không xác nhận hiệu quả glossary.
    Có thể chạy smoke 2 records trước; smoke không được dùng để promotion.
    """)
    code("""
    RUN_ABLATION_SMOKE = True
    if RUN_ABLATION_SMOKE:
        run_eval('ablation', 'ablation_smoke', selection=SELECTION, limit=2)
    """)
    code("""
    RUN_FULL_ABLATION = False  # Đặt True sau khi smoke đã chạy và kiểm tra glossary
    if RUN_FULL_ABLATION:
        ABLATION_DIR = run_eval('ablation', selection=SELECTION)
        FINAL_PLACEHOLDER_DIR = run_eval('placeholder', 'placeholder_selected', pipeline=ABLATION_DIR / 'selected_pipeline.json')
        print((ABLATION_DIR / 'ablation.md').read_text())
    else:
        print('Full ablation chưa chạy. Không dùng smoke để chốt submission.')
    """)
    markdown("""
    ## 6. Tải báo cáo và bước chốt

    Đọc `ablation/manual_review.md` (30 mẫu), `promotion_evidence.json` và từng
    R0–R5 summary. Chưa biết GPU/RAM/time của ban tổ chức nên promotion vẫn pending.
    `selected_pipeline.json` là bản chờ duyệt. Chốt bằng `scripts/finalize_inference_promotion.py`
    với report GPU và placeholder của đúng candidate; chỉ mount `approved_pipeline.json` sau passed.
    Dev hiện thiếu markup nên bước nghiệm thu placeholder vẫn bị chặn; không tự tạo ví dụ để bù.
    Model merged cần được đo lại trong môi trường deployment; bằng chứng adapter không
    tự coi là bằng chứng cho merged weights. API và script ba tham số giữ nguyên.
    Không dùng public/private test để chỉnh glossary, decoding hoặc retry.
    """)
    code("""
    import shutil
    report_zip = shutil.make_archive(str(WORKING_ROOT / 'NLP_inference_reports'), 'zip', EVAL_DIR)
    print('Download:', report_zip)
    """)
    notebook={"cells":cells,"metadata":{"kernelspec":{"display_name":"Python 3","language":"python","name":"python3"},"language_info":{"name":"python","version":"3.11"}},"nbformat":4,"nbformat_minor":5}
    path=Path(__file__).resolve().parents[1]/"notebooks/05_inference_pipeline_kaggle.ipynb"
    path.write_text(json.dumps(notebook,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(path)


if __name__=="__main__": main()
