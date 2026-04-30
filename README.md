# Project Navigation Guide

This repository is organized into two main areas:

- `tensorAbuseWithDetectFramework/` (core framework + detection workflows)
- `attacks/` (standalone attack replications)

## Folder Map

### `tensorAbuseWithDetectFramework/`
Primary working area for TensorAbuse + TensorDetect.

- `TensorDetect/`
  - Detection engine and scan workflows
  - Existing retained results are under `TensorDetect/results/`
  - See `TensorDetect/README.md` for exact commands and options

### `attacks/`
Additional attack-focused content outside the main framework layout. NOTE: The docker-compoose

- `code_execution/`
  - Build/run scripts for code execution attack demo
- `shell_access/`
  - Build/run scripts for shell access attack demo
- `file_read/`
  - Containerized file-read attack lab (`docker-compose`, `Makefile`, per-container folders)

