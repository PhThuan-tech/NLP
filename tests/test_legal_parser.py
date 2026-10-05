import unittest
from src.vinai_baseline.pipeline.md_parser import parse_document, mask_inline, restore_inline, placeholder_errors, strip_spans
from src.vinai_baseline.pipeline.reassembler import reassemble
from src.vinai_baseline.pipeline.types import Candidate


class ParserTests(unittest.TestCase):
    def test_lossless_structural_cases(self):
        cases=["# Heading  \r\n\r\n> 1. A  \r\n>    a) B\r\n", "- Top\n  - Nested\n    - Third\n", "| A | B |\n| :--- | ---: |\n| | x\\|y |\n| `a|b` | [label](https://a/x(y)) |\n", "---\r\ntitle: hello\r\n---\r\n## Title ### \r\n***\r\n", "~~~py\n# not heading\n~~~\n`inline` and ![image](https://a) [^1]\n", "<div>\n# untouched\n</div>\n\n<!--\nhi\n-->\n", "***bold italic*** **bold *nested*** _italic_\n", "    code\n\n\\* escaped\n", "\ufeff# Unicode — Điều 5\r\nNo final newline"]
        for source in cases:
            with self.subTest(source=source):
                doc=parse_document(source); self.assertEqual(reassemble(doc,identity=True).encode(),source.encode())
                for unit in doc.units: unit.final=Candidate(unit.src_masked)
                self.assertEqual(reassemble(doc),source)
    def test_structural_markers_and_empty_table_cells(self):
        doc=parse_document("| Col | Second |\n| --- | --- |\n| | Giá trị |\n  - Nội dung  \r\n")
        self.assertEqual(len([u for u in doc.units if u.kind=="table_cell"]),3)
        for u in doc.units: u.final=Candidate("Value")
        self.assertEqual(reassemble(doc),"| Value | Value |\n| --- | --- |\n| | Value |\n  - Value  \r\n")
    def test_three_placeholder_formats_nested_order(self):
        for fmt in ("tags","brackets","braces"):
            source="**a [b](https://a/x(y))** and `code` [^1]"; masked, ph=mask_inline(source,fmt)
            self.assertEqual(restore_inline(masked,ph),source); self.assertEqual(placeholder_errors(masked,ph),[])
            self.assertTrue(placeholder_errors(masked.replace(ph[0].token,""),ph))
            broken=masked.replace(ph[0].token,"TEMP").replace(ph[1].token,ph[0].token).replace("TEMP",ph[1].token)
            self.assertTrue(placeholder_errors(broken,ph))
    def test_strip_partial_and_whole_spans(self):
        u=parse_document("**all content**").units[0]; plain,singles,opening,closing,partial=strip_spans(u)
        self.assertEqual((plain,opening,closing,partial),("all content","**","**",False))
        u=parse_document("partial **bold** and `protected`").units[0]; plain,singles,opening,closing,partial=strip_spans(u)
        self.assertTrue(partial); self.assertEqual(len(singles),1); self.assertEqual(restore_inline(plain,singles),"partial bold and `protected`")
    def test_missing_final_is_not_silent(self):
        with self.assertRaises(ValueError): reassemble(parse_document("Text"))
    def test_unterminated_front_matter_is_a_rule_not_lost_text(self):
        doc=parse_document("---\nTranslate this text\n")
        self.assertEqual(len(doc.units),1)
        self.assertEqual(doc.units[0].src_text,"Translate this text")
    def test_fences_inside_quotes_and_lists_are_not_translatable(self):
        for source in ("> ```py\n> # immutable\n> ```\n", "- ```py\n  # immutable\n  ```\n"):
            doc=parse_document(source)
            self.assertEqual(doc.units,[]); self.assertEqual(reassemble(doc),source)


if __name__=="__main__": unittest.main()
