# Placeholder survival

Status: pending real-model generation. Parser tests cover tags, brackets, and
braces, including nested pairs and protected singles. These are correctness
tests, not evidence of model survival.

The fixed VI→EN dev contains **zero units with paired inline markup**, after
parsing 2,783 records into 14,319 units. Therefore the requested measurement on
200 dev units cannot be performed on this corpus. The evaluation CLI reports
sample availability and refuses to declare a winning format without real data.
External Markdown fixtures may measure robustness separately, but cannot be
presented as the fixed-dev measurement. Default format `brackets` is provisional.
