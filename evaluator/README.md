# Evaluator

This package provides the paper F1 evaluator for SARGE.

## Metric

`role-f1` reports strict surface-form role-level micro precision, recall, and F1. Predictions and gold records are matched within the same document and event type. Each event type uses the schema role order, each role slot contributes at most one normalized value, and repeated values in one role are collapsed to the last normalized non-empty value.

The JSON report contains:

- `overall.precision`, `overall.recall`, `overall.f1`
- `per_event`
- `subset_metrics.single_event.f1` for `F1(S.)`
- `subset_metrics.multi_event.f1` for `F1(M.)`
- `record_metrics.exact_record` for order-insensitive exact-record P/R/F1
- `record_metrics.delta_record` for role F1 minus ExactRec
- diagnostics for parse failures, schema validation, fixed role-slot counts,
  and exact-record counts

ExactRec compares the multiset of schema-ordered fixed-slot records within each
document and event type. Normalization is intentionally minimal: Unicode NFKC,
leading/trailing whitespace removal, repeated whitespace collapse, and
empty-value removal. The evaluator does not use semantic matching, embedding
matching, alias expansion, date conversion, amount conversion, or gold-based
repair.

## CLI

```bash
python -m evaluator --help

python -m evaluator inspect-gold \
  --dataset DuEE-Fin-dev500 \
  --gold data/DuEE-Fin-dev500/test.jsonl \
  --schema data/DuEE-Fin-dev500/schema.json

python -m evaluator role-f1 \
  --dataset DuEE-Fin-dev500 \
  --gold data/DuEE-Fin-dev500/test.jsonl \
  --pred predictions.jsonl \
  --schema data/DuEE-Fin-dev500/schema.json \
  --out report.json
```

If `--out` is omitted, the report is printed to stdout.
