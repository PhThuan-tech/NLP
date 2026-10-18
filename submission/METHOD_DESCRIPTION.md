# VinAI-Legal-LoRA

Our system uses two direction-specific sequence-to-sequence models for
English-to-Vietnamese and Vietnamese-to-English legal document translation.
They are based on the mBART-style `vinai/vinai-translate-en2vi-v2` and
`vinai/vinai-translate-vi2en-v2` checkpoints. Each model has 12 encoder
layers, 12 decoder layers, hidden size 1024, and 16 attention heads. The two
deployed models contain 846,533,034 parameters in total, below the 3-billion
parameter limit.

The legal parallel corpus was normalized and aligned at document and logical
block level. Duplicate document groups were kept in the same split to reduce
leakage, and the split was stratified by legal category with seed 67. Training
pairs were filtered with a minimum alignment score of 0.75 and a minimum
LaBSE semantic similarity of 0.70. The resulting frozen dataset contains
27,756 training segments and 2,783 development segments for each direction.

Domain adaptation was performed independently for each direction using LoRA.
Adapters were applied to the `q_proj` and `v_proj` attention projections with
rank 16, alpha 32, and dropout 0.05. Training used 3 epochs, learning rate
5e-5, weight decay 0.01, warmup ratio 0.05, label smoothing 0.1, FP16,
gradient checkpointing, micro-batch size 4, and 4 gradient accumulation
steps. The best checkpoint was selected using chrF++ on the development set.

For deployment, each adapter was merged into its corresponding base model.
Inference is fully local and does not call external APIs or model hubs.
Documents are split deterministically into chunks of at most 448 source
tokens and restored in their original order. English-to-Vietnamese decoding
uses beam size 2; Vietnamese-to-English uses beam size 4. Both use length
penalty 1.1, repetition penalty 1.0, and no-repeat trigram blocking.

The complete system, including both merged models and all runtime
dependencies, is distributed as a self-contained CUDA Docker image. The
service accepts UTF-8 Markdown through direction-specific or automatically
detected translation endpoints. A Bash client accepts the service URL, input
Markdown path, and output Markdown path as its three arguments and reports
runtime and throughput statistics.
