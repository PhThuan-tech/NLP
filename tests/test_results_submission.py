import csv
import io
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

from src.vinai_baseline.results_submission import (
    TestDocument, load_test, official_metrics, translate_document,
    validate_archive, validate_rows, write_submission,
)
from src.vinai_baseline.pipeline.types import Candidate


class WordTokenizer:
    def __call__(self, text, **kwargs):
        return {"input_ids": list(range(len(text.split()) + 2))}


class ResultsSubmissionTests(unittest.TestCase):
    def test_public_sources_generate_both_directions_without_changing_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"input.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["sample_id", "english_markdown", "vietnamese_markdown"])
                writer.writeheader()
                for i in range(50):
                    writer.writerow({"sample_id": f"Law/{i:03}", "english_markdown": "# English", "vietnamese_markdown": "# Tiếng Việt"})
            documents = load_test(path, "public")
            self.assertEqual(len(documents), 100)
            self.assertEqual(documents[0].sample_id, "Law/000")
            self.assertEqual(documents[1].source, "# Tiếng Việt")
            with self.assertRaises(ValueError): load_test(path, "public", expected_documents=100)

    def test_private_direction_is_supplied_and_references_are_not_invented(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"private.csv"
            path.write_text('sample_id,direction,source\nA,vi-en,"Văn bản"\n', encoding="utf-8")
            documents = load_test(path, "private", expected_documents=1)
            self.assertIsNone(documents[0].reference)
            rows = [{"sample_id": "A", "direction": "vi-en", "translation": "Document"}]
            self.assertEqual(official_metrics(rows, documents)["status"], "not_scored_no_private_references")
            path.write_text('sample_id,direction,source\nA,vi2en,Text\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "direction"): load_test(path, "private", expected_documents=1)

    def test_archive_preserves_unicode_quotes_commas_crlf_and_large_documents(self):
        document = TestDocument("Law/007", "en-vi", "source")
        text = '# Điều 1\r\n"Nghĩa vụ", điều kiện\n' + "Văn bản "*20000
        row = {"sample_id": document.sample_id, "direction": document.direction, "translation": text}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            report = write_submission([row], [document], output)
            self.assertEqual(report["status"], "passed")
            with zipfile.ZipFile(output/"submission.zip") as archive:
                self.assertEqual(archive.namelist(), ["results.csv"])
                parsed = list(csv.DictReader(io.StringIO(archive.read("results.csv").decode("utf-8"), newline="")))
            self.assertEqual(parsed, [row])
            with self.assertRaises(FileExistsError): write_submission([row], [document], output)

    def test_reject_missing_duplicate_wrong_direction_and_empty_predictions(self):
        documents = [TestDocument("A", "en-vi", "source"), TestDocument("A", "vi-en", "nguồn")]
        rows = [{"sample_id": "A", "direction": d, "translation": "Text"} for d in ("en-vi", "vi-en")]
        for wrong in (rows[:1], [rows[0], rows[0]], [rows[0], {**rows[1], "direction": "vi2en"}],
                      [rows[0], {**rows[1], "translation": " \n"}], [rows[0], {**rows[1], "sample_id": "B"}]):
            with self.subTest(wrong=wrong), self.assertRaises(ValueError): validate_rows(wrong, documents)

    def test_nested_csv_is_rejected_and_prediction_alias_is_accepted(self):
        documents = [TestDocument("A", "en-vi", "Source")]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"submission.zip"
            with zipfile.ZipFile(path, "w") as archive: archive.writestr("folder/results.csv", "sample_id,direction,translation\nA,en-vi,Text\n")
            with self.assertRaisesRegex(ValueError, "root"): validate_archive(path, documents)
            with zipfile.ZipFile(path, "w") as archive: archive.writestr("results.csv", "sample_id,direction,prediction\nA,en-vi,Text\n")
            self.assertEqual(validate_archive(path, documents)["rows"], 1)

    def test_official_metric_is_chrf_without_word_ngrams_and_equal_direction_weight(self):
        reference = "The parties shall comply with all obligations set out in this agreement."
        documents = [TestDocument(str(i), direction, "source", reference) for i, direction in enumerate(("en-vi", "en-vi", "vi-en"))]
        rows = [{"sample_id": d.sample_id, "direction": d.direction,
                 "translation": reference if d.direction=="en-vi" else "Entirely unrelated text."} for d in documents]
        report = official_metrics(rows, documents)
        self.assertIn("nw:0", report["per_direction"]["en-vi"]["signatures"]["chrF"])
        self.assertIn("tok:13a", report["per_direction"]["en-vi"]["signatures"]["BLEU"])
        self.assertIn("smooth:exp", report["per_direction"]["en-vi"]["signatures"]["BLEU"])
        for metric in ("BLEU", "chrF"):
            scores = [v[metric] for v in report["per_direction"].values()]
            self.assertAlmostEqual(report["macro_average"][metric], sum(scores)/2)

    def test_markdown_syntax_stays_local_and_all_text_is_translated(self):
        source = '# Heading\r\n\r\n- **Obligation** and [conditions](https://example.org/a) with `ID_123`.\r\n\r\n| Title | Value |\r\n| --- | --- |\r\n| Legal text | 123 |\r\n\r\n    MINISTRY OF JUSTICE\r\n'
        seen = []
        def generate(texts):
            seen.extend(texts)
            return [[Candidate("Translated " + text, reached_token_cap=False)] for text in texts]
        output, report = translate_document(source, "A", WordTokenizer(), generate)
        self.assertIn('# Translated Heading\r\n', output)
        self.assertIn('**Translated Obligation**', output)
        self.assertIn('[Translated conditions](https://example.org/a)', output)
        self.assertIn('`ID_123`', output)
        self.assertIn('| --- | --- |\r\n', output)
        self.assertIn('    Translated MINISTRY OF JUSTICE\r\n', output)
        self.assertEqual(output.count('\r\n'), source.count('\r\n'))
        self.assertTrue(report['invariants']['unique_ordered_ids'])
        self.assertFalse(any('⟦' in text or 'https://' in text or 'ID_123' in text for text in seen))
        self.assertIn('Legal text', seen)

    def test_long_spans_are_split_without_omitting_words(self):
        source = ' '.join('word'+str(i) for i in range(60))
        def identity(texts): return [[Candidate(t, reached_token_cap=False)] for t in texts]
        output, report = translate_document(source, 'A', WordTokenizer(), identity, source_budget=15)
        self.assertEqual(output, source)
        self.assertGreater(report['translated_spans'], 1)

    def test_cap_triggers_smaller_split_and_empty_indivisible_span_fails(self):
        source = ' '.join('word'+str(i) for i in range(20))
        calls = []
        def generate(texts):
            calls.append(texts)
            return [[Candidate(t, reached_token_cap=len(calls)==1)] for t in texts]
        output, report = translate_document(source, 'A', WordTokenizer(), generate, source_budget=24)
        self.assertEqual(output, source)
        self.assertEqual(report['split_after_cap'], 1)
        with self.assertRaisesRegex(RuntimeError, 'indivisible'):
            translate_document('Obligation', 'A', WordTokenizer(), lambda texts: [[Candidate('')] for t in texts])

    def test_interrupted_full_run_resumes_and_only_publishes_complete_archive(self):
        from contextlib import redirect_stdout
        from src.vinai_baseline.results_submission import build
        class Model:
            def to(self, **kwargs): return self
        class Generator:
            calls = 0
            fail = True
            def __init__(self, *args): pass
            def __call__(self, texts):
                Generator.calls += 1
                if Generator.fail and Generator.calls == 3: raise RuntimeError('simulated interruption')
                return [[Candidate('Translated '+t, reached_token_cap=False)] for t in texts]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root/'input.csv'
            with path.open('w', encoding='utf-8', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=['sample_id','english_markdown','vietnamese_markdown'])
                writer.writeheader()
                for i in range(50): writer.writerow({'sample_id':str(i), 'english_markdown':f'English document {i}', 'vietnamese_markdown':f'Vietnamese document {i}'})
            args = SimpleNamespace(input=path, phase='public', source_column=None, output_dir=root/'output',
                batch_size=8, maximum_source_tokens=448, allow_cpu=True, smoke_documents=None, resume=False,
                en2vi_config=Path('submission/configs/en2vi.json'), vi2en_config=Path('submission/configs/vi2en.json'),
                en2vi_model=root/'en', vi2en_model=root/'vi')
            with patch('torch.cuda.is_available', return_value=False), \
                 patch('src.vinai_baseline.results_submission.model_identity', return_value={'weights':'fixed'}), \
                 patch('src.vinai_baseline.inference.load_inference_model', return_value=(WordTokenizer(), Model())), \
                 patch('src.vinai_baseline.results_submission.FrozenGenerator', Generator), redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(RuntimeError, 'interruption'): build(args)
                self.assertFalse((args.output_dir/'submission.zip').exists())
                self.assertEqual(len(list((args.output_dir/'documents').glob('*.json'))), 2)
                Generator.fail = False
                args.resume = True
                report = build(args)
                self.assertEqual(report['rows'], 100)
                self.assertEqual(Generator.calls, 101)  # 3 attempted, then 98 uncached documents.
                self.assertEqual(validate_archive(args.output_dir/'submission.zip', load_test(path,'public'))['rows'], 100)


if __name__ == '__main__': unittest.main()
