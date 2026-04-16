# GA4GH Provenance Server

A **Beacon-style API for workflow provenance** across GA4GH federated sites.

Think of it as "Beacon Network, but for data elements produced by workflows" — any site in the federation can answer the question:

> *"Do you have data elements produced by workflow X (version Y)?"*

The server is based on [RO-Crate](https://www.researchobject.org/ro-crate/) provenance vocabulary and integrates with the [GA4GH Tool Registry Service (TRS)](https://ga4gh.github.io/tool-registry-service-schemas/) / [Dockstore](https://dockstore.org) for workflow metadata.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Federated Network                     │
│                                                          │
│  ┌─────────────┐     /federated/query     ┌───────────┐ │
│  │  Node A     │ ◄──────────────────────► │  Node B   │ │
│  │  (Site A)   │                          │  (Site B) │ │
│  └──────┬──────┘                          └─────┬─────┘ │
│         │  local provenance DB                  │       │
│  ┌──────▼──────────────────────────────────┐    │       │
│  │  SQLite / PostgreSQL                    │    │       │
│  │  workflows  ← ProvenanceRecords →       │    │       │
│  └─────────────────────────────────────────┘    │       │
└──────────────────────────────────────────────────────────┘
```

Each node runs its own instance with its own database. No shared state is required; federation works by fanning out HTTP queries to configured peer nodes.

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/provenance/info` | GA4GH service-info |
| `POST` | `/provenance/workflows` | Register a workflow |
| `GET`  | `/provenance/workflows` | List workflows |
| `GET`  | `/provenance/workflows/{id}` | Get workflow details |
| `PUT`  | `/provenance/workflows/{id}` | Update workflow |
| `POST` | `/provenance/records` | Register a provenance record |
| `GET`  | `/provenance/records` | List records |
| `GET`  | `/provenance/records/{id}` | Get a record |
| `DELETE` | `/provenance/records/{id}` | Delete a record |
| `POST` | `/provenance/query` | Beacon-style query |
| `POST` | `/provenance/query/export` | Export results as RO-Crate zip |
| `POST` | `/federated/query` | Fan-out query to peer nodes |
| `GET`  | `/federated/peers` | List configured peers |

Interactive docs are available at `/docs` (Swagger UI) and `/redoc`.

---

## Data Model

A **ProvenanceRecord** links a data element to the workflow that produced it:

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "data_element_id": "drs://drs.example.org/sample-NA12878",
  "workflow_id": "trs://dockstore.org/workflow/github.com/broadinstitute/gatk-workflows/broad-prod-wgs-germline-snps-indels",
  "workflow_version": "3.1.0",
  "execution_id": "wes-run-abc123",
  "site": "site-a",
  "parameters": { "reference": "hg38", "sample": "NA12878" },
  "execution_timestamp": "2026-04-15T10:00:00Z",
  "created_at": "2026-04-15T12:00:00Z"
}
```

**Key identifiers:**

- `data_element_id` — DRS object ID (`drs://...`) or any resolvable URI
- `workflow_id` — canonical TRS URI (`trs://dockstore.org/workflow/...`)
- `execution_id` — WES run ID or TES task ID

---

## Quick Start

### Local (development)

```bash
# Install
cd 01-access-data-compute/provenance-server
pip install -e ".[dev]"

# Run
PROVENANCE_SITE=my-site uvicorn provenance_server.main:app --reload

# Open docs
open http://localhost:8000/docs
```

### Docker (single node)

```bash
docker build -t provenance-server .
docker run -p 8000:8000 \
  -e PROVENANCE_SITE=my-site \
  -e PROVENANCE_SERVICE_ID=my-node \
  provenance-server
```

### Two-node demo

```bash
cd demo
docker compose up --build --detach

# Seed demo data
python seed_data.py

# Or run the full end-to-end demo script
bash run_demo.sh
```

After seeding:

- Node A: <http://localhost:8001/docs>
- Node B: <http://localhost:8002/docs>

---

## Configuration

All settings are read from environment variables (prefix `PROVENANCE_`) or a `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `PROVENANCE_SERVICE_ID` | `provenance-server-default` | Unique node identifier |
| `PROVENANCE_SERVICE_NAME` | `GA4GH Provenance Server` | Human-readable name |
| `PROVENANCE_SITE` | `local` | Site/node label |
| `PROVENANCE_DATABASE_URL` | `sqlite+aiosqlite:///./provenance.db` | SQLAlchemy DB URL |
| `PROVENANCE_PEER_NODES` | _(empty)_ | Comma-separated peer node base URLs |

---

## Federated Queries

Register peer nodes via the environment variable:

```bash
PROVENANCE_PEER_NODES="http://node-b:8000,http://node-c:8000"
```

Then issue a federated query:

```bash
curl -X POST http://localhost:8000/federated/query \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "trs://dockstore.org/workflow/github.com/broadinstitute/gatk-workflows/broad-prod-wgs-germline-snps-indels",
    "workflow_version": "3.1.0"
  }'
```

The response aggregates results from all peers, each annotated with `_source_node`.

---

## RO-Crate Export

Export matching records as a standards-compliant RO-Crate zip:

```bash
curl -X POST http://localhost:8000/provenance/query/export \
  -H "Content-Type: application/json" \
  -d '{"workflow_id": "trs://dockstore.org/workflow/github.com/broadinstitute/gatk-workflows/broad-prod-wgs-germline-snps-indels"}' \
  -o provenance-crate.zip
```

The zip contains `ro-crate-metadata.json` with `CreateAction` entities linking
each data element to its producing workflow (`SoftwareApplication`).

---

## TRS / Dockstore Integration

When registering a workflow, if the `id` starts with `trs://` and no `name` is
provided, the server automatically queries the corresponding TRS endpoint to
populate metadata:

```bash
curl -X POST http://localhost:8000/provenance/workflows \
  -H "Content-Type: application/json" \
  -d '{"id": "trs://dockstore.org/workflow/github.com/broadinstitute/gatk-workflows/broad-prod-wgs-germline-snps-indels"}'
```

---

## Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

---

## Design Decisions

1. **Beacon alignment** — the `meta`/`response` response envelope mirrors Beacon v2, so Beacon-compatible tooling can be adapted.
2. **TRS URI as canonical ID** — using `trs://host/workflow/...` as the workflow identifier ensures records from different sites can be compared without coordination.
3. **Opt-in federation** — nodes only expose what they explicitly register; there is no automatic data crawling.
4. **RO-Crate portability** — any query result can be exported as a valid RO-Crate 1.1 zip archive for long-term preservation and interoperability.
5. **SQLite by default** — zero-configuration for development; swap to PostgreSQL via `PROVENANCE_DATABASE_URL` for production.

---

## Relation to GA4GH Standards

| This server | GA4GH standard |
|-------------|----------------|
| Workflow identifier | [TRS](https://github.com/ga4gh/tool-registry-service-schemas) |
| Data element identifier | [DRS](https://github.com/ga4gh/data-repository-service-schemas) |
| Workflow execution ID | [WES](https://github.com/ga4gh/workflow-execution-service-schemas) / [TES](https://github.com/ga4gh/task-execution-schemas) |
| Provenance vocabulary | [RO-Crate](https://www.researchobject.org/ro-crate/) |
| Query/response pattern | [Beacon v2](https://github.com/ga4gh-beacon/beacon-v2) |
| Service metadata | [Service Info](https://github.com/ga4gh-discovery/ga4gh-service-info) |
