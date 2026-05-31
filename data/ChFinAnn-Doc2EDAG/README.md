# ChFinAnn-Doc2EDAG

This directory contains public metadata for the ChFinAnn split used by SARGE. Full data files are not committed.

Source: https://github.com/shun-zheng/Doc2EDAG

Expected processed files after running `scripts/prepare_public_data.py`:

- `train.jsonl`
- `dev.jsonl`
- `test.jsonl`
- `schema.json`
- `schema_validation_report.json`
- `split_manifest.json`

Split policy: preserve the upstream train/dev/test split.
