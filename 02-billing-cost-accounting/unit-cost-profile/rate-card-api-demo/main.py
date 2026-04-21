import os
from pathlib import Path

from fastapi import FastAPI, HTTPException

from schema import Offer, RateCard

DEFAULT_RATE_CARD = (
    Path(__file__).parent.parent / "unit-cost-profile" / "node-rate-card-example02.json"
)
RATE_CARD_FILE = Path(os.environ.get("RATE_CARD_FILE", DEFAULT_RATE_CARD))

RATE_CARD: RateCard = RateCard.model_validate_json(RATE_CARD_FILE.read_text())

app = FastAPI(title="Federated Rate Card API", version="0.1.0")


@app.get("/api/rate-card", response_model=RateCard, response_model_by_alias=True)
def get_rate_card() -> RateCard:
    return RATE_CARD


@app.get(
    "/api/rate-card/offers/{offer_id}",
    response_model=Offer,
    response_model_by_alias=True,
)
def get_offer(offer_id: str) -> Offer:
    for offer in RATE_CARD.offers:
        if offer.identifier == offer_id:
            return offer
    raise HTTPException(status_code=404, detail=f"Unknown offer: {offer_id}")


@app.get("/api/rate-card/service-info")
def get_service_info() -> dict:
    return {
        "id": RATE_CARD.identifier,
        "name": RATE_CARD.name,
        "type": {
            "group": "org.ga4gh.fedml",
            "artifact": "rate-card",
            "version": RATE_CARD.spec_version,
        },
        "rateCardUrl": RATE_CARD.id_,
    }
