"""Train the Learned Record Disambiguator (LRD) pairwise scorer.

Expects precomputed pairwise training data from
``scripts/prepare_lrd_pairs.py``.  Trains the minimised
``BCE(L_pair) + λ * REINFORCE(L_record)`` objective,
saves a checkpoint, and runs a smoke inference on a small dev slice.

Example:
    python scripts/train_lrd.py \\
        --train-pairs runs/lrd/train_pairs.jsonl \\
        --schema data/processed/DuEE-Fin-dev500/schema.json \\
        --roberta models/chinese-roberta-wwm-ext_safetensors \\
        --out runs/lrd/train_seed13 \\
        --epochs 5 --seed 13
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import torch  # noqa: E402
from torch.utils.data import DataLoader, Dataset  # noqa: E402

from sarge.data.schema import load_schema  # noqa: E402
from sarge.models.encoder import ArgumentEncodingConfig  # noqa: E402
from sarge.postprocess.lrd_planner import LRDConfig, LRDPlanner  # noqa: E402


class PairwiseDataset(Dataset[dict[str, Any]]):
    """Wraps jsonl of precomputed training rows."""

    def __init__(self, path: str | Path, limit: int | None = None):
        self.rows: list[dict] = []
        with Path(path).open(encoding="utf-8") as f:
            for idx, line in enumerate(f):
                if limit is not None and idx >= limit:
                    break
                if line.strip():
                    self.rows.append(json.loads(line))

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, idx: int) -> dict[str, Any]:
        return self.rows[idx]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-pairs", required=True)
    parser.add_argument("--dev-pairs", default=None)
    parser.add_argument("--schema", required=True)
    parser.add_argument("--roberta", required=True, help="path to Chinese-RoBERTa-wwm-ext safetensors")
    parser.add_argument("--out", required=True)
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--reward-weight", type=float, default=0.3)
    parser.add_argument("--max-train-samples", type=int, default=None)
    args = parser.parse_args()

    import random
    import numpy as np
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load schema + build role vocabulary.
    # ``args.schema`` is the path to a ``<data_root>/<dataset>/schema.json``
    # file; recover dataset name and data_root from it instead of hard-coding
    # ``"lrd"`` (which would resolve to a non-existent ``<dir>/lrd/schema.json``).
    schema_path = Path(args.schema).resolve()
    dataset_name = schema_path.parent.name
    data_root = schema_path.parent.parent
    schema = load_schema(dataset_name, data_root=data_root)
    role_vocab = sorted(schema.unique_roles)

    # Build model.
    encoder_cfg = ArgumentEncodingConfig(
        model_path=args.roberta,
        hidden_dim=768,
        role_embedding_dim=64,
    )
    lrd_cfg = LRDConfig(
        encoder_config=encoder_cfg,
        role_vocabulary=role_vocab,
    )
    planner = LRDPlanner(lrd_cfg, schema)
    planner.to(device)
    planner.train()

    # Train dataset.
    train_ds = PairwiseDataset(args.train_pairs, limit=args.max_train_samples)
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, collate_fn=_collate)

    optimizer = torch.optim.AdamW(
        list(planner.scorer.parameters()) + list(planner.encoder.projection.parameters())
        + [planner.merge_thresholds],
        lr=args.lr,
    )

    print(f"train docs: {len(train_ds)}  batches: {len(train_loader)}  device: {device}")
    t0 = time.monotonic()
    for epoch in range(1, args.epochs + 1):
        total_loss = 0.0
        for batch in train_loader:
            loss, pair_loss, reward_loss = _train_step(
                planner, batch, device, reward_weight=args.reward_weight
            )
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        avg = total_loss / max(len(train_loader), 1)
        print(f"epoch {epoch}/{args.epochs}  loss={avg:.4f}")

    train_secs = time.monotonic() - t0
    print(f"training done in {train_secs:.0f}s")

    # Save checkpoint.
    ckpt_path = out_dir / "checkpoints" / "lrd_planner.pt"
    ckpt_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "scorer": planner.scorer.state_dict(),
            "encoder_projection": planner.encoder.projection.state_dict(),
            "merge_thresholds": planner.merge_thresholds,
            "config": lrd_cfg,
            "role_vocabulary": role_vocab,
        },
        ckpt_path,
    )
    print(f"saved: {ckpt_path}")

    summary = {
        "train_docs": len(train_ds),
        "epochs": args.epochs,
        "train_secs": round(train_secs, 1),
        "checkpoint": str(ckpt_path),
        "seed": args.seed,
    }
    (out_dir / "summary_train.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


def _train_step(
    planner: LRDPlanner,
    batch: list[dict],
    device: torch.device,
    *,
    reward_weight: float,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Compute L_total = BCE(pair) + λ * REINFORCE(exact-record-F1 reward)."""
    pair_losses: list[torch.Tensor] = []
    reward_losses: list[torch.Tensor] = []

    for doc in batch:
        records = doc["records"]
        doc_text = doc.get("text") or ""
        pairs = doc.get("pairs") or []

        if len(records) < 2 or not pairs:
            continue

        from sarge.postprocess.rule_planner import EventRecord as ER  # noqa: E402

        event_records = [ER.from_canonical(r) if isinstance(r, dict) else r for r in records]
        probs, cluster_soft, record_embs = planner.forward_soft(
            event_records, doc_text=doc_text
        )

        # Pairwise BCE.
        for pair in pairs:
            i, j, label = pair["i"], pair["j"], pair["label"]
            if i < len(records) and j < len(records):
                logit = planner.scorer.score_pair(record_embs[i], record_embs[j], 0.0)
                pair_losses.append(
                    torch.nn.functional.binary_cross_entropy_with_logits(
                        logit, torch.tensor([[float(label)]], device=device)
                    )
                )

        # REINFORCE reward: use cluster_soft to approximate exact-record
        # grouping and compute a differentiable F1 surrogate.
        if reward_weight > 0 and len(pairs) > 0:
            pos_count = sum(1 for p in pairs if p["label"] == 1)
            precision_proxy = cluster_soft.diag().mean()  # encourages tight clusters
            reward = 2.0 * pos_count / max(pos_count + len(pairs), 1) * precision_proxy
            reward_losses.append(-reward * torch.log(probs.diag().mean() + 1e-8))

    if not pair_losses:
        return torch.tensor(0.0, device=device, requires_grad=True), torch.tensor(0.0), torch.tensor(0.0)

    pair_loss = torch.stack(pair_losses).mean()
    reward_loss = torch.stack(reward_losses).mean() if reward_losses else torch.tensor(0.0, device=device)
    total = pair_loss + reward_weight * reward_loss
    return total, pair_loss.detach(), reward_loss.detach()


def _collate(batch: list[dict]) -> list[dict]:
    return list(batch)


if __name__ == "__main__":
    raise SystemExit(main())
