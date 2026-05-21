| Split | Factor | Setting | F1 | P | R | F1(S) | F1(M) | Note |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| dev (full-dev, 3204) | SFT | vLLM 0.8.5 BF16 no-SFT | 18.6 | - | - | - | - | 3.4 / 3.3 |
| dev (full-dev, 3204) | SFT | vLLM 0.8.5 BF16 SFT | 85.5 | - | - | - | - | delta=66.9 |
| dev (500) | backend | HF-4bin, k=1 greedy | 84.4 | - | - | - | - | 3.1 / 3.2 / 5 |
| dev (500) | backend | vLLM-bf16, k=1 greedy | 84.2 | - | - | - | - | delta=-0.3 |
| dev (full-dev, 3204) | decoding | vLLM 0.8.5 BF16 merged k1 | 85.5 | - | - | - | - | 3.3 / 3.5 / 6 |
| dev (full-dev, 3204) | decoding | vLLM 0.8.5 BF16 merged k4 T0.7 | 84.3 | - | - | - | - | 3.3 / 3.5 / 6 |
| test | no-SFT | vLLM BF16, k=1 greedy | 24.8 | 61.2 | 15.6 | 38.9 | 6.8 | SFT 是主要增益来源 |
| test | decoding | vLLM BF16, SFT | 84.2 | 79.5 | 89.5 | 87.5 | 80.7 | k=4 T=0.7 低于 k=1 主路径 1.26pp |
