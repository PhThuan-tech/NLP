from __future__ import annotations

import unittest

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
from src.data.semantic_filter import reverse_direction, score_batch


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


if __name__ == "__main__":
    unittest.main()
