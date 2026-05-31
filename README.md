# SARGE

Schema-Aware Role-Grounded Extractor for Chinese financial document-level event extraction.

SARGE converts a financial document into schema-constrained event records. The public repository contains the code path needed to prepare the public datasets, train the Qwen3-4B LoRA extractor, run inference, and report the paper F1 metric.

## Repository Layout

```text
SARGE/
├── data/                         # metadata only; raw and processed samples are not committed
│   ├── ChFinAnn-Doc2EDAG/
│   └── DuEE-Fin-dev500/
├── evaluator/                    # role-level micro P/R/F1 evaluator
├── scripts/
│   ├── prepare_public_data.py    # build processed splits from downloaded raw datasets
│   ├── train_sft.py
│   ├── infer_checkpoint.py
│   ├── infer_checkpoint_vllm.py
│   └── merge_lora_to_bf16.py
└── src/sarge/                    # extraction package
```

Large assets are intentionally excluded: downloaded raw datasets, processed JSON/JSONL splits, model checkpoints, adapters, inference runs, and logs.

## Datasets

Download the source datasets from:

- ChFinAnn / Doc2EDAG: https://github.com/shun-zheng/Doc2EDAG
- DuEE-Fin: https://aistudio.baidu.com/datasetdetail/186939

Place the downloaded files under `data/raw/`:

```text
data/raw/
├── ChFinAnn/
│   ├── train.json
│   ├── dev.json
│   └── test.json
└── DuEE-Fin/
    ├── duee_fin_train.json
    ├── duee_fin_dev.json
    └── duee_fin_test.json        # optional blind split; labels are not used for paper F1
```

Build the processed splits:

```bash
python -B scripts/prepare_public_data.py --raw-root data/raw --out-root data
```

The split policy is recorded in the sanitized manifests under `data/*/split_manifest.json`.

- ChFinAnn preserves the upstream train/dev/test split.
- DuEE-Fin uses the official labeled dev file as the paper test split. The official labeled train file is deterministically split into train plus a 500-document development split using seed `42` and event-signature stratification.

The manifests include aggregate split counts and event distributions only. They do not include document IDs, row hashes, raw text, local paths, output hashes, or duplicate examples.

## Installation

Use Python 3.10 or newer.

```bash
uv venv
uv sync
```

For GPU training or inference, install the optional server stack:

```bash
uv sync --extra server
```

## Training

The default model path assumes a locally available Qwen3-4B-Instruct-2507 snapshot under `models/`.

```bash
CUDA_VISIBLE_DEVICES=0 PYTHONPATH=src \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 \
uv run python -B scripts/train_sft.py \
  --dataset DuEE-Fin-dev500 \
  --epochs 3 \
  --seed 13 \
  --gpu 0
```

Use `--dataset ChFinAnn-Doc2EDAG` for ChFinAnn.

## Inference

Run a LoRA checkpoint:

```bash
CUDA_VISIBLE_DEVICES=0 PYTHONPATH=src \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 \
uv run python -B scripts/infer_checkpoint.py \
  --dataset DuEE-Fin-dev500 \
  --split test \
  --ckpt runs/<run-name>/artifacts/model/adapter \
  --model models/Qwen/Qwen3-4B-Instruct-2507
```

The canonical prediction file is written under:

```text
runs/<run-id>/predictions/<dataset>/<split>.canonical.pred.jsonl
```

## Evaluation

The paper reports strict surface-form role-level micro precision, recall, and F1. The evaluator also reports `F1(S.)` and `F1(M.)` via `subset_metrics.single_event.f1` and `subset_metrics.multi_event.f1`.

```bash
PYTHONPATH=. uv run python -B -m evaluator role-f1 \
  --dataset DuEE-Fin-dev500 \
  --gold data/DuEE-Fin-dev500/test.jsonl \
  --pred runs/<run-id>/predictions/DuEE-Fin-dev500/test.canonical.pred.jsonl \
  --schema data/DuEE-Fin-dev500/schema.json \
  --out runs/<run-id>/eval/role_f1.json
```

For ChFinAnn:

```bash
PYTHONPATH=. uv run python -B -m evaluator role-f1 \
  --dataset ChFinAnn-Doc2EDAG \
  --gold data/ChFinAnn-Doc2EDAG/test.jsonl \
  --pred runs/<run-id>/predictions/ChFinAnn-Doc2EDAG/test.canonical.pred.jsonl \
  --schema data/ChFinAnn-Doc2EDAG/schema.json \
  --out runs/<run-id>/eval/role_f1.json
```

The evaluator does not perform semantic matching, embedding matching, alias expansion, or label repair.

## License

MIT
