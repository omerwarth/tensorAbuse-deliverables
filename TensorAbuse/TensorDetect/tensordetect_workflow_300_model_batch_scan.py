#!/usr/bin/env python3
import argparse
import csv
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from TensorDetect.model import Model, ModelType
from TensorDetect.scan import H5Scan, SavedModelScan


MODEL_SUFFIXES = {".h5", ".zip", ".pb"}


def find_models(models_dir: Path) -> list[Path]:
    candidates = []
    for child in sorted(models_dir.iterdir()):
        if child.is_dir():
            if (child / "saved_model.pb").exists():
                candidates.append(child)
            continue
        if child.suffix.lower() in MODEL_SUFFIXES:
            candidates.append(child)
    return candidates


def parse_details(details: str) -> tuple[str, str, str]:
    op_name = ""
    node_name = ""
    indicator = ""

    op_match = re.search(r"'op': '([^']+)'", details)
    if op_match:
        op_name = op_match.group(1)

    node_match = re.search(r"'name': '([^']+)'", details)
    if node_match:
        node_name = node_match.group(1)

    indicator_match = re.search(r"\n(\[[^\n]+\]:\s*[^\n]+)", details)
    if indicator_match:
        indicator = indicator_match.group(1).strip()

    return op_name, node_name, indicator


def scan_model(model_path: Path) -> list[dict]:
    try:
        mod = Model(str(model_path))
        scanner = H5Scan(mod) if mod.model_type == ModelType.TF_H5 else SavedModelScan(mod)
        scanner.scan()
    except Exception as e:
        return [
            {
                "model_name": model_path.name,
                "model_path": str(model_path),
                "model_type": "",
                "issue_index": "",
                "severity": "error",
                "category": "scan error",
                "op_name": "",
                "node_name": "",
                "indicator": "",
                "details": str(e),
            }
        ]

    rows = []
    if not scanner.issues:
        rows.append(
            {
                "model_name": model_path.name,
                "model_path": str(model_path),
                "model_type": mod.model_type.value,
                "issue_index": "",
                "severity": "none",
                "category": "none",
                "op_name": "",
                "node_name": "",
                "indicator": "",
                "details": "No issues detected",
            }
        )
        return rows

    for idx, issue in enumerate(scanner.issues, start=1):
        op_name, node_name, indicator = parse_details(issue.details)
        rows.append(
            {
                "model_name": model_path.name,
                "model_path": str(model_path),
                "model_type": mod.model_type.value,
                "issue_index": idx,
                "severity": issue.severity.value,
                "category": issue.category.value,
                "op_name": op_name,
                "node_name": node_name,
                "indicator": indicator,
                "details": " ".join(issue.details.split()),
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run TensorDetect against every model in a folder and export CSV findings."
    )
    parser.add_argument(
        "--models-dir",
        default="TensorDetect/demo_models",
        help="Directory containing model folders/files.",
    )
    parser.add_argument(
        "--output",
        default="TensorDetect/results/tensordetect_findings.csv",
        help="CSV output file path.",
    )
    args = parser.parse_args()

    models_dir = Path(args.models_dir)
    if not models_dir.exists():
        raise FileNotFoundError(f"Models directory not found: {models_dir}")

    models = find_models(models_dir)
    if not models:
        raise RuntimeError(f"No models found in {models_dir}")

    rows = []
    for model_path in models:
        rows.extend(scan_model(model_path))

    output_path = Path(args.output)
    os.makedirs(output_path.parent, exist_ok=True)

    fieldnames = [
        "model_name",
        "model_path",
        "model_type",
        "issue_index",
        "severity",
        "category",
        "op_name",
        "node_name",
        "indicator",
        "details",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {output_path}")


if __name__ == "__main__":
    main()
