#!/usr/bin/env python3
import argparse
import csv
import json
import os
import re
import shutil
import sys
import tarfile
import tempfile
import time
import zipfile
from collections import Counter
from pathlib import Path
from typing import Optional
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from TensorDetect.model import Model, ModelType
from TensorDetect.scan import H5Scan, SavedModelScan

HF_API = "https://huggingface.co/api/models"
HF_DL = "https://huggingface.co"
KAGGLE_API = "https://www.kaggle.com/api/v1/models/list"

TF_HINTS = (
    "tf",
    "tensorflow",
    "tf-keras",
    "tfhub",
    "saved_model",
    "savedmodel",
    "keras",
)


def http_json(url: str, headers: Optional[dict] = None, timeout: int = 45):
    req = Request(url, headers=headers or {})
    with urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", errors="ignore"))


def http_json_with_headers(url: str, headers: Optional[dict] = None, timeout: int = 45):
    req = Request(url, headers=headers or {})
    with urlopen(req, timeout=timeout) as r:
        body = json.loads(r.read().decode("utf-8", errors="ignore"))
        return body, r.headers


def download_file(url: str, dst: Path, headers: Optional[dict] = None, timeout: int = 120):
    req = Request(url, headers=headers or {})
    with urlopen(req, timeout=timeout) as r, dst.open("wb") as f:
        while True:
            chunk = r.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)


def head_content_length(url: str, headers: Optional[dict] = None, timeout: int = 45):
    req = Request(url, headers=headers or {}, method="HEAD")
    with urlopen(req, timeout=timeout) as r:
        raw = r.headers.get("Content-Length")
        return int(raw) if raw and raw.isdigit() else None


def hf_headers(token: Optional[str]):
    h = {"User-Agent": "TensorDetect-ephemeral-scan/1.0"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def parse_size_from_siblings(siblings):
    sizes = []
    for s in siblings or []:
        size = s.get("size")
        if isinstance(size, int) and size > 0:
            sizes.append(size)
    return max(sizes) if sizes else None


def preferred_hf_artifact(siblings):
    names = [s.get("rfilename", "") for s in siblings or []]
    for n in names:
        if n.endswith("saved_model.pb"):
            return n
    h5 = [n for n in names if n.lower().endswith(".h5")]
    if h5:
        return sorted(h5, key=len)[0]
    zips = [n for n in names if n.lower().endswith(".zip")]
    if zips:
        return sorted(zips, key=len)[0]
    tars = [n for n in names if n.lower().endswith((".tar.gz", ".tgz"))]
    if tars:
        return sorted(tars, key=len)[0]
    return None


def parse_next_link(link_header: str):
    if not link_header:
        return None
    parts = [p.strip() for p in link_header.split(",")]
    for p in parts:
        if 'rel="next"' in p and p.startswith("<") and ">;" in p:
            return p[1 : p.index(">;")]
    return None


def collect_hf_candidates(
    limit_pool: int,
    min_bytes: Optional[int],
    max_bytes: Optional[int],
    token: Optional[str],
    pages_per_query: int,
):
    headers = hf_headers(token)
    base_queries = [
        {"library": "tensorflow"},
        {"library": "tf-keras"},
        {"library": "tfhub"},
    ]
    search_terms = [
        "saved_model.pb",
        "tf_model.h5",
        "tensorflow keras",
        "savedmodel",
        "keras model.h5",
        "tf saved model",
        "vision tf_model.h5",
        "nlp tf_model.h5",
        "unet h5",
        "bert tf_model.h5",
        "clip tf_model.h5",
        "whisper tf_model.h5",
    ]
    sorts = ["downloads", "likes", "lastModified"]

    queries = []
    for q in base_queries:
        for s in sorts:
            q2 = dict(q)
            q2.update({"limit": 100, "sort": s, "direction": -1, "full": "true"})
            queries.append(q2)
    for term in search_terms:
        for s in sorts:
            queries.append({"search": term, "limit": 100, "sort": s, "direction": -1, "full": "true"})

    seen = set()
    out = []
    for q in queries:
        next_url = HF_API + "?" + urlencode(q)
        pages = 0
        while next_url and pages < pages_per_query and len(out) < limit_pool:
            try:
                models, resp_headers = http_json_with_headers(next_url, headers=headers)
            except Exception:
                break

            for m in models:
                mid = m.get("id")
                if not mid or mid in seen:
                    continue
                siblings = m.get("siblings") or []
                artifact = preferred_hf_artifact(siblings)
                if not artifact:
                    continue

                tags = " ".join(m.get("tags", [])).lower()
                # Keep models if tags suggest TF OR if artifacts themselves are TensorFlow-compatible.
                if not any(t in tags for t in TF_HINTS):
                    if not artifact.lower().endswith((".h5", ".zip", ".tar.gz", ".tgz", "saved_model.pb")):
                        continue

                max_sibling = parse_size_from_siblings(siblings)
                if min_bytes and max_sibling and max_sibling < min_bytes:
                    continue
                if max_bytes and max_sibling and max_sibling > max_bytes:
                    continue
                out.append(
                    {
                        "hub": "huggingface",
                        "repo": mid,
                        "artifact": artifact,
                        "downloads": m.get("downloads") or 0,
                        "likes": m.get("likes") or 0,
                        "size_hint": max_sibling,
                    }
                )
                seen.add(mid)
                if len(out) >= limit_pool:
                    break

            pages += 1
            next_url = parse_next_link(resp_headers.get("Link", ""))
    return out


def collect_kaggle_candidates(limit_pool: int, min_bytes: Optional[int], max_bytes: Optional[int], kaggle_token: Optional[str]):
    if not kaggle_token:
        return []
    headers = {
        "User-Agent": "TensorDetect-ephemeral-scan/1.0",
        "Authorization": f"Bearer {kaggle_token}",
    }
    out = []
    next_token = None
    seen = set()

    while len(out) < limit_pool:
        qs = {"page_size": 100}
        if next_token:
            qs["nextPageToken"] = next_token
        url = KAGGLE_API + "?" + urlencode(qs)
        try:
            data = http_json(url, headers=headers)
        except Exception:
            break

        if isinstance(data, dict):
            items = data.get("models") or data.get("items") or []
            next_token = data.get("nextPageToken")
        else:
            items = data
            next_token = None

        if not items:
            break

        for item in items:
            inst = item.get("instances", [{}])
            best = inst[0] if inst else {}
            dl = best.get("downloadUrl") or item.get("downloadUrl")
            if not dl:
                continue
            rid = item.get("ref") or item.get("name") or dl
            if rid in seen:
                continue
            framework = (item.get("framework") or "").lower()
            name_blob = " ".join(
                [
                    str(item.get("name") or ""),
                    str(item.get("description") or ""),
                    str(item.get("modelType") or ""),
                    str(best.get("name") or ""),
                    str(dl or ""),
                ]
            ).lower()
            if ("tensor" not in framework and "keras" not in framework) and (
                "tf" not in name_blob and "tensorflow" not in name_blob and "keras" not in name_blob and ".h5" not in name_blob
            ):
                continue
            size = best.get("sizeBytes") or item.get("sizeBytes")
            if min_bytes and size and size < min_bytes:
                continue
            if max_bytes and size and size > max_bytes:
                continue
            out.append(
                {
                    "hub": "kaggle",
                    "repo": rid,
                    "artifact": dl,
                    "downloads": item.get("downloadCount") or 0,
                    "likes": item.get("voteCount") or 0,
                    "size_hint": size,
                }
            )
            seen.add(rid)
            if len(out) >= limit_pool:
                break
        if not next_token:
            break

    return out


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


def scan_single_model(path: Path, model_name: str, model_path: str, hub: str):
    rows = []
    try:
        mod = Model(str(path))
        scanner = H5Scan(mod) if mod.model_type == ModelType.TF_H5 else SavedModelScan(mod)
        scanner.scan()
        if not scanner.issues:
            rows.append({
                "model_name": model_name,
                "model_path": model_path,
                "model_type": mod.model_type.value,
                "issue_index": "",
                "severity": "none",
                "category": "none",
                "op_name": "",
                "node_name": "",
                "indicator": "",
                "details": "No issues detected",
                "hub": hub,
            })
        else:
            for idx, issue in enumerate(scanner.issues, start=1):
                op_name, node_name, indicator = parse_details(issue.details)
                rows.append({
                    "model_name": model_name,
                    "model_path": model_path,
                    "model_type": mod.model_type.value,
                    "issue_index": idx,
                    "severity": issue.severity.value,
                    "category": issue.category.value,
                    "op_name": op_name,
                    "node_name": node_name,
                    "indicator": indicator,
                    "details": " ".join(issue.details.split()),
                    "hub": hub,
                })
    except Exception as e:
        rows.append({
            "model_name": model_name,
            "model_path": model_path,
            "model_type": "",
            "issue_index": "",
            "severity": "error",
            "category": "scan error",
            "op_name": "",
            "node_name": "",
            "indicator": "",
            "details": str(e),
            "hub": hub,
        })
    return rows


def find_saved_model_root(extract_root: Path):
    if (extract_root / "saved_model.pb").exists():
        return extract_root
    for p in extract_root.rglob("saved_model.pb"):
        return p.parent
    return None


def unpack_if_needed(model_file: Path, tmpdir: Path):
    lower = model_file.name.lower()
    if lower.endswith(".h5"):
        return model_file
    if lower.endswith("saved_model.pb"):
        return model_file.parent
    if lower.endswith(".zip"):
        unpack_dir = tmpdir / "unzipped"
        unpack_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(model_file, "r") as zf:
            zf.extractall(unpack_dir)
        sm_root = find_saved_model_root(unpack_dir)
        return sm_root if sm_root else model_file
    if lower.endswith(".tar.gz") or lower.endswith(".tgz"):
        unpack_dir = tmpdir / "untarred"
        unpack_dir.mkdir(parents=True, exist_ok=True)
        with tarfile.open(model_file, "r:gz") as tf:
            tf.extractall(unpack_dir)
        sm_root = find_saved_model_root(unpack_dir)
        return sm_root if sm_root else model_file
    return model_file


def choose_final(candidates, target):
    candidates = sorted(candidates, key=lambda x: (x["downloads"], x["likes"]), reverse=True)
    return candidates[:target]


def load_excluded_repos(csv_path: str):
    if not csv_path:
        return set()
    p = Path(csv_path)
    if not p.exists():
        raise FileNotFoundError(f"Exclude CSV not found: {csv_path}")
    excluded = set()
    with p.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        if not r.fieldnames or "model_repo_id" not in r.fieldnames:
            raise RuntimeError("Exclude CSV must contain a model_repo_id column")
        for row in r:
            rid = (row.get("model_repo_id") or "").strip().lower()
            if rid:
                excluded.add(rid)
    return excluded


def run_scan(args):
    hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
    kaggle_token = os.environ.get("KAGGLE_TOKEN")

    min_bytes = args.min_gb * (1024**3) if args.min_gb else None
    max_bytes = args.max_gb * (1024**3) if args.max_gb else None

    hf_pool = max(args.hf_pool, args.target * 3, 80)
    kg_pool = max(args.kg_pool, args.target * 2, 40)
    excluded_repos = load_excluded_repos(args.exclude_repos_csv)
    if excluded_repos:
        print(f"Loaded excluded repos: {len(excluded_repos)}")

    merged = []
    attempts = 0
    max_attempts = max(args.max_fill_rounds, 1)
    while len(merged) < args.target and attempts < max_attempts:
        attempts += 1
        hf = collect_hf_candidates(hf_pool * attempts, min_bytes, max_bytes, hf_token, args.hf_pages_per_query)
        kg = collect_kaggle_candidates(kg_pool * attempts, min_bytes, max_bytes, kaggle_token) if args.include_kaggle else []
        dedup = {}
        for c in hf + kg:
            if excluded_repos and c["repo"].strip().lower() in excluded_repos:
                continue
            key = (c["hub"], c["repo"], c["artifact"])
            if key not in dedup:
                dedup[key] = c
        merged = choose_final(list(dedup.values()), args.target)
        print(f"Candidate fill round {attempts}: hf={len(hf)} kg={len(kg)} merged={len(merged)}")

    rows = []
    selected = []
    failures = []

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
        "hub",
    ]

    results_dir = Path(args.output_csv).resolve().parent
    results_dir.mkdir(parents=True, exist_ok=True)

    for idx, cand in enumerate(merged, start=1):
        model_name = cand["repo"].replace("/", "__")
        artifact = cand["artifact"]
        hub = cand["hub"]

        with tempfile.TemporaryDirectory(prefix="td_ephemeral_") as td:
            td_path = Path(td)
            try:
                if hub == "huggingface":
                    dl_url = f"{HF_DL}/{cand['repo']}/resolve/main/{quote(artifact)}"
                    headers = hf_headers(hf_token)
                else:
                    dl_url = artifact
                    headers = {"Authorization": f"Bearer {kaggle_token}", "User-Agent": "TensorDetect-ephemeral-scan/1.0"}

                local_name = Path(artifact).name
                if not local_name or "." not in local_name:
                    local_name = f"{model_name}.bin"
                local_file = td_path / local_name

                if min_bytes or max_bytes:
                    remote_size = head_content_length(dl_url, headers=headers)
                    if remote_size is not None:
                        if min_bytes and remote_size < min_bytes:
                            raise RuntimeError("skipped_by_size_lt_min")
                        if max_bytes and remote_size > max_bytes:
                            raise RuntimeError("skipped_by_size_gt_max")

                download_file(dl_url, local_file, headers=headers)

                scan_target = unpack_if_needed(local_file, td_path)
                rows.extend(scan_single_model(scan_target, model_name, str(scan_target), hub))
                selected.append({**cand, "resolved_url": dl_url})
            except Exception as e:
                failures.append({"candidate": cand, "error": str(e)})
                rows.append({
                    "model_name": model_name,
                    "model_path": artifact,
                    "model_type": "",
                    "issue_index": "",
                    "severity": "error",
                    "category": "scan error",
                    "op_name": "",
                    "node_name": "",
                    "indicator": "",
                    "details": str(e),
                    "hub": hub,
                })

        if idx % 5 == 0:
            print(f"Processed {idx}/{len(merged)}")

    with Path(args.output_csv).open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    if args.output_selected_json:
        with Path(args.output_selected_json).open("w", encoding="utf-8") as f:
            json.dump(selected, f, indent=2)

    if args.output_failures_json:
        with Path(args.output_failures_json).open("w", encoding="utf-8") as f:
            json.dump(failures, f, indent=2)

    sev = Counter(r["severity"] for r in rows)
    print("Completed.")
    print(f"selected={len(selected)} failures={len(failures)} rows={len(rows)} severity={dict(sev)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", type=int, required=True)
    ap.add_argument("--min-gb", type=float, default=0.0)
    ap.add_argument("--max-gb", type=float, default=0.0)
    ap.add_argument("--include-kaggle", action="store_true")
    ap.add_argument("--hf-pool", type=int, default=0, help="Override HF candidate pool depth before final ranking.")
    ap.add_argument("--kg-pool", type=int, default=0, help="Override Kaggle candidate pool depth before final ranking.")
    ap.add_argument("--hf-pages-per-query", type=int, default=12, help="HF pages to pull per query via cursor pagination.")
    ap.add_argument("--max-fill-rounds", type=int, default=3, help="How many widening rounds to run until target is reached.")
    ap.add_argument("--output-csv", required=True)
    ap.add_argument("--output-selected-json", default="")
    ap.add_argument("--output-failures-json", default="")
    ap.add_argument("--exclude-repos-csv", default="", help="CSV containing model_repo_id column to exclude from candidate selection.")
    args = ap.parse_args()
    run_scan(args)


if __name__ == "__main__":
    main()
