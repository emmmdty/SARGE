# DuEE-Fin-dev500

This directory contains public metadata for the DuEE-Fin split used by SARGE. Full data files are not committed.

Source: https://aistudio.baidu.com/datasetdetail/186939

Expected processed files after running `scripts/prepare_public_data.py`:

- `train.jsonl`
- `dev.jsonl`
- `test.jsonl`
- `blind_test_unlabeled.jsonl` if the optional blind file is downloaded
- `schema.json`
- `split_manifest.json`

Split policy: the official labeled dev file is used as the paper test split. The official labeled train file is deterministically split into train plus a 500-document development split using seed `42` and event-signature stratification.
