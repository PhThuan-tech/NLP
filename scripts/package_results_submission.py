"""Package offline prediction generation inputs; this ZIP is not a competition submission."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('dist/NLP_results_submission_kaggle.zip'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    if output.exists(): raise FileExistsError('Choose a new output filename; existing bundles are immutable')
    selected = ('README.md', 'src', 'tests', 'scripts', 'docs', 'submission/configs',
                'submission/resources', 'submission/requirements-inference.txt', 'requirements.txt',
                'notebooks/06_results_submission_kaggle.ipynb', 'data/test/en-vi-public_test.csv')
    files = []
    for relative in selected:
        path = root/relative
        if not path.exists(): raise FileNotFoundError(path)
        files.extend(path.rglob('*') if path.is_dir() else [path])
    manifest = {'schema_version': 1, 'purpose': 'Kaggle input for original full-document prediction; no training',
                'files': {}, 'adapters': {}}
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix('.zip.tmp')
    with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        def add(name, data):
            bundle.writestr('project/'+name, data)
            manifest['files'][name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
        for path in sorted(set(files)):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix not in {'.pyc', '.pyo'}:
                add(path.relative_to(root).as_posix(), path.read_bytes())
        for direction in ('en2vi', 'vi2en'):
            candidates = list((root/'modelAI').glob(f'*{direction}*zip'))
            if len(candidates) != 1: raise ValueError(f'Expected one trained {direction} archive: {candidates}')
            config = json.loads((root/f'submission/configs/{direction}.json').read_text(encoding='utf-8'))
            with zipfile.ZipFile(candidates[0]) as archive:
                metadata = json.loads(archive.read('best_model/adapter_config.json'))
                if metadata.get('base_model_name_or_path') != config['model_name']:
                    raise ValueError(f'Wrong adapter base for {direction}')
                if metadata.get('revision') != config['model_revision']:
                    raise ValueError(f'Wrong adapter revision for {direction}')
                for item in archive.infolist():
                    path = Path(item.filename)
                    if path.is_absolute() or '..' in path.parts or '\\' in item.filename: raise ValueError('Unsafe model archive path')
                    if len(path.parts)==2 and path.parts[0]=='best_model' and path.suffix in {'.json', '.model', '.safetensors'} and not item.is_dir():
                        add(f'models/{direction}/{path.name}', archive.read(item))
                manifest['adapters'][direction] = {'source_archive': candidates[0].name,
                    'weight_sha256': hashlib.sha256(archive.read('best_model/adapter_model.safetensors')).hexdigest()}
        bundle.writestr('project/bundle_manifest.json', json.dumps(manifest, indent=2))
    with zipfile.ZipFile(temporary) as check:
        if check.testzip() is not None: raise ValueError('Corrupt project bundle')
    temporary.replace(output)
    checksum = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix('.zip.sha256').write_text(checksum+'  '+output.name+'\n', encoding='utf-8')
    print(json.dumps({'output': str(output), 'bytes': output.stat().st_size, 'sha256': checksum,
                      'adapters': manifest['adapters']}, indent=2))


if __name__ == '__main__': main()
