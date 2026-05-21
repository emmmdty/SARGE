# SARGE EMNLP/AACL Draft

This directory contains an English ACL-family manuscript draft for SARGE.

Local build metadata in this directory is not part of the anonymous review
source bundle. Submit `main.tex`, `references.bib`, `style/`, `tables/`, and
`figures/` after checking that local paths are excluded from the source package.

Paths and environments:

- Local project root: `/home/tjk/myProjects/masterProjects/DEE/SARGE`
- Server project root: `/data/TJK/DEE/SARGE`
- Local Python: `/home/tjk/miniconda3/envs/feg-dev-py310/bin/python`
- Server Python: `/data/TJK/envs/sarge_vllm_full/bin/python`
- Asset/build Python: `/home/tjk/.codex/venvs/codex-tools/bin/python`

Build:

```bash
cd /home/tjk/myProjects/masterProjects/DEE/SARGE/paper/emnlp_aacl_draft
./build.sh
```

The build script regenerates tables and vector figures from `paper/exp/data/asset_registry.json`, checked-in JSON snapshots, and baseline constants, then compiles `main.tex` with the official ACL style files stored in `style/`.

Important boundaries:

- The draft is anonymous by default (`review` mode).
- Completed numbers only come from checked-in snapshot JSON and `asset_registry.json`.
- Active experiments stay in status text/tables and are excluded from main results until eval JSON exists.
- `references.bib` is paired with `citation_audit.md`; DOI fields are included only when verified.
