import hashlib
import hmac
import json
import base64
import time
from typing import Any
from urllib.parse import urlparse
import httpx
from .config import settings

class IntegrationError(RuntimeError):
    pass

class HubSpotClient:
    BASE = "https://api.hubapi.com"

    def __init__(self, token: str | None = None):
        self.token = token if token is not None else settings.hubspot_access_token

    def _headers(self):
        if not self.token:
            raise IntegrationError("HUBSPOT_ACCESS_TOKEN is not configured.")
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    async def request(self, method: str, path: str, **kwargs):
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.request(method, self.BASE + path, headers=self._headers(), **kwargs)
        if response.is_error:
            raise IntegrationError(f"HubSpot API returned {response.status_code}: {response.text[:500]}")
        return response.json() if response.content else {}

    async def get_company(self, company_id: str):
        return await self.request("GET", f"/crm/v3/objects/companies/{company_id}", params={"properties": "name,domain,description,industry,numberofemployees,annualrevenue,linkedin_company_page"})

    async def get_contact(self, contact_id: str):
        return await self.request("GET", f"/crm/v3/objects/contacts/{contact_id}", params={"properties": "firstname,lastname,email,phone,jobtitle,linkedin_url,city,state,country,company,website"})

    async def search_company_by_domain(self, domain: str):
        body = {"filterGroups":[{"filters":[{"propertyName":"domain","operator":"EQ","value":domain}]}],
                "properties":["name","domain","description","industry","numberofemployees","annualrevenue","linkedin_company_page"],"limit":1}
        result = await self.request("POST", "/crm/v3/objects/companies/search", json=body)
        return result.get("results", [])

    async def search_contact_by_email(self, email: str):
        body = {"filterGroups":[{"filters":[{"propertyName":"email","operator":"EQ","value":email}]}],
                "properties":["firstname","lastname","email","phone","jobtitle","linkedin_url","city","state","country","company","website"],"limit":1}
        result = await self.request("POST", "/crm/v3/objects/contacts/search", json=body)
        return result.get("results", [])

    async def update_company(self, company_id: str, properties: dict[str, Any]):
        return await self.request("PATCH", f"/crm/v3/objects/companies/{company_id}", json={"properties": properties})

    async def create_company(self, properties: dict[str, Any]):
        return await self.request("POST", "/crm/v3/objects/companies", json={"properties": properties})

    async def update_contact(self, contact_id: str, properties: dict[str, Any]):
        return await self.request("PATCH", f"/crm/v3/objects/contacts/{contact_id}", json={"properties": properties})

    async def create_contact(self, properties: dict[str, Any]):
        return await self.request("POST", "/crm/v3/objects/contacts", json={"properties": properties})

    async def associate_contact_company(self, contact_id: str, company_id: str):
        # HubSpot v4 default association type for contact-to-company is supported by this endpoint.
        return await self.request("PUT", f"/crm/v4/objects/contacts/{contact_id}/associations/default/companies/{company_id}")

def verify_hubspot_signature(raw_body: bytes, signature: str | None, client_secret: str) -> bool:
    """Verify HubSpot v3 signature. A blank secret disables verification only for local development."""
    if not client_secret:
        return settings.demo_mode
    if not signature:
        return False
    # HubSpot v3: HMAC-SHA256(client secret, HTTP method + URI + body)
    # URI must be the externally visible request URI including query string.
    return False  # Use verify_hubspot_v3_signature in main.py where URI/method are available.

def verify_hubspot_v3_signature(client_secret: str, method: str, uri: str, raw_body: bytes, signature: str | None, timestamp: str | None) -> bool:
    """Verify HubSpot v3 signature and reject requests older than five minutes."""
    if not client_secret or not signature or not timestamp:
        return False
    try:
        sent_at_ms = int(timestamp)
    except (TypeError, ValueError):
        return False
    if abs(int(time.time() * 1000) - sent_at_ms) > 5 * 60 * 1000:
        return False
    # HubSpot v3 signs method + URI + body + timestamp and base64-encodes HMAC-SHA256.
    source = method.upper().encode() + uri.encode() + raw_body + str(timestamp).encode()
    digest = hmac.new(client_secret.encode(), source, hashlib.sha256).digest()
    expected = base64.b64encode(digest).decode()
    return hmac.compare_digest(expected, signature)
