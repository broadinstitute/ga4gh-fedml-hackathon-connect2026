"""RO-Crate helpers for exporting provenance records."""

from __future__ import annotations

import io
import zipfile
from datetime import timezone
from typing import Any

from provenance_server.models import ProvenanceRecordRead, WorkflowRead


def _iso(dt) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def build_rocrate_metadata(
    records: list[ProvenanceRecordRead],
    workflows: dict[str, WorkflowRead],
    site: str = "unknown",
) -> dict[str, Any]:
    """Build an RO-Crate metadata JSON-LD document from provenance records.

    The crate follows the RO-Crate 1.1 specification:
    https://www.researchobject.org/ro-crate/specification/1.1/

    Each provenance record is represented as a ``CreateAction`` entity with:
    - ``instrument`` → the ``SoftwareApplication`` (workflow)
    - ``result`` → the data element (``File`` / ``Dataset``)
    """
    graph: list[dict[str, Any]] = [
        # Root data entity
        {
            "@type": "Dataset",
            "@id": "./",
            "name": f"Provenance Crate — {site}",
            "description": "GA4GH workflow provenance records exported as RO-Crate",
            "license": "https://creativecommons.org/licenses/by/4.0/",
        },
        # Metadata file descriptor
        {
            "@type": "CreativeWork",
            "@id": "ro-crate-metadata.json",
            "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
            "about": {"@id": "./"},
        },
    ]

    # Add workflow SoftwareApplication entities (deduplicated)
    for wf in workflows.values():
        entity: dict[str, Any] = {
            "@type": ["SoftwareApplication", "HowTo"],
            "@id": wf.id,
            "name": wf.name or wf.id,
            "version": wf.version,
            "description": wf.description,
        }
        if wf.trs_url:
            entity["url"] = wf.trs_url
        graph.append(entity)

    # Add data elements and CreateAction entities per record
    for rec in records:
        data_entity: dict[str, Any] = {
            "@type": "File",
            "@id": rec.data_element_id,
            "name": rec.data_element_id,
        }
        graph.append(data_entity)

        action: dict[str, Any] = {
            "@type": "CreateAction",
            "@id": f"#action-{rec.id}",
            "name": f"Workflow execution producing {rec.data_element_id}",
            "instrument": {"@id": rec.workflow_id},
            "result": {"@id": rec.data_element_id},
            "startTime": _iso(rec.execution_timestamp),
            "agent": {"@type": "Organization", "name": site},
        }
        if rec.execution_id:
            action["object"] = {"@id": rec.execution_id, "@type": "Action", "name": rec.execution_id}
        if rec.parameters:
            action["actionAccessibilityRequirement"] = rec.parameters
        graph.append(action)

    return {
        "@context": "https://w3id.org/ro/crate/1.1/context",
        "@graph": graph,
    }


def build_rocrate_zip(
    records: list[ProvenanceRecordRead],
    workflows: dict[str, WorkflowRead],
    site: str = "unknown",
) -> bytes:
    """Return a zip archive containing the RO-Crate metadata file."""
    import json

    metadata = build_rocrate_metadata(records, workflows, site)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("ro-crate-metadata.json", json.dumps(metadata, indent=2))
    return buf.getvalue()
