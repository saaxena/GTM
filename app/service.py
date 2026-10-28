from typing import Any
from .clients import HubSpotClient, IntegrationError
from .forager import ForagerClient

COMPANY_MAP = {
    "name": "name",
    "domain": "domain",
    "description": "description",
    "industry": "industry",
    "numberofemployees": "numberofemployees",
    "annualrevenue": "annualrevenue",
    "linkedin_company_page": "linkedin_company_page",
}
CONTACT_MAP = {
    "firstname": "firstname",
    "lastname": "lastname",
    "jobtitle": "jobtitle",
    "linkedin_url": "linkedin_url",
    "email": "email",
    "phone": "phone",
    "city": "city",
    "state": "state",
    "country": "country",
    "company": "company",
    "website": "website",
}

def nonempty_properties(data: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
    """Only return known HubSpot properties with meaningful values; never overwrite with blanks."""
    properties = {}
    for source, target in mapping.items():
        value = data.get(source)
        if value is not None and value != "":
            properties[target] = str(value) if isinstance(value, (int, float)) else value
    return properties

def title_matches(title: str | None, filters: list[str]) -> bool:
    if not filters:
        return True
    title = (title or "").strip().lower()
    return any(wanted in title for wanted in filters)

class EnrichmentService:
    def __init__(self, hubspot: HubSpotClient | None = None, forager: ForagerClient | None = None):
        self.hubspot = hubspot or HubSpotClient()
        self.forager = forager or ForagerClient()

    async def enrich_company_id(self, company_id: str) -> dict[str, Any]:
        record = await self.hubspot.get_company(company_id)
        current = record.get("properties", {})
        enriched = await self.forager.enrich_company(domain=current.get("domain"), name=current.get("name"))
        properties = nonempty_properties(enriched, COMPANY_MAP)
        if properties:
            await self.hubspot.update_company(company_id, properties)
        return {"status": "ok", "object_type": "company", "record_id": company_id,
                "updated_fields": sorted(properties), "data": properties,
                "notes": ["Forager response fields were mapped conservatively; inspect unmapped fields before adding more."]}

    async def enrich_contact_id(self, contact_id: str) -> dict[str, Any]:
        record = await self.hubspot.get_contact(contact_id)
        current = record.get("properties", {})
        company_domain = None
        company_name = current.get("company")
        if company_name and "." in company_name:
            company_domain = company_name
        enriched = await self.forager.enrich_contact(
            email=current.get("email"), linkedin_url=current.get("linkedin_url"),
            first_name=current.get("firstname"), last_name=current.get("lastname"),
            company_domain=company_domain,
        )
        properties = nonempty_properties(enriched, CONTACT_MAP)
        if properties:
            await self.hubspot.update_contact(contact_id, properties)
        return {"status": "ok", "object_type": "contact", "record_id": contact_id,
                "updated_fields": sorted(properties), "data": properties,
                "notes": ["No missing values are fabricated. Verify Forager's response schema and HubSpot property names."]}

    async def enrich_company_and_contacts(self, company_id: str, job_titles: list[str], limit: int = 5):
        company_result = await self.enrich_company_id(company_id)
        company = await self.hubspot.get_company(company_id)
        props = company.get("properties", {})
        discovered = await self.forager.find_contacts(
            company_domain=props.get("domain"), company_name=props.get("name"),
            job_titles=job_titles, limit=limit,
        )
        rows = discovered.get("results", discovered.get("contacts", []))
        processed = []
        for person in rows:
            title = person.get("jobtitle") or person.get("job_title") or person.get("title")
            if not title_matches(title, job_titles):
                continue
            email = person.get("email")
            props = nonempty_properties({
                "firstname": person.get("firstname") or person.get("first_name"),
                "lastname": person.get("lastname") or person.get("last_name"),
                "jobtitle": title,
                "linkedin_url": person.get("linkedin_url") or person.get("linkedin"),
                "email": email,
                "phone": person.get("phone"),
                "city": person.get("city"),
                "state": person.get("state"),
                "country": person.get("country"),
                "company": person.get("company") or company.get("properties", {}).get("name"),
                "website": person.get("website") or company.get("properties", {}).get("domain"),
            }, CONTACT_MAP)
            if not props:
                continue
            existing = await self.hubspot.search_contact_by_email(email) if email else []
            if existing:
                contact_id = existing[0]["id"]
                await self.hubspot.update_contact(contact_id, props)
                await self.hubspot.associate_contact_company(contact_id, company_id)
                action = "updated"
            elif email:
                created = await self.hubspot.create_contact(props)
                contact_id = created["id"]
                await self.hubspot.associate_contact_company(contact_id, company_id)
                action = "created"
            else:
                processed.append({"status": "skipped", "reason": "Contact has no email; cannot safely deduplicate/create", "job_title": title})
                continue
            processed.append({"status": action, "contact_id": contact_id, "job_title": title, "fields": sorted(props)})
        return {"status": "ok", "object_type": "company_with_contacts", "record_id": company_id,
                "company": company_result, "contacts": processed,
                "notes": ["Only contacts returned by Forager are processed. Email-less contacts are skipped to avoid duplicates.",
                          "Confirm whether your Forager plan/API returns all required fields."]}
