# ChFinAnn vLLM 模块消融快筛

证据来源：`gpu-4090:/data/TJK/DEE/SARGE/runs/`，小型 JSON 快照已拉取到 `paper/exp/data/run_snapshots/chfinann_test_seed13_vllm_ablation_*_mem080/`。

固定设置：ChFinAnn-Doc2EDAG test，seed 13，Qwen3-4B LoRA merged BF16，vLLM，`k=1` greedy，`gpu_memory_utilization=0.80`，`slot_train_limit=50`，Legacy-FS / `legacy_doc2edag`。

| Profile | Legacy-FS F1 | P | R | Single F1 | Multi F1 | TP | FP | FN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| full | 0.8547 | 0.8426 | 0.8671 | 0.8994 | 0.8064 | 25523 | 4766 | 3912 |
| no_surface_memory | 0.8538 | 0.8483 | 0.8595 | 0.9035 | 0.7999 | 25298 | 4525 | 4137 |
| no_slot_plan | 0.8567 | 0.8403 | 0.8739 | 0.8963 | 0.8139 | 25723 | 4890 | 3712 |

Delta vs full：

| Profile | Delta F1 | Delta P | Delta R | Delta Single F1 | Delta Multi F1 | 解释 |
|---|---:|---:|---:|---:|---:|---|
| no_surface_memory | -0.0009 | +0.0056 | -0.0076 | +0.0041 | -0.0066 | Surface Memory 增加召回倾向，但也引入候选噪声；净 F1 基本持平 |
| no_slot_plan | +0.0020 | -0.0024 | +0.0068 | -0.0030 | +0.0074 | 去掉 Slot Plan 后召回和 multi-event F1 更高，提示当前 train-prior plan 可能过度约束多事件展开 |

解释边界：这是 vLLM 快筛，不替代 HF 主后端结论；但它足以反驳“Surface Memory / Slot Plan 是稳定正向模块”的强说法。结合 DuEE-Fin HF 消融，两个模块应降级为辅助/诊断，不进入主贡献。
