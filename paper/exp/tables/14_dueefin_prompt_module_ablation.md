| Backend | Profile | Docs | gmem | Legacy-FS | Unified | DocFEE | ExactRec | Note |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| HF-4bin + LoRA | full | 1171 | - | 78.0 | 78.9 | 77.7 | 42.8 | Primary DuEE-Fin test result; no-LRD remains the main path. |
| HF-4bin + LoRA | no_surface_memory | 1171 | - | 78.1 | 79.0 | 77.8 | 42.9 | HF-4bit confirmation for Surface Memory removal; no_slot_plan HF confirmation is still running. |
| vLLM-bf16 merged | full | 1171 | - | 75.0 | 76.0 | 75.0 | 38.2 | Fresh vLLM BF16 merged backend rerun; kept as diagnostic backend cross-check, not main result. |
| vLLM-bf16 merged | no_surface_memory | 1171 | 0.7 | 2.1 | 2.1 | 2.1 | 0.9 | vLLM full-test fast screen; removal of surface candidates collapsed recall under gpu_memory_utilization=0.70. |
| vLLM-bf16 merged | no_slot_plan | 1171 | 0.7 | 1.6 | 1.7 | 1.6 | 0.8 | vLLM full-test fast screen; removal of slot plan collapsed recall under gpu_memory_utilization=0.70. |
| vLLM-bf16 merged | no_surface_or_slot | 1171 | 0.7 | 75.5 | 76.4 | 75.2 | 37.6 | vLLM full-test fast screen; combined removal stayed near full-vLLM level, indicating backend/prompt interaction rather than simple additive module effect. |
| vLLM-bf16 merged | schema_only | 1171 | 0.7 | 65.5 | 66.2 | 65.0 | 18.8 | vLLM full-test coarse lower-bound diagnostic; not a single-variable module ablation. |
| vLLM-bf16 merged | direct_json | 1171 | 0.7 | 0.0 | 0.0 | 0.0 | 0.0 | vLLM full-test direct JSON lower bound; extraction failed completely. |
