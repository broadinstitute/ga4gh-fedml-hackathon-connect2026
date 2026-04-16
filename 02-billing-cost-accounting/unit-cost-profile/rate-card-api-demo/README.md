# Rate Card API Demo

Reference FastAPI implementation of the GA4GH federated rate card schema. See `rate-card-spec.md` for the schema and `schema.py` for the Pydantic models.

## Run

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Point at a different rate-card file with the `RATE_CARD_FILE` env var:

```bash
RATE_CARD_FILE=/path/to/your/rate-card.json uvicorn main:app --reload
```

Default: `../unit-cost-profile/node-rate-card-example02.json`.

## Endpoints

- `GET /api/rate-card` — full card (JSON-LD)
- `GET /api/rate-card/offers/{offer_id}` — single offer by identifier
- `GET /api/rate-card/service-info` — GA4GH-style discovery stub

## Files

- `schema.py` — Pydantic models. JSON-LD `@` keys and `x_ga4gh:` extensions are mapped via field aliases; `populate_by_name=True` lets you construct from Python names and serialize back to aliased form with `model_dump(by_alias=True)`.
- `main.py` — FastAPI wiring; loads the rate card at import time.
