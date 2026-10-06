"""Create results.csv and the single-file ZIP required by the competition."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.vinai_baseline.results_submission import build, load_test, validate_archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--phase", choices=["public", "private"], default="public")
    parser.add_argument("--source-column", help="Private input source-text column; inferred only when unambiguous")
    parser.add_argument("--output-dir", type=Path, default=Path("dist/public_results"))
    for direction in ("en2vi", "vi2en"):
        parser.add_argument(f"--{direction}-config", type=Path, default=Path(f"submission/configs/{direction}.json"))
        parser.add_argument(f"--{direction}-model", type=Path, help="Saved best_model adapter or merged model directory")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--maximum-source-tokens", type=int, default=448)
    parser.add_argument("--vi2en-context-lines", action=argparse.BooleanOptionalAction, default=True,
                        help="Join VI-to-EN prose lines split only by source hard wrapping")
    parser.add_argument("--reuse-en2vi-zip", type=Path,
                        help="Validated previous 100-row public submission; reuse only its EN-to-VI rows")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--allow-cpu", action="store_true")
    parser.add_argument("--smoke-documents", type=int, help="Documents per direction; smoke never creates a submission ZIP")
    parser.add_argument("--validate-zip", type=Path, help="Validate an existing prediction ZIP against the original phase input, without loading models")
    args = parser.parse_args()
    if args.validate_zip:
        docs = load_test(args.input, args.phase, args.source_column, expected_documents=50 if args.phase=="public" else 100)
        print(json.dumps(validate_archive(args.validate_zip, docs), indent=2))
    else:
        build(args)


if __name__ == "__main__": main()
