"""Learned Record Disambiguator — replace rule-based dedup/merge/split.

This module wires the :class:`~sarge.models.encoder.ArgumentEncoder` and
:class:`~sarge.models.disambiguator.PairwiseScorer` into a drop-in
replacement for the conservative-* rule functions in
:mod:`sarge.postprocess.rule_planner`.

Compatibility contract
----------------------
``disambiguate_records(records, *, doc_text, schema)`` accepts the same
``EventRecord`` list that ``apply_planner`` receives (already deduplicated
and empty-target-dropped) and returns a list of ``EventRecord`` instances
that all pass ``_validate_record``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

from sarge.data.schema import DatasetSchema
from sarge.models.disambiguator import PairwiseScorer, jaccard_overlap_matrix
from sarge.models.encoder import ArgumentEncoder, ArgumentEncodingConfig
from sarge.postprocess.rule_planner import (
    EventRecord,
    PlannerDecision,
    PlannerDiagnostics,
    _validate_record,
)


@dataclass
class LRDConfig:
    """Hyperparameters for the Learned Record Disambiguator."""

    encoder_config: ArgumentEncodingConfig
    scorer_hidden_dim: int = 256
    scorer_dropout: float = 0.1
    linkage_method: str = "average"  # scipy linkage method
    base_merge_threshold: float = 0.65  # default τ when no per-type τ is learned
    gumbel_temperature: float = 1.0  # for training relaxations
    role_vocabulary: list[str] = field(default_factory=list)


class LRDPlanner:
    """Learned Record Disambiguator pluggable into the SARGE pipeline.

    Replaces the three rule functions ``conservative_split``,
    ``conservative_merge``, and ``near_dedup_conservative`` in
    :func:`sarge.postprocess.rule_planner.apply_planner` when
    ``mode == "lrd"``.

    At inference time the planner runs a hard agglomerative clustering
    step.  At training time (when ``.train()`` is set) the
    Gumbel-softmax relaxation is active and a REINFORCE-style
    exact-record reward can be back-propagated.
    """

    def __init__(self, config: LRDConfig, schema: DatasetSchema):
        self.config = config
        self.schema = schema
        self.encoder = ArgumentEncoder(config.encoder_config, config.role_vocabulary)
        self.scorer = PairwiseScorer(
            input_dim=config.encoder_config.hidden_dim + len(config.role_vocabulary),
            hidden_dim=config.scorer_hidden_dim,
            dropout=config.scorer_dropout,
        )
        # Per-event-type learned merge threshold.
        n_types = len(schema.event_types)
        self.merge_thresholds = nn.Parameter(
            torch.full((n_types,), config.base_merge_threshold)
        )
        self._event_type_index = {et: i for i, et in enumerate(sorted(schema.event_types))}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def disambiguate(
        self,
        records: list[EventRecord],
        *,
        doc_text: str,
    ) -> tuple[list[EventRecord], PlannerDiagnostics]:
        """Run learned record disambiguation (inference mode).

        Returns reconstituted records and diagnostic metadata.
        """
        diagnostics = PlannerDiagnostics(mode="lrd", events_before=len(records))
        if len(records) <= 1:
            diagnostics.events_after = len(records)
            return list(records), diagnostics

        # 1. Encode arguments.
        record_embeddings, role_masks = self._encode_records(records, doc_text)

        # 2. Pairwise scoring.
        surface_overlap = jaccard_overlap_matrix(
            [rec.to_canonical() for rec in records]
        ).to(record_embeddings.device)

        with torch.no_grad():
            logits = self.scorer(record_embeddings, surface_overlap)
            probs = torch.sigmoid(logits)

        # 3. Hierarchical agglomerative clustering.
        distance = (1.0 - probs).cpu().numpy()
        np.fill_diagonal(distance, 0.0)
        condensed = squareform(distance, checks=False)

        if len(records) <= 2:
            # scipy linkage fails for n < 3 with some methods.
            clusters = self._greedy_cluster(records, probs)
        else:
            z = linkage(condensed, method=self.config.linkage_method)
            # Pick threshold: use the minimum per-event-type τ among
            # the records in the cluster.
            et_indices = [
                self._event_type_index.get(rec.event_type, 0)
                for rec in records
            ]
            with torch.no_grad():
                tau = float(self.merge_thresholds[et_indices].min().item())
            cluster_ids = fcluster(z, t=1.0 - tau, criterion="distance")
            clusters = self._cluster_from_labels(records, cluster_ids, diagnostics)

        merged = self._merge_clusters(records, clusters, diagnostics)
        for rec in merged:
            _validate_record(rec, self.schema)
        diagnostics.events_after = len(merged)
        return merged, diagnostics

    def forward_soft(
        self,
        records: list[EventRecord],
        *,
        doc_text: str,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Training forward pass with Gumbel-softmax relaxation.

        Returns:
            (probs, cluster_soft_assignments, record_embeddings)
        """
        record_embeddings, role_masks = self._encode_records(records, doc_text)
        surface_overlap = jaccard_overlap_matrix(
            [rec.to_canonical() for rec in records]
        ).to(record_embeddings.device)

        logits = self.scorer(record_embeddings, surface_overlap)
        probs = torch.sigmoid(logits)
        # Gumbel-softmax over the linkage step:
        # treat (1 - probs) as log-probabilities for a soft partition.
        cluster_soft = F.gumbel_softmax(
            (1.0 - probs).neg(), tau=self.config.gumbel_temperature, hard=False, dim=-1
        )
        return probs, cluster_soft, record_embeddings

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _encode_records(
        self, records: list[EventRecord], doc_text: str
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Encode all argument triples → pooled record embeddings."""
        all_arg_embs: list[torch.Tensor] = []
        record_embs: list[torch.Tensor] = []
        role_masks: list[torch.Tensor] = []

        # Determine device from the first parameter.
        device = next(self.encoder.parameters()).device

        full_tokenized = self.encoder.tokenizer(
            doc_text, return_tensors="pt", truncation=True,
            max_length=self.config.encoder_config.max_seq_len,
        )
        full_input_ids = full_tokenized["input_ids"].to(device)  # [1, L]
        full_attention_mask = full_tokenized["attention_mask"].to(device)

        for rec in records:
            rec_arg_embs: list[torch.Tensor] = []
            role_mask = torch.zeros(len(self.config.role_vocabulary), device=device)
            for role, values in rec.arguments.items():
                if role not in self.encoder.role_to_idx:
                    continue
                role_idx = self.encoder.role_to_idx[role]
                role_mask[role_idx] = 1.0
                for value in values:
                    text = str(value.get("text", "")).strip()
                    if not text:
                        continue
                    emb = self._encode_argument(
                        doc_text, text, role_idx, full_input_ids, full_attention_mask
                    )
                    if emb is not None:
                        rec_arg_embs.append(emb)
            if rec_arg_embs:
                stacked = torch.stack(rec_arg_embs)
                rec_emb = self.encoder.record_embedding(stacked, role_mask)
            else:
                rec_emb = torch.zeros(
                    self.config.encoder_config.hidden_dim + len(self.config.role_vocabulary),
                    device=device,
                )
            record_embs.append(rec_emb)
            role_masks.append(role_mask)

        return torch.stack(record_embs), torch.stack(role_masks)

    def _encode_argument(
        self,
        doc_text: str,
        arg_text: str,
        role_idx: int,
        full_input_ids: torch.Tensor,
        full_attention_mask: torch.Tensor,
    ) -> torch.Tensor | None:
        """Encode a single argument value within its document context."""
        # Locate argument span in document.
        pos = doc_text.find(arg_text)
        if pos == -1:
            return None

        cw = self.config.encoder_config.context_window
        start = max(0, pos - cw)
        end = min(len(doc_text), pos + len(arg_text) + cw)
        window = doc_text[start:end]
        arg_start_in_window = pos - start
        arg_end_in_window = arg_start_in_window + len(arg_text)

        tokenized = self.encoder.tokenizer(
            window, return_tensors="pt", truncation=True,
            max_length=self.config.encoder_config.max_seq_len,
        )
        device = full_input_ids.device
        input_ids = tokenized["input_ids"].to(device)
        attention_mask = tokenized["attention_mask"].to(device)

        # Build span mask: mark tokens that fall inside the argument.
        char_to_token = _char_to_token_map(window, self.encoder.tokenizer, input_ids[0])
        span_mask = torch.zeros_like(input_ids, dtype=torch.float)
        for tok_idx, (c_start, c_end) in enumerate(char_to_token):
            if c_start >= arg_start_in_window and c_end <= arg_end_in_window:
                span_mask[0, tok_idx] = 1.0

        if span_mask.sum() == 0:
            span_mask[0, 0] = 1.0  # fall back to CLS

        role_idx_t = torch.tensor([role_idx], device=device)
        return self.encoder.encode(input_ids, attention_mask, span_mask, role_idx_t)

    def _greedy_cluster(
        self, records: list[EventRecord], probs: torch.Tensor
    ) -> list[list[int]]:
        """Simple greedy merging (fallback for small record sets)."""
        n = len(records)
        assigned: set[int] = set()
        clusters: list[list[int]] = []
        for i in range(n):
            if i in assigned:
                continue
            cluster = [i]
            for j in range(i + 1, n):
                if j in assigned:
                    continue
                if probs[i, j] > 0.5:
                    cluster.append(j)
                    assigned.add(j)
            assigned.add(i)
            clusters.append(cluster)
        return clusters

    @staticmethod
    def _cluster_from_labels(
        records: list[EventRecord],
        cluster_ids: np.ndarray,
        diagnostics: PlannerDiagnostics,
    ) -> list[list[int]]:
        """Convert flat cluster labels → list-of-lists, recording merge decisions."""
        clusters: dict[int, list[int]] = {}
        for i, cid in enumerate(cluster_ids):
            clusters.setdefault(int(cid), []).append(i)
        result = list(clusters.values())
        # Record decisions for any cluster with ≥ 2 records (a "merge").
        for cl in result:
            if len(cl) < 2:
                continue
            diagnostics.add_decision(
                PlannerDecision(
                    action="merge",
                    event_type=records[cl[0]].event_type,
                    before_count=len(cl),
                    after_count=1,
                    reason="lrd agglomerative merge",
                )
            )
        return result

    @staticmethod
    def _merge_clusters(
        records: list[EventRecord],
        clusters: list[list[int]],
        diagnostics: PlannerDiagnostics,
    ) -> list[EventRecord]:
        """Collapse each cluster into a single record (role-wise majority vote)."""
        merged: list[EventRecord] = []
        for cl in clusters:
            if len(cl) == 1:
                merged.append(records[cl[0]])
                continue
            # Merge: union-of-arguments, duplicates resolved by keeping
            # the first normalised occurrence (same logic as
            # rule_planner._merge_records).
            base = records[cl[0]]
            merged_args: dict[str, list[dict[str, str]]] = {
                role: [{"text": v["text"]} for v in values]
                for role, values in base.arguments.items()
            }
            seen_texts: dict[str, set[str]] = {
                role: {_norm(v["text"]) for v in values}
                for role, values in merged_args.items()
            }
            for idx in cl[1:]:
                rec = records[idx]
                for role, values in rec.arguments.items():
                    seen = seen_texts.setdefault(role, set())
                    target = merged_args.setdefault(role, [])
                    for v in values:
                        n = _norm(v["text"])
                        if n not in seen:
                            target.append({"text": v["text"]})
                            seen.add(n)

            merged.append(
                EventRecord(event_type=base.event_type, arguments=merged_args)
            )
        return merged


def _norm(text: str) -> str:
    return "".join(text.split())


def _char_to_token_map(text: str, tokenizer: Any, input_ids: torch.Tensor) -> list[tuple[int, int]]:
    """Map each token to its character span in the original text.

    Uses the fast tokenizer's ``token_to_chars`` when available, falling
    back to a character-level heuristic.
    """
    if hasattr(tokenizer, "token_to_chars") and callable(tokenizer.token_to_chars):
        encoding = tokenizer(text, return_offsets_mapping=True)
        offsets = encoding.get("offset_mapping") or []
        return [(o[0], o[1]) for o in offsets]
    # Slow fallback: approximate per character.
    spans: list[tuple[int, int]] = []
    decoded = tokenizer.decode(input_ids, skip_special_tokens=False)
    # Not perfectly aligned; use with caution on non-space languages.
    return [(0, len(text)) for _ in input_ids]
