# TensorDetect Workflow Guide

This folder now has two primary scan workflows:

- `tensordetect_workflow_large_model_hub_scan.py`
- `tensordetect_workflow_300_model_batch_scan.py`

## 1) Hub/Ephemeral Workflow (discover + download + scan + cleanup)

File: `tensordetect_workflow_large_model_hub_scan.py`

Use this when you want to scan models directly from Hugging Face/Kaggle without keeping full model archives on disk.

What it does:
- Discovers candidate models from Hugging Face (and optionally Kaggle)
- Filters by size (`--min-gb`, `--max-gb`)
- Downloads each model to a temporary directory
- Scans with TensorDetect
- Deletes temp artifacts after each model
- Writes CSV + optional selected/failures JSON

Typical command:

```bash
TensorAbuse/.venv39/bin/python TensorAbuse/TensorDetect/tensordetect_workflow_large_model_hub_scan.py \
  --target 30 \
  --include-kaggle \
  --output-csv TensorAbuse/TensorDetect/results/tensordetect_findings_large_popular_30.csv
```

Useful options:
- `--target`
- `--min-gb`, `--max-gb`
- `--include-kaggle`
- `--exclude-repos-csv` (exclude models already in a prior CSV using `model_repo_id`)
- `--output-csv`
- `--output-selected-json`
- `--output-failures-json`

## 2) Local Batch Workflow (scan files already on disk)

File: `tensordetect_workflow_300_model_batch_scan.py`

Use this when models are already downloaded in a local folder and you want a deterministic folder scan.

What it does:
- Scans all compatible models in `--models-dir`
- Uses TensorDetect scanner (`H5Scan` / `SavedModelScan`)
- Exports a single CSV findings file
- Records scan/load errors as `severity=error` rows

Typical command:

```bash
TensorAbuse/.venv39/bin/python TensorAbuse/TensorDetect/tensordetect_workflow_300_model_batch_scan.py \
  --models-dir TensorAbuse/TensorDetect/demo_models \
  --output TensorAbuse/TensorDetect/results/tensordetect_findings.csv
```

## Current Core Results Retained

- `TensorAbuse/TensorDetect/results/tensordetect_findings_final_300.csv`
- `TensorAbuse/TensorDetect/results/tensordetect_findings_final_300.xlsx`
- `TensorAbuse/TensorDetect/results/tensordetect_findings_large_popular_30.csv`

## Notes

- Preferred Python env: `TensorAbuse/.venv39/bin/python`
- Kaggle auth uses `KAGGLE_TOKEN` env var when enabled.
- `results/` is the canonical output directory.
