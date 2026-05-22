# DuEE-Fin Test Backend Seed Stability

Metric values are percentages. HF rows use the 4-bit NF4 base model with runtime LoRA; vLLM rows use merged BF16 checkpoints. These rows are backend diagnostics and do not replace the seed-13 HF main-table row.

| Dataset | Split | Backend | Seeds | Legacy-FS F1 | Unified F1 | DocFEE F1 | ExactRec |
|---|---|---|---:|---:|---:|---:|---:|
| DuEE-Fin-dev500 | test | HF-4bin + LoRA, k=1 greedy, no-LRD | 13 | 77.96 | 78.88 | 77.71 | 42.85 |
| DuEE-Fin-dev500 | test | HF-4bin + LoRA, k=1 greedy, no-LRD | 17 | 78.72 | 79.37 | 78.22 | 43.14 |
| DuEE-Fin-dev500 | test | HF-4bin + LoRA, k=1 greedy, no-LRD | 42 | 78.28 | 79.21 | 78.09 | 43.82 |
| DuEE-Fin-dev500 | test | HF-4bin + LoRA, k=1 greedy, no-LRD | mean±std | 78.32±0.38 | 79.15±0.25 | 78.01±0.26 | 43.27±0.50 |
| DuEE-Fin-dev500 | test | vLLM BF16 merged, k=1 greedy | 13 | 75.02 | 75.96 | 74.96 | 38.22 |
| DuEE-Fin-dev500 | test | vLLM BF16 merged, k=1 greedy | 17 | 74.70 | 75.44 | 74.49 | 36.61 |
| DuEE-Fin-dev500 | test | vLLM BF16 merged, k=1 greedy | 42 | 75.83 | 76.75 | 75.94 | 39.56 |
| DuEE-Fin-dev500 | test | vLLM BF16 merged, k=1 greedy | mean±std | 75.18±0.58 | 76.05±0.66 | 75.13±0.74 | 38.13±1.48 |
