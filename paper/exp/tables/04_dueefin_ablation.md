| Split | Factor | Setting | F1 | P | R | F1(S) | F1(M) | Note |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| dev (500) | SFT | HF Transformers 4-bit NF4 + LoRA no-SFT | 3.8 | - | - | - | - | 2.1 / 2.9 |
| dev (500) | SFT | HF Transformers 4-bit NF4 + LoRA SFT | 76.7 | - | - | - | - | delta=72.8 |
| dev (500) | SFT | vLLM 0.8.5 BF16 merged no-SFT | 11.2 | - | - | - | - | 2.7 / 2.3 |
| dev (500) | SFT | vLLM 0.8.5 BF16 merged SFT | 72.8 | - | - | - | - | delta=61.5 |
| dev (500) | backend | HF-4bin, k=1 greedy | 76.7 | - | - | - | - | 2.9 / 2.3 / 5 |
| dev (500) | backend | vLLM-bf16, k=1 greedy | 72.8 | - | - | - | - | delta=-3.9 |
| dev (500) | decoding | vLLM 0.8.5 BF16 merged k1 | 72.8 | - | - | - | - | 2.3 / 2.5 / 2.6 / 2.4 / 6 |
| dev (500) | decoding | vLLM 0.8.5 BF16 merged k4 T0.3 | 73.9 | - | - | - | - | 2.3 / 2.5 / 2.6 / 2.4 / 6 |
| dev (500) | decoding | vLLM 0.8.5 BF16 merged k4 T0.5 | 72.7 | - | - | - | - | 2.3 / 2.5 / 2.6 / 2.4 / 6 |
| dev (500) | decoding | vLLM 0.8.5 BF16 merged k4 T0.7 | 72.3 | - | - | - | - | 2.3 / 2.5 / 2.6 / 2.4 / 6 |
| test | backend | SFT, k=1 greedy | 73.5 | 74.0 | 73.0 | 77.2 | 72.0 | vLLM BF16 比 HF 4-bit 主路径低 4.42pp |
| test | no-SFT | vLLM BF16, k=1 greedy | 11.3 | 37.2 | 6.7 | 13.8 | 9.4 | SFT 是主要增益来源 |
| test | decoding | vLLM BF16, SFT | 73.1 | 69.2 | 77.5 | 75.8 | 72.5 | k=4 T=0.7 未优于 vLLM k=1 |
| test | LRD | no-LRD | 78.0 | 76.6 | 79.3 | 79.3 | 77.5 | docs/exp_result.md 7.2 |
| test | LRD | safe-anchor | 78.0 | 76.7 | 79.3 | 79.4 | 77.5 | delta=0.0 |
| dev | LRD | safe-anchor tau=0.90 | 76.8 | - | - | - | 75.5 | docs/exp_result.md 7 |
