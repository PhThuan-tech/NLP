from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd
import numpy as np

from src.data.prepare import (
    PreparationConfig,
    add_hashes,
    align_blocks,
    normalize_text,
    split_logical_blocks,
    stratified_document_split,
)
from src.data.finalize import (
    FinalizationConfig,
    deterministic_filter,
    finalize_dataset,
    reverse_direction,
    score_batch,
    semantic_filter,
)


class NormalizeTextTests(unittest.TestCase):
    def test_normalizes_line_endings_and_repeated_blank_lines(self) -> None:
        source = "A  \r\n\r\n\r\nB\u200b\rC"
        self.assertEqual(normalize_text(source), "A\n\nB\nC")


class LogicalBlockTests(unittest.TestCase):
    def test_joins_soft_wrapped_lines_and_preserves_article(self) -> None:
        text = (
            "Article 1. Scope\n"
            "Organizations shall comply with this\n"
            "Decree and relevant laws.\n\n"
            "1. First obligation;\n"
            "2. Second obligation."
        )
        blocks = split_logical_blocks(text)
        self.assertEqual(blocks[0].kind, "article")
        self.assertEqual(blocks[0].anchor, "article:1")
        self.assertIn("this Decree", blocks[1].text)
        self.assertEqual([block.kind for block in blocks[-2:]], ["list_item", "list_item"])

    def test_drops_ornamental_separator(self) -> None:
        blocks = split_logical_blocks("TITLE\n-------\nContent.")
        self.assertFalse(any(block.text == "-------" for block in blocks))


class AlignmentTests(unittest.TestCase):
    def test_aligns_matching_legal_anchors(self) -> None:
        en = split_logical_blocks("Article 1. Scope\nThe rule applies to organizations.")
        vi = split_logical_blocks("Điều 1. Phạm vi\nQuy định áp dụng với các tổ chức.")
        alignments = align_blocks(en, vi, PreparationConfig(minimum_alignment_score=0.2))
        self.assertEqual(alignments[0].operation, "1-1")
        self.assertTrue(alignments[0].accepted)
        self.assertIn("Article 1", alignments[0].english)
        self.assertIn("Điều 1", alignments[0].vietnamese)

    def test_skips_extra_block_and_realigns_at_next_anchor(self) -> None:
        en = split_logical_blocks(
            "Article 1. Scope\nEnglish scope.\n"
            "An English-only note.\nArticle 2. Subjects\nEnglish subjects."
        )
        vi = split_logical_blocks(
            "Điều 1. Phạm vi\nPhạm vi tiếng Việt.\n"
            "Điều 2. Đối tượng\nĐối tượng tiếng Việt."
        )
        config = PreparationConfig(minimum_alignment_score=0.2)
        alignments = align_blocks(en, vi, config)
        article_two = [
            item for item in alignments
            if "Article 2" in item.english or "Điều 2" in item.vietnamese
        ]
        self.assertEqual(len(article_two), 1)
        self.assertIn("Article 2", article_two[0].english)
        self.assertIn("Điều 2", article_two[0].vietnamese)


class SplitTests(unittest.TestCase):
    def test_default_split_seed_is_67(self) -> None:
        self.assertEqual(PreparationConfig().seed, 67)

    def test_duplicate_source_stays_in_one_split_and_split_is_deterministic(self) -> None:
        rows = []
        for category in ["A", "B"]:
            for index in range(10):
                rows.append(
                    {
                        "sample_id": f"{category}/{index}",
                        "category": category,
                        "english_markdown": f"English {category} {index}",
                        "vietnamese_markdown": f"Vietnamese {category} {index}",
                    }
                )
        rows.append(
            {
                "sample_id": "A/duplicate-source",
                "category": "A",
                "english_markdown": "English A 0",
                "vietnamese_markdown": "Alternative translation",
            }
        )
        frame = add_hashes(pd.DataFrame(rows))
        config = PreparationConfig(seed=7, dev_ratio=0.2)
        first = stratified_document_split(frame, config)
        second = stratified_document_split(frame, config)
        self.assertEqual(first["split"].tolist(), second["split"].tolist())
        duplicate_source = first.loc[
            first["english_markdown"].isin(["English A 0"]), "split"
        ]
        self.assertEqual(duplicate_source.nunique(), 1)
        self.assertEqual(set(first["split"]), {"train", "dev"})

    def test_different_seed_changes_group_selection_without_leakage(self) -> None:
        rows = []
        for category in ["A", "B"]:
            for index in range(30):
                rows.append(
                    {
                        "sample_id": f"{category}/{index}",
                        "category": category,
                        "english_markdown": f"English {category} {index}",
                        "vietnamese_markdown": f"Vietnamese {category} {index}",
                    }
                )
        frame = add_hashes(pd.DataFrame(rows))
        seed_7 = stratified_document_split(
            frame, PreparationConfig(seed=7, dev_ratio=0.2)
        )
        seed_19 = stratified_document_split(
            frame, PreparationConfig(seed=19, dev_ratio=0.2)
        )
        dev_7 = set(seed_7.loc[seed_7["split"] == "dev", "sample_id"])
        dev_19 = set(seed_19.loc[seed_19["split"] == "dev", "sample_id"])
        self.assertNotEqual(dev_7, dev_19)
        self.assertEqual(len(dev_7), 12)
        self.assertEqual(len(dev_19), 12)
        for split_frame in [seed_7, seed_19]:
            counts = split_frame.groupby(["split", "category"]).size()
            self.assertEqual(counts.to_dict(), {
                ("dev", "A"): 6,
                ("dev", "B"): 6,
                ("train", "A"): 24,
                ("train", "B"): 24,
            })


class FakeEncoder:
    def encode(self, sentences, **kwargs):
        vectors = []
        for sentence in sentences:
            if "matching" in sentence or "tương ứng" in sentence:
                vectors.append([1.0, 0.0])
            else:
                vectors.append([0.0, 1.0])
        return np.asarray(vectors, dtype=np.float32)


class SemanticFilterTests(unittest.TestCase):
    def test_scores_parallel_pair_higher_than_mismatch(self) -> None:
        records = [
            {"source": "matching source", "target": "bản dịch tương ứng"},
            {"source": "matching source", "target": "unrelated target"},
        ]
        scores = score_batch(records, FakeEncoder(), batch_size=2)
        self.assertAlmostEqual(float(scores[0]), 1.0)
        self.assertAlmostEqual(float(scores[1]), 0.0)

    def test_reverses_direction_without_losing_quality_score(self) -> None:
        record = {
            "segment_id": "doc::segment-0001::en2vi",
            "direction": "en2vi",
            "source_lang": "en",
            "target_lang": "vi",
            "source": "English",
            "target": "Tiếng Việt",
            "source_word_count": 1,
            "target_word_count": 2,
            "semantic_similarity": 0.9,
        }
        reversed_record = reverse_direction(record)
        self.assertEqual(reversed_record["source"], "Tiếng Việt")
        self.assertEqual(reversed_record["target"], "English")
        self.assertEqual(reversed_record["semantic_similarity"], 0.9)
        self.assertTrue(reversed_record["segment_id"].endswith("::vi2en"))


def make_segment(
    segment_id: str,
    source: str,
    target: str,
    *,
    alignment_score: float = 0.9,
) -> dict[str, object]:
    return {
        "segment_id": f"{segment_id}::en2vi",
        "sample_id": segment_id.split("::", 1)[0],
        "category": "test",
        "direction": "en2vi",
        "source_lang": "en",
        "target_lang": "vi",
        "source": source,
        "target": target,
        "source_word_count": len(source.split()),
        "target_word_count": len(target.split()),
        "alignment_score_min": alignment_score,
    }


class DatasetFinalizationTests(unittest.TestCase):
    def test_deterministic_filter_rejects_identity_duplicates_and_dev_leakage(self) -> None:
        config = FinalizationConfig(minimum_alignment_score=0.75)
        good = make_segment("doc/1::segment-0001", "The first rule applies.", "Quy tắc đầu tiên được áp dụng.")
        duplicate = make_segment("doc/2::segment-0001", " the first rule applies. ", "Quy tắc đầu tiên được áp dụng.")
        identical = make_segment("doc/3::segment-0001", "same text", " SAME TEXT ")
        low_score = make_segment("doc/4::segment-0001", "English provision", "Quy định tiếng Việt", alignment_score=0.5)
        accepted, rejected = deterministic_filter(
            [good, duplicate, identical, low_score],
            config=config,
            forbidden_sources={"reserved validation source"},
        )
        self.assertEqual([row["segment_id"] for row in accepted], [good["segment_id"]])
        self.assertEqual(
            [row["finalization_rejection_reason"] for row in rejected],
            [
                "duplicate_pair_same_split",
                "identical_source_target",
                "alignment_score_below_threshold",
            ],
        )

    def test_language_gate_rejects_reversed_language_pair(self) -> None:
        row = make_segment(
            "doc/1::segment-0001",
            "Điều này được quy định trong luật và có trách nhiệm của chính phủ.",
            "The government shall apply this article and section of the law.",
        )
        accepted, rejected = deterministic_filter(
            [row], config=FinalizationConfig()
        )
        self.assertFalse(accepted)
        self.assertEqual(
            rejected[0]["finalization_rejection_reason"],
            "source_looks_vietnamese",
        )

    def test_semantic_gate_keeps_only_matching_pair(self) -> None:
        rows = [
            make_segment("doc/1::segment-0001", "matching source", "bản dịch tương ứng"),
            make_segment("doc/1::segment-0002", "matching source", "unrelated target"),
        ]
        accepted, rejected = semantic_filter(
            rows,
            encoder=FakeEncoder(),
            threshold=0.72,
            batch_size=2,
        )
        self.assertEqual(len(accepted), 1)
        self.assertEqual(accepted[0]["semantic_similarity"], 1.0)
        self.assertEqual(
            rejected[0]["finalization_rejection_reason"],
            "semantic_similarity_below_threshold",
        )

    def test_finalize_writes_both_directions_and_frozen_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_dir = root / "v1"
            output_dir = root / "v2"
            input_dir.mkdir()
            rows = {
                "train": [
                    make_segment("train/1::segment-0001", "A unique English rule.", "Một quy tắc tiếng Việt duy nhất."),
                    make_segment("train/2::segment-0001", "Validation sentence.", "Câu xác thực."),
                ],
                "dev": [
                    make_segment("dev/1::segment-0001", "Validation sentence.", "Câu xác thực."),
                ],
                "public_test": [
                    make_segment("test/1::segment-0001", "Public English sentence.", "Câu tiếng Việt công khai."),
                ],
            }
            for split, split_rows in rows.items():
                path = input_dir / f"segments_{split}_en2vi.jsonl"
                path.write_text(
                    "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in split_rows),
                    encoding="utf-8",
                )
            (input_dir / "manifest.json").write_text(
                json.dumps({"dataset_id": "parent_v1"}), encoding="utf-8"
            )

            manifest = finalize_dataset(
                input_dir,
                output_dir,
                FinalizationConfig(dataset_id="clean_v2", split_seed=67),
            )

            self.assertEqual(manifest["split_contract"]["seed"], 67)
            self.assertEqual(manifest["counts"]["segments_train_en2vi"], 1)
            self.assertEqual(
                manifest["rejection_reasons"]["train"],
                {"source_overlap_with_dev": 1},
            )
            vi_row = json.loads(
                (output_dir / "segments_dev_vi2en.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()[0]
            )
            self.assertEqual(vi_row["direction"], "vi2en")
            self.assertEqual(vi_row["source"], "Câu xác thực.")
            self.assertIn("sha256", manifest["files"]["segments_dev_en2vi.jsonl"])

    def test_semantically_rejected_dev_does_not_reserve_train_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_dir = root / "v1"
            output_dir = root / "v2"
            input_dir.mkdir()
            rows = {
                "train": [
                    make_segment("train/1::segment-0001", "matching shared", "bản dịch tương ứng"),
                ],
                "dev": [
                    make_segment("dev/1::segment-0001", "matching shared", "unrelated target"),
                    make_segment("dev/2::segment-0001", "matching dev only", "matching dev target"),
                ],
                "public_test": [
                    make_segment("test/1::segment-0001", "matching public", "bản dịch tương ứng"),
                ],
            }
            for split, split_rows in rows.items():
                (input_dir / f"segments_{split}_en2vi.jsonl").write_text(
                    "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in split_rows),
                    encoding="utf-8",
                )
            manifest = finalize_dataset(
                input_dir,
                output_dir,
                FinalizationConfig(
                    dataset_id="semantic_v2",
                    semantic_model="fake",
                    minimum_semantic_similarity=0.72,
                ),
                encoder=FakeEncoder(),
            )
            self.assertEqual(manifest["counts"]["segments_dev_en2vi"], 1)
            self.assertEqual(manifest["counts"]["segments_train_en2vi"], 1)


if __name__ == "__main__":
    unittest.main()
