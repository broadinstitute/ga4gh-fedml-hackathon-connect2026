#!/usr/bin/env python3
"""Seed demo data into the two provenance nodes.

Usage:
    python seed_data.py

Assumes both nodes are running:
  - node-a on http://localhost:8001
  - node-b on http://localhost:8002
"""

from __future__ import annotations

import json
import sys

import httpx

NODE_A = "http://localhost:8001"
NODE_B = "http://localhost:8002"

WORKFLOW_GATK = "trs://dockstore.org/workflow/github.com/broadinstitute/gatk-workflows/broad-prod-wgs-germline-snps-indels"
WORKFLOW_ATAC = "trs://dockstore.org/workflow/github.com/ENCODE-DCC/atac-seq-pipeline/master"


def post(base_url: str, path: str, data: dict) -> dict:
    url = f"{base_url}{path}"
    resp = httpx.post(url, json=data, timeout=10)
    if resp.status_code not in (200, 201, 409):
        print(f"ERROR {resp.status_code} POST {url}: {resp.text}", file=sys.stderr)
        resp.raise_for_status()
    return resp.json()


def seed_node(base_url: str, site: str, records: list[dict]) -> None:
    print(f"\n--- Seeding {site} ({base_url}) ---")

    # Register workflows
    for wf_id, name, version in [
        (WORKFLOW_GATK, "GATK WGS Germline Pipeline", "3.1.0"),
        (WORKFLOW_ATAC, "ENCODE ATAC-seq Pipeline", "2.2.2"),
    ]:
        result = post(
            base_url,
            "/provenance/workflows",
            {"id": wf_id, "name": name, "version": version, "descriptor_type": "WDL"},
        )
        status = "409 already exists" if result.get("detail") else "created"
        print(f"  Workflow {name!r}: {status}")

    # Register provenance records
    for rec in records:
        result = post(base_url, "/provenance/records", rec)
        record_id = result.get("response", {}).get("id", "?")
        print(f"  Record {record_id}: {rec['data_element_id']}")


def main() -> None:
    seed_node(
        NODE_A,
        "site-a",
        [
            {
                "data_element_id": "drs://drs.example.org/sample-NA12878-gatk-hg38",
                "workflow_id": WORKFLOW_GATK,
                "workflow_version": "3.1.0",
                "execution_id": "wes-run-site-a-001",
                "site": "site-a",
                "parameters": {"reference": "hg38", "sample": "NA12878"},
            },
            {
                "data_element_id": "drs://drs.example.org/sample-NA12879-gatk-hg38",
                "workflow_id": WORKFLOW_GATK,
                "workflow_version": "3.1.0",
                "execution_id": "wes-run-site-a-002",
                "site": "site-a",
                "parameters": {"reference": "hg38", "sample": "NA12879"},
            },
            {
                "data_element_id": "drs://drs.example.org/atac-sample-001-site-a",
                "workflow_id": WORKFLOW_ATAC,
                "workflow_version": "2.2.2",
                "execution_id": "wes-run-site-a-003",
                "site": "site-a",
                "parameters": {"genome": "hg38"},
            },
        ],
    )

    seed_node(
        NODE_B,
        "site-b",
        [
            {
                "data_element_id": "drs://drs.example.org/sample-NA12880-gatk-hg38",
                "workflow_id": WORKFLOW_GATK,
                "workflow_version": "3.1.0",
                "execution_id": "wes-run-site-b-001",
                "site": "site-b",
                "parameters": {"reference": "hg38", "sample": "NA12880"},
            },
            {
                "data_element_id": "drs://drs.example.org/sample-NA12881-gatk-hg38",
                "workflow_id": WORKFLOW_GATK,
                "workflow_version": "3.1.0",
                "execution_id": "wes-run-site-b-002",
                "site": "site-b",
                "parameters": {"reference": "hg38", "sample": "NA12881"},
            },
        ],
    )

    print("\n=== Seed complete ===")
    print(f"Node A API docs: {NODE_A}/docs")
    print(f"Node B API docs: {NODE_B}/docs")


if __name__ == "__main__":
    main()
