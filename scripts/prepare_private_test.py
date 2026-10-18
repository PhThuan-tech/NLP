"""Verify private sources and merged weights; package a ready-to-run GPU notebook."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.vinai_baseline.results_submission import load_test, parse_legal_document
from src.vinai_baseline.pipeline.promotion import file_hash


def prepare(input_path, output):
    docs = load_test(input_path, 'private', expected_documents=100)
    report = {'input_sha256': file_hash(input_path), 'documents': len(docs),
              'directions': dict(Counter(d.direction for d in docs)), 'models': {},
              'source_characters': sum(len(d.source) for d in docs)}
    block_counts = Counter()
    for document in docs:
        parsed = parse_legal_document(document.source, document.sample_id)
        block_counts.update(b['kind'] for b in parsed.blocks)
    report['source_block_counts'] = dict(block_counts)
    for direction in ('en2vi', 'vi2en'):
        archive_path = ROOT/'modelAI'/f'{direction}_merged.zip'
        config = json.loads((ROOT/f'submission/configs/{direction}.json').read_text(encoding='utf-8'))
        with zipfile.ZipFile(archive_path) as archive:
            metadata = json.loads(archive.read(f'{direction}/merge_manifest.json'))
            if (metadata['base_model'], metadata['base_model_revision'], metadata['direction']) != (
                    config['model_name'], config['model_revision'], direction):
                raise ValueError(f'Merged model identity mismatch: {direction}')
            for name, expected in metadata['files'].items():
                digest = hashlib.sha256()
                size = 0
                with archive.open(f'{direction}/{name}') as handle:
                    for chunk in iter(lambda: handle.read(1024*1024), b''):
                        digest.update(chunk)
                        size += len(chunk)
                if digest.hexdigest() != expected['sha256'] or size != expected['bytes']:
                    raise ValueError(f'Merged model checksum mismatch: {direction}/{name}')
            report['models'][direction] = metadata
        print(f'VERIFIED {direction}', flush=True)

    notebook = json.loads((ROOT/'notebooks/06_results_submission_kaggle.ipynb').read_text(encoding='utf-8'))
    for cell in notebook['cells']:
        source = ''.join(cell['source'])
        if cell['cell_type'] == 'markdown':
            cell['source'] = ['Private test: 100 nguồn, 50 EN→VI và 50 VI→EN. '
                              'Dùng hai merged model đã chốt, giữ config và context v2.\n']
        elif 'MODEL_SPECS = ' in source:
            cell['source'] = [
                "from src.vinai_baseline.pipeline.promotion import file_hash\n",
                "ADAPTER_DIRS = {}\n",
                "for direction in ('en2vi', 'vi2en'):\n",
                "    candidates = [p.parent for p in INPUT_ROOT.rglob('merge_manifest.json') if p.parent.name == direction]\n",
                "    if not candidates:\n",
                "        archives = list(INPUT_ROOT.rglob(f'{direction}_merged.zip'))\n",
                "        if len(archives) != 1: raise ValueError(f'Expected one merged ZIP: {archives}')\n",
                "        destination = WORKING_ROOT/'merged_models'\n",
                "        safe_extract(archives[0], destination)\n",
                "        candidates = [destination/direction]\n",
                "    if len(candidates) != 1: raise ValueError(f'Ambiguous merged models: {candidates}')\n",
                "    model_dir = candidates[0]\n",
                "    metadata = json.loads((model_dir/'merge_manifest.json').read_text(encoding='utf-8'))\n",
                "    config = json.loads((PROJECT_DIR/f'submission/configs/{direction}.json').read_text(encoding='utf-8'))\n",
                "    assert (metadata['base_model'], metadata['base_model_revision'], metadata['direction']) == (config['model_name'], config['model_revision'], direction)\n",
                "    for name, expected in metadata['files'].items():\n",
                "        path = (model_dir/name).resolve()\n",
                "        if not path.is_relative_to(model_dir.resolve()): raise ValueError('Unsafe manifest path')\n",
                "        if path.stat().st_size != expected['bytes'] or file_hash(path) != expected['sha256']: raise ValueError(f'Model checksum mismatch: {path}')\n",
                "    ADAPTER_DIRS[direction] = model_dir\n",
                "print('Verified merged models:', ADAPTER_DIRS)\n",
            ]
        elif "PHASE = 'public'" in source:
            source = source.replace("PHASE = 'public'", "PHASE = 'private'")
            source = source.replace("PROJECT_DIR/'data/test/en-vi-public_test.csv'", "PROJECT_DIR/'data/test/private_test_input.csv'")
            source = source.replace('SOURCE_COLUMN = None', "SOURCE_COLUMN = 'source_markdown'")
            cell['source'] = source.splitlines(keepends=True)
        cell['outputs'] = [] if cell['cell_type'] == 'code' else cell.get('outputs', [])
        if cell['cell_type'] == 'markdown': cell.pop('outputs', None)
    notebook['cells'][0]['source'] = [
        '# Private test — chạy suy luận bằng merged models\n',
        'Kaggle: bật GPU, Internet OFF; attach đúng một project bundle mới, '
        '`en2vi_merged.zip`, `vi2en_merged.zip` và wheelhouse Linux Python 3.13. '
        'Không cần base model ZIP. Chạy trong session mới, Run All.\n',
        'File nộp sau khi dịch đủ 100 tài liệu: '
        '`/kaggle/working/results_submission/results_private_context_v2/submission.zip`. '
        'Private không có reference nên không tính BLEU/chrF local.\n',
    ]
    notebook_path = ROOT/'notebooks/07_private_test_merged_kaggle.ipynb'
    notebook_path.write_text(json.dumps(notebook, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    for cell in notebook['cells']:
        if cell['cell_type'] == 'code': compile(''.join(cell['source']), '<notebook>', 'exec')
    if output.exists(): raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest = {'schema_version': 1, 'purpose': 'Kaggle input for original full-document prediction; private merged models', 'files': {}}
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        def add(name, data):
            archive.writestr('project/'+name, data)
            manifest['files'][name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        for relative in ('src', 'tests', 'scripts', 'submission/configs', 'submission/requirements-inference.txt'):
            path = ROOT/relative
            for file in sorted(path.rglob('*')) if path.is_dir() else [path]:
                if file.is_file() and '__pycache__' not in file.parts and file.suffix not in ('.pyc', '.pyo'):
                    add(file.relative_to(ROOT).as_posix(), file.read_bytes())
        add('data/test/private_test_input.csv', input_path.read_bytes())
        add('notebooks/'+notebook_path.name, notebook_path.read_bytes())
        add('private_preparation_report.json', json.dumps(report, ensure_ascii=False, indent=2).encode())
        archive.writestr('project/bundle_manifest.json', json.dumps(manifest, indent=2))
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None: raise ValueError('Corrupt bundle')
    output.with_suffix('.zip.sha256').write_text(file_hash(output)+'  '+output.name+'\n', encoding='utf-8')
    (output.parent/'private_preparation_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'bundle': str(output), 'notebook': str(notebook_path), **report}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--output', type=Path, default=ROOT/'dist/NLP_results_submission_kaggle_private_merged.zip')
    args = parser.parse_args()
    prepare(args.input, args.output)
