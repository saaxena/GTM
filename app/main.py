import json
import logging
from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from .config import settings
from .clients import HubSpotClient, IntegrationError, verify_hubspot_v3_signature
from .forager import ForagerClient
from .models import EnrichmentRequest
from .service import EnrichmentService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("forager-hubspot")
app = FastAPI(title="Forager × HubSpot Enrichment", version="1.0.0",
              description="Python webhook service for company and contact enrichment.")

def service():
    return EnrichmentService(HubSpotClient(), ForagerClient())

@app.get("/")
async def root():
    return {"service": "Forager × HubSpot Enrichment", "status": "running", "docs": "/docs",
            "warning": "Configure credentials and verify Forager endpoint schemas before live use."}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/enrich/company/{company_id}")
async def enrich_company(company_id: str):
    try:
        return await service().enrich_company_id(company_id)
    except IntegrationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

@app.post("/enrich/contact/{contact_id}")
async def enrich_contact(contact_id: str):
    try:
        return await service().enrich_contact_id(contact_id)
    except IntegrationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

@app.post("/enrich/company-and-contacts/{company_id}")
async def enrich_company_and_contacts(company_id: str, request: EnrichmentRequest):
    try:
        return await service().enrich_company_and_contacts(company_id, request.job_titles, request.limit)
    except IntegrationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

@app.post("/webhooks/hubspot")
async def hubspot_webhook(request: Request, x_hubspot_signature_v3: str | None = Header(default=None), x_hubspot_request_timestamp: str | None = Header(default=None)):
    raw = await request.body()
    # HubSpot signature verification depends on the public URI. Behind a proxy, configure
    # PUBLIC_BASE_URL to the exact public URL registered with HubSpot.
    public_base = getattr(settings, "public_base_url", "")
    uri = public_base.rstrip("/") + request.url.path if public_base else str(request.url)
    if not verify_hubspot_v3_signature(settings.hubspot_webhook_secret, request.method, uri, raw, x_hubspot_signature_v3, x_hubspot_request_timestamp):
        raise HTTPException(status_code=401, detail="Invalid HubSpot webhook signature.")
    try:
        events = json.loads(raw)
        if not isinstance(events, list):
            events = [events]
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.")

    results = []
    for event in events:
        subscription = (event.get("subscriptionType") or "").lower()
        object_id = event.get("objectId")
        try:
            if "company" in subscription and object_id:
                results.append(await service().enrich_company_and_contacts(str(object_id), settings.allowed_titles, 5))
            elif "contact" in subscription and object_id:
                results.append(await service().enrich_contact_id(str(object_id)))
            else:
                results.append({"status": "ignored", "subscriptionType": subscription, "reason": "Unsupported event"})
        except Exception as exc:
            logger.exception("Webhook event failed")
            results.append({"status": "error", "objectId": object_id, "error": str(exc)[:300]})
    return JSONResponse(content={"received": len(events), "results": results}, status_code=200)
