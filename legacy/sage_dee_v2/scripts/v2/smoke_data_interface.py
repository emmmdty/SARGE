from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from sage_dee.v2.contracts.canonical import CANONICAL_PREDICTION_FORMAT_VERSION  # noqa: E402
from sage_dee.v2.contracts.run import SAGE_V2_RUN_MANIFEST_VERSION  # noqa: E402
from sage_dee.v2.data_interface.dataset_loader import load_documents  # noqa: E402
from sage_dee.v2.data_interface.schema_registry import load_schema  # noqa: E402
from sage_dee.v2.pipeline.export_canonical import export_predictions  # noqa: E402

DATASETS = ("DuEE-Fin-dev500", "ChFinAnn", "DocFEE-dev1000")
SPLITS = ("train", "dev", "test")
DATA_ROOT = REPO_ROOT / "data"
OUTPUT_ROOT = Path("/tmp/sage_v2_smoke_predictions")


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {
        "manifest_version": SAGE_V2_RUN_MANIFEST_VERSION,
        "prediction_format": CANONICAL_PREDICTION_FORMAT_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "data_root": str(DATA_ROOT),
        "output_root": str(OUTPUT_ROOT),
        "datasets": [],
    }
    canonical_example: dict[str, object] | None = None

    print("SAGE-DEE v2 data interface smoke")
    print(f"output_root={OUTPUT_ROOT}")

    for dataset in DATASETS:
        dataset_root = DATA_ROOT / dataset
        if not dataset_root.exists():
            raise FileNotFoundError(f"Missing dataset directory: {dataset_root}")
        schema = load_schema(dataset, data_root=DATA_ROOT)
        dataset_manifest: dict[str, object] = {
            "dataset_id": dataset,
            "dataset_path": str(dataset_root),
            "exists": True,
            "schema_dataset": schema.schema_dataset,
            "event_type_count": len(schema.event_types),
            "unique_role_count": len(schema.unique_roles),
            "splits": {},
        }
        print(
            f"dataset={dataset} exists=True "
            f"schema_dataset={schema.schema_dataset} event_types={len(schema.event_types)}"
        )

        for split in SPLITS:
            mode = _mode_for_split(split)
            documents = load_documents(dataset, split, data_root=DATA_ROOT, mode=mode, limit=2)
            prediction_rows = [{"doc_id": document.doc_id, "events": []} for document in documents]
            output_path = OUTPUT_ROOT / dataset / f"{split}.canonical.pred.jsonl"
            export_predictions(prediction_rows, output_path)
            gold_visible = any(document.gold is not None for document in documents)
            dataset_manifest["splits"][split] = {
                "mode": mode,
                "documents_read": len(documents),
                "gold_visible": gold_visible,
                "canonical_prediction_path": str(output_path),
            }
            if canonical_example is None and prediction_rows:
                canonical_example = prediction_rows[0]
            print(
                f"  split={split} mode={mode} docs={len(documents)} "
                f"gold_visible={gold_visible} canonical={output_path}"
            )
        manifest["datasets"].append(dataset_manifest)

    manifest_path = OUTPUT_ROOT / "run_manifest.json"
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(f"run_manifest={manifest_path}")
    print(f"canonical_example={json.dumps(canonical_example, ensure_ascii=False)}")


def _mode_for_split(split: str) -> str:
    if split == "train":
        return "train"
    if split == "dev":
        return "eval_internal"
    return "predict"


if __name__ == "__main__":
    main()
