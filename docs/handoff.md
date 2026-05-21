# SARGE Handoff

> Last updated: 2026-05-21 23:15 UTC+8
> Project: CCKS 2026 main submission candidate
> Current status: seed13 test evidence consolidated; seed17/42 extension jobs are running or queued on `gpu-4090`.

---

## 1. Paths And Environments

| Resource | Local | Server |
|---|---|---|
| Project root | `/home/tjk/myProjects/masterProjects/DEE/SARGE/` | `/data/TJK/DEE/SARGE/` |
| Python | `/home/tjk/miniconda3/envs/feg-dev-py310/bin/python` | `/data/TJK/envs/sarge_vllm_full/bin/python` |
| Data | `data/` | `data/` |
| Models | `models/` | `models/` |
| Qwen3-4B | `models/Qwen/Qwen3-4B-Instruct-2507` | `models/Qwen/Qwen3-4B-Instruct-2507` |
| Evaluator | `evaluator/` | `evaluator/` |
| Runs | small JSON snapshots under `paper/exp/data/run_snapshots/` | `/data/TJK/DEE/SARGE/runs/` |

Offline runtime flags:

```bash
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_DATASETS_OFFLINE=1
export TORCHDYNAMO_DISABLE=1
export TORCH_COMPILE_DISABLE=1
```

GPU jobs run only on `gpu-4090`. Prefer an idle GPU, set `CUDA_VISIBLE_DEVICES`, and never kill non-`TJK` processes.

---

## 2. Repository State

Local and server were checked on `main` at:

```text
7ddc3da97044050512f43d4fac94fea60957d94c
```

This handoff intentionally keeps runtime logs and server `runs/` as server artifacts. Git tracks only source, docs, paper assets, and small JSON evidence snapshots needed for reproducible tables.

---

## 3. Authoritative Evidence Layer

| Artifact | Path |
|---|---|
| Experiment registry | `paper/exp/data/asset_registry.json` |
| Small run snapshots | `paper/exp/data/run_snapshots/` |
| Generated experiment summary | `paper/exp/seed13_summary.md` |
| Markdown tables | `paper/exp/tables/` |
| Current result narrative | `docs/exp_result.md` |
| ACL-family draft | `paper/emnlp_aacl_draft/main.tex` |
| Draft build script | `paper/emnlp_aacl_draft/scripts/build_assets.py` |

Main paper numbers must come from real non-mock runs with complete eval JSON and traceable manifests. Running jobs stay in status tables until their eval files exist.

---

## 4. Current Main Results

The main comparison metric is Legacy-FS / `legacy_doc2edag`. Unified-Strict, DocFEE, and ExactRec are diagnostics and must not be mixed into the main baseline table.

| Dataset | Split | Seed | Main setting | Legacy-FS F1 | Unified F1 | DocFEE F1 | ExactRec |
|---|---|---:|---|---:|---:|---:|---:|
| ChFinAnn-Doc2EDAG | test | 13 | HF-4bin + LoRA, k=1 greedy | 0.8603 | 0.8742 | 0.8653 | 0.5842 |
| DuEE-Fin-dev500 | test | 13 | HF-4bin + LoRA, k=1 greedy, no-LRD | 0.7796 | 0.7888 | 0.7771 | 0.4285 |

ChFinAnn was promoted from the older vLLM BF16 line to the HF-4bin line after full-test backend cross-check. DuEE-Fin remains HF-4bin no-LRD as the main path.

---

## 5. Important Findings

- Greedy `k=1` is the default production path; `k=4` sampling did not improve either dataset in completed test ablations.
- LoRA SFT is the dominant gain source. No-SFT baselines are very low, especially DuEE-Fin HF no-SFT F1 `0.0330`.
- vLLM BF16 is useful as a diagnostic backend, but it underperforms HF-4bin on both completed full-test backend checks.
- Safe-anchor LRD on DuEE-Fin test changes Legacy-FS F1 only from `0.7796` to `0.7800`; keep it diagnostic/appendix unless a later fair candidate-contract run shows a real gain.
- Seed17 dev LRD F1 `0.3354` is invalid as a performance number because it used all k=4 parsed candidates instead of MRS-selected/fair k=1-compatible candidates.

---

## 6. Active Remote Jobs

| Task | GPU | Status | Log |
|---|---:|---|---|
| DuEE-Fin test seed17 HF-4bin + LoRA k=1 | 0 | running | `logs/sarge_infer_DuEE-Fin-dev500_test_seed17_4bitNF4_k1_20260521T2141Z.log` |
| DuEE-Fin test seed42 HF-4bin + LoRA k=1 | 0 | running | `logs/sarge_infer_DuEE-Fin-dev500_test_seed42_4bitNF4_k1_20260521T2221Z.log` |
| ChFinAnn train seed17 HF-4bin LoRA ep2 `--skip-eval` | 1 | running | `logs/sarge_sft_ChFinAnn-Doc2EDAG_s17_ep2_gpu1_20260521T143813Z.log` |
| ChFinAnn train seed42 HF-4bin LoRA ep2 `--skip-eval` | 1 | queued | `logs/sarge_sft_ChFinAnn-Doc2EDAG_s42_ep2_gpu1_20260521T143813Z.log` |

When a running job finishes, first inspect log tail and output tree, then pull only JSON summaries/manifests/eval/diagnostics into `paper/exp/data/run_snapshots/`. Do not pull checkpoints, full prediction JSONL, raw outputs, or parsed candidates into Git.

---

## 7. Key Commands

Local validation:

```bash
PYTHONDONTWRITEBYTECODE=1 /home/tjk/miniconda3/envs/feg-dev-py310/bin/python -B -m pytest tests/ -v
```

Server eval for completed inference:

```bash
cd /data/TJK/DEE/SARGE
/data/TJK/envs/sarge_vllm_full/bin/python -B scripts/eval_three_tracks.py \
  --run-root runs/<run_name>/<inner_run_name> \
  --dataset <DuEE-Fin-dev500|ChFinAnn-Doc2EDAG> \
  --split test
```

Rebuild local experiment summary:

```bash
PYTHONDONTWRITEBYTECODE=1 /home/tjk/miniconda3/envs/feg-dev-py310/bin/python -B paper/exp/scripts/build_seed13_summary.py
```

Build ACL-family draft assets:

```bash
cd /home/tjk/myProjects/masterProjects/DEE/SARGE/paper/emnlp_aacl_draft
./build.sh
```

---

## 8. Next Work

1. Refresh DuEE-Fin seed17/42 test assets after both active inference jobs finish and eval JSON exists.
2. After ChFinAnn seed17/42 training finishes, schedule HF-4bin test inference and three-track eval with new run names.
3. Update `paper/exp/data/asset_registry.json`, regenerate `paper/exp/seed13_summary.md`, then rebuild `paper/emnlp_aacl_draft/`.
4. Keep LRD fair-candidate policy explicit: no main LRD result from all k=4 parsed candidate pools.
