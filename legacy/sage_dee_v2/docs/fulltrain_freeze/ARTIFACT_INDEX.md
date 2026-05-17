# Artifact Index

These paths are recorded for audit and reproducibility. The current repository
does not vendor data, model checkpoints, evaluator artifacts, or ProcNet code.

| Item | Path | Note |
| --- | --- | --- |
| full-train row root | `/data/TJK/DEE/sage-dee/runs/v21_r3_s4_train_size_scaling_seed42/s4_full_or_max_frozen_surface` | R3 Row D source |
| adapter path | `/data/TJK/DEE/sage-dee/runs/v21_r3_s4_train_size_scaling_seed42/s4_full_or_max_frozen_surface/train/artifacts/model/adapter` | S4 full/max adapter |
| S4 full-method test-reference output root | `/data/TJK/DEE/sage-dee/methodology_checks/s4_full_method_test_reference_seed42_20260508T170434Z` | methodology reference |
| merged canonical prediction | `/data/TJK/DEE/sage-dee/methodology_checks/s4_full_method_test_reference_seed42_20260508T170434Z/merged/predictions/DuEE-Fin-dev500/test.canonical.pred.jsonl` | do not modify |
| unified evaluator artifact root | `/data/TJK/DEE/sage-dee/methodology_checks/s4_full_method_test_reference_seed42_20260508T170434Z/evaluator_artifacts/unified/s4_full_method_test_reference_seed42_20260508T182626Z` | strict evaluator output |
| ProcNet-native reference output root | `/data/TJK/DEE/sage-dee/methodology_checks/procnet_native_test_reference_s4_seed42_20260508T163329Z` | Phase13 prediction native reference |
| S4 test-reference ProcNet-native root | `/data/TJK/DEE/sage-dee/methodology_checks/s4_full_method_test_reference_seed42_20260508T170434Z/procnet_native` | S4 methodology reference native score |
| historical Phase 13 run root | `/data/TJK/DEE/sage-dee/runs/phase13_final_test_seed42_recovery_20260506T113047Z` | historical boundary only |
| historical Phase 13 canonical prediction | `/data/TJK/DEE/sage-dee/runs/phase13_final_test_seed42_recovery_20260506T113047Z/predictions/DuEE-Fin-dev500/test.canonical.pred.jsonl` | do not modify |
| historical Phase 13 evaluator root | `/data/TJK/DEE/sage-dee/runs/phase13_final_test_seed42_recovery_20260506T113047Z/evaluator_artifacts/phase13_final_test_once_20260506T140545Z` | locked evidence |
| data root | `/data/TJK/DEE/data/processed/views/evaluator_gold` | server evaluator-gold views |
| evaluator root | `/home/TJK/DEE/dee-eval` | sibling evaluator; do not vendor |
| ProcNet root | `/home/TJK/DEE/procnet` | sibling ProcNet; do not modify |
| Python env | `/home/TJK/.conda/envs/tjk-feg/bin/python` | server Python |
| Qwen model root | `/data/TJK/DEE/models/Qwen` | server model root |

Local project Python for unit validation:

```bash
/home/tjk/miniconda3/envs/feg-dev-py310/bin/python
```
