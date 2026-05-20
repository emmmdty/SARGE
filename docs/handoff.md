# SARGE Handoff

> **Last updated:** 2026-05-20 UTC+8
> **Project:** CCKS 2026 main submission candidate
> **Current status:** W3 main evidence complete; Chinese paper draft v0 assets prepared from completed evidence.

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

Local and server were reconciled on `main` at the evidence-sync commit before the draft-v0 paper work:

```text
6281ae9 fix: sync sacd and lrd state
```

Use `git rev-parse HEAD` on both local and server to check the latest documentation commit after draft-v0 work. Source/script state for the current evidence base is committed in `6281ae9`, covering:

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

Chinese paper draft v0:

| Artifact | Path |
|---|---|
| Draft | `paper/draft_v0/draft.md` |
| Source manifest | `paper/draft_v0/source_manifest.json` |
| Rebuild script | `paper/draft_v0/build_assets.py` |
| Tables | `paper/draft_v0/tables/` |
| Figures | `paper/draft_v0/assets/` |

The draft uses only completed paper-ready runs listed below plus EPAL/SEELE table values from the local `dee-fin` baseline docs.

Main paper numbers must come from real non-mock runs with `model_performance_evidence: true`, non-mock backend, source commit, command, model path, decoding config, limit, and document count in `run_manifest.json`.

Current strongest paper-ready paper-style results:

| Dataset | Run | Backend / decoding | Paper F1 |
|---|---|---|---|
| ChFinAnn-Doc2EDAG full dev | `runs/sarge_infer_ChFinAnn-Doc2EDAG_dev_20260519T040525Z/` | vLLM 0.8.5, BF16 merged, k=1 greedy | legacy fixed-slot `0.8549` |
| DuEE-Fin-dev500 dev | `runs/sarge_infer_DuEE-Fin-dev500_dev_20260519T043458Z/` | HF Transformers 5.4.0, 4-bit NF4 + LoRA ep2, k=1 greedy | legacy fixed-slot `0.7666` |

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
| `runs/sarge_postlrd_DuEE-Fin-dev500_dev_seed13_safe_anchor_tau0.90_20260520T001837Z/` | `0.7679` | `0.7735` | W8 seed13 pass candidate |

Failure-shape audit on 2026-05-20 found an unsafe merge boundary: LRD collapsed same-event clusters without the deterministic anchor/role compatibility guard used by the rule planner. The clearest case is `被约谈`, where multiple companies sharing the same agency/time were merged into one multi-value record; rule F1 `0.7376` fell to LRD F1 `0.1942`. Local code now requires anchor-compatible merges in `src/sarge/postprocess/lrd_planner.py`, with a unit test for the `被约谈` anchor-conflict case.

Safe-anchor rerun on GPU 0 used `runs/sarge_infer_DuEE-Fin-dev500_dev_20260519T043458Z/intermediate/getm/parsed_candidates.dev.jsonl`, wrote `docs=500 events_in=677 events_out=675`, and passed both W8 seed13 gates: legacy multi-event F1 `0.7550` and exact-record F1 `0.4181`.

Conclusion: W4 prototype executed, the original LRD run failed, and the safe-anchor repair is a W8 seed13 pass candidate. Do not start W9 test set or W11 seed 17/19 without a separate phase command.

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

1. When revising the Chinese draft, regenerate tables and figures with `/home/tjk/.codex/venvs/codex-tools/bin/python paper/draft_v0/build_assets.py`.
2. Keep `paper/draft_v0/source_manifest.json` aligned with any newly accepted paper evidence.
3. If new experiment numbers are promoted to paper evidence, update `docs/exp_result.md`, regenerate `paper/draft_v0/`, and re-sync local/server additively.
4. Continue to keep server `backup/` and `logs/` as untracked runtime evidence.
