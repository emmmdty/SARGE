# SARGE Handoff

> **Last updated:** 2026-05-19 UTC+8  
> **Project:** CCKS 2026 main submission candidate  
> **Current status:** W3 main evidence complete; W4/LRD prototype executed but hard gate not passed.

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
| Runs | local small pulled artifacts only | `/data/TJK/DEE/SARGE/runs/` |

Use offline model loading:

```bash
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_DATASETS_OFFLINE=1
export TORCHDYNAMO_DISABLE=1
export TORCH_COMPILE_DISABLE=1
```

GPU jobs run only on `gpu-4090`. Check `nvidia-smi` first, prefer an idle GPU, set `CUDA_VISIBLE_DEVICES`, and never kill non-`TJK` processes.

---

## 2. Repository State

Local and server are both on `main` at:

```text
876cc6fff566d20c72c7cc1000f1b15a1814d88c docs: set default server python environment
```

As of this handoff, local and server have matching source/script worktree changes for:

- `src/sarge/data/schema.py`
- `src/sarge/generation/schema_decoding.py`
- `src/sarge/models/vllm_backend.py`
- `src/sarge/pipeline/manifest.py`
- `src/sarge/postprocess/lrd_planner.py`
- `scripts/infer_checkpoint_vllm.py`
- `scripts/preencode_lrd.py`
- `scripts/prepare_lrd_pairs.py`
- `scripts/postprocess_lrd_eval.py`
- related tests and docs

Server also has untracked `backup/` and `logs/`; keep them as runtime evidence and do not delete during additive sync.

---

## 3. Paper-Ready Evidence

Authoritative result table: `docs/exp_result.md`.

Main paper numbers must come from real non-mock runs with `model_performance_evidence: true`, non-mock backend, source commit, command, model path, decoding config, limit, and document count in `run_manifest.json`.

Current strongest paper-ready results:

| Dataset | Run | Backend / decoding | Main F1 |
|---|---|---|---|
| ChFinAnn-Doc2EDAG full dev | `runs/sarge_infer_ChFinAnn-Doc2EDAG_dev_20260519T040525Z/` | vLLM BF16 merged, k=1 greedy | legacy `0.8549`, unified `0.8705` |
| DuEE-Fin-dev500 dev | `runs/sarge_infer_DuEE-Fin-dev500_dev_20260519T043458Z/` | HF 4-bit NF4 + LoRA ep2, k=1 greedy | legacy `0.7666`, unified `0.7723` |

Do not use `MockGetmBackend` outputs, smoke runs, or LRD diagnostic runs in the main paper table.

---

## 4. Current Findings

### Decoding / Runtime

- Greedy k=1 is the default production path.
- vLLM BF16 is strong on ChFinAnn but underperforms HF 4-bit NF4 on DuEE-Fin.
- DuEE-Fin vLLM sampling did not improve overall F1:
  - T=0.3: legacy `0.7386`, unified `0.7525`
  - T=0.5: legacy `0.7265`, unified `0.7381`
  - T=0.7: legacy `0.7228`, unified `0.7332`
- SACD is now wired as an optional vLLM feature through `scripts/infer_checkpoint_vllm.py --sacd`; treat it as diagnostic until a full run validates performance.

### LRD Prototype

LRD artifacts exist on server:

- Train candidates: `runs/sarge_infer_DuEE-Fin-dev500_train_20260519T105958Z/`
- Pair file/cache: `runs/lrd/dueefin_train_pairs.jsonl`, `runs/lrd/dueefin_preencoded.pt`
- Checkpoints:
  - `runs/lrd/dueefin_train_seed13/checkpoints/lrd_planner.pt`
  - `runs/lrd/dueefin_train_seed13_ep15_lr5e5/checkpoints/lrd_planner.pt`

Observed DuEE-Fin post-LRD diagnostics are below rule-planner baselines. Best checked tau run:

| Run | legacy F1 | unified F1 | Note |
|---|---:|---:|---|
| `runs/sarge_postlrd_DuEE-Fin-dev500_dev_seed13_tau0.90/` | `0.6911` | `0.6921` | diagnostic only |

Conclusion: W4 prototype executed, but LRD hard gate is not passed. Do not claim LRD gain yet.

---

## 5. Key Commands

Local validation:

```bash
PYTHONDONTWRITEBYTECODE=1 /home/tjk/miniconda3/envs/feg-dev-py310/bin/python -B -m pytest tests/ -v
```

vLLM inference template:

```bash
cd /data/TJK/DEE/SARGE
CUDA_VISIBLE_DEVICES=<free_gpu> PYTHONPATH=src \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 \
TORCHDYNAMO_DISABLE=1 TORCH_COMPILE_DISABLE=1 \
/data/TJK/envs/sarge_vllm_full/bin/python -u scripts/infer_checkpoint_vllm.py \
  --merged runs/merged_models/qwen3_4b_chfinann_ep2_s13 \
  --dataset ChFinAnn-Doc2EDAG \
  --split dev \
  --k 1 \
  --source-commit <committed_local_git_hash>
```

Optional SACD diagnostic variant:

```bash
... scripts/infer_checkpoint_vllm.py ... --sacd --sacd-backend xgrammar
```

Evaluation:

```bash
/data/TJK/envs/sarge_vllm_full/bin/python -B scripts/eval_three_tracks.py \
  --run-root runs/<run_name> \
  --dataset <DuEE-Fin-dev500|ChFinAnn-Doc2EDAG> \
  --split dev
```

LRD postprocess diagnostic:

```bash
/data/TJK/envs/sarge_vllm_full/bin/python -B scripts/postprocess_lrd_eval.py \
  --candidates runs/<infer_run>/intermediate/getm/parsed_candidates.dev.jsonl \
  --dataset DuEE-Fin-dev500 \
  --split dev \
  --planner lrd \
  --lrd-ckpt runs/lrd/dueefin_train_seed13/checkpoints/lrd_planner.pt \
  --roberta models/chinese-roberta-wwm-ext_safetensors \
  --tau-override 0.90 \
  --out runs/sarge_postlrd_DuEE-Fin-dev500_dev_seed13_tau0.90
```

---

## 6. Next Work

1. Commit and sync the current bugfix/docs state before using new numbers as paper evidence.
2. If pursuing SACD, run a small DuEE-Fin dev diagnostic first, then full dev only if parse/schema diagnostics improve.
3. For LRD, debug the objective/labeling failure shape before spending more GPU time; current pairwise BCE prototype over-merges or suppresses recall and does not satisfy C3.
4. Do not start multi-seed seed 17/19 until the W8 hard gate is passed.
