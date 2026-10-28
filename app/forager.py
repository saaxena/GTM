
from typing import Any

import httpx

from .config import settings
from .clients import IntegrationError


class ForagerClient:
    """Forager API adapter."""

    def __init__(self):
        self.api_key = settings.forager_api_key
        self.base_url = settings.forager_base_url.rstrip("/")
        self.account_id = settings.forager_account_id

    async def _post(
        self,
        path: str,
        payload: dict[str, Any],
    ) -> Any:
        if settings.demo_mode:
            return self._demo_response(path, payload)

        if not self.api_key:
            raise IntegrationError("FORAGER_API_KEY is not configured.")

        if not self.account_id:
            raise IntegrationError("FORAGER_ACCOUNT_ID is not configured.")

        url = f"{self.base_url}/{path.lstrip('/')}"

        try:
            async with httpx.AsyncClient(
                timeout=settings.request_timeout_seconds
            ) as client:
                response = await client.post(
                    url,
                    headers={
                        "X-API-KEY": self.api_key,
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
        except httpx.RequestError as exc:
            raise IntegrationError(
                f"Forager connection failed: {type(exc).__name__}"
            ) from exc

        if response.is_error:
            raise IntegrationError(
                f"Forager returned HTTP {response.status_code} "
                f"for {path}. Check the endpoint and API documentation."
            )

        try:
            return response.json()
        except ValueError as exc:
            raise IntegrationError(
                "Forager returned an invalid JSON response."
            ) from exc

    async def enrich_company(
        self,
        *,
        domain: str | None = None,
        name: str | None = None,
    ):
        if not domain:
            raise IntegrationError(
                "Company domain is required for organization search."
            )

        data = await self._post(
            f"/api/{self.account_id}/datastorage/organization_search/",
            {
                "domains": [domain],
                "page": 0,
            },
        )

        if isinstance(data, list):
            rows = data
        elif isinstance(data, dict):
            rows = data.get(
                "search_results",
                data.get("results", []),
            )
        else:
            rows = []

        if not isinstance(rows, list) or not rows:
            raise IntegrationError(
                f"Forager found no organization for {domain}."
            )

        org = rows[0]

        if not isinstance(org, dict):
            raise IntegrationError(
                "Unexpected organization result from Forager."
            )

        return {
            "name": org.get("name") or name,
            "domain": domain,
            "description": org.get("description"),
            "industry": org.get("industry"),
            "numberofemployees": org.get("employees_amount"),
            "annualrevenue": None,
            "linkedin_company_page": org.get("linkedin_url"),
        }

    async def enrich_contact(
        self,
        *,
        email: str | None = None,
        linkedin_url: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        company_domain: str | None = None,
    ):
        raise IntegrationError(
            "Contact enrichment is not configured. "
            "The correct Forager person lookup endpoint and payload "
            "must be verified before enabling this operation."
        )

    async def find_contacts(
        self,
        *,
        company_domain: str | None,
        company_name: str | None,
        job_titles: list[str],
        limit: int = 5,
    ):
        if not job_titles or limit <= 0:
            return {"results": []}

        if not company_domain:
            raise IntegrationError(
                "Company domain is required for contact search."
            )

        path = (
            f"/api/{self.account_id}/"
            "datastorage/person_role_search/"
        )

        results = []

        for title in job_titles:
            data = await self._post(
                path,
                {
                    "role_title": title,
                    "role_is_current": True,
                },
            )

            if isinstance(data, list):
                rows = data
            elif isinstance(data, dict):
                rows = data.get("search_results", [])
            else:
                rows = []

            if not isinstance(rows, list):
                continue

            for row in rows:
                if not isinstance(row, dict):
                    continue

                organization = row.get("organization") or {}
                if not isinstance(organization, dict):
                    continue

                result_domain = (
                    organization.get("domain") or ""
                ).lower().strip()

                wanted_domain = company_domain.lower().strip()

                # Never include a result whose company cannot
                # be verified against the requested domain.
                if result_domain != wanted_domain:
                    continue

                results.append(row)

                if len(results) >= limit:
                    return {"results": results[:limit]}

        return {"results": results[:limit]}

    @staticmethod
    def _demo_response(
        path: str,
        payload: dict[str, Any],
    ):
        if "organization_search" in path:
            return {
                "search_results": [
                    {
                        "name": payload.get("name") or "Demo Company",
                        "domain": (payload.get("domains") or [None])[0],
                        "description": "DEMO DATA - not verified.",
                        "industry": None,
                        "employees_amount": None,
                        "linkedin_url": None,
                    }
                ],
                "_demo": True,
            }

        if "person_role_search" in path or "search" in path:
            return {
                "results": [],
                "_demo": True,
                "note": "No fake contacts generated.",
            }

        return {
            "_demo": True,
            "note": "No verified enrichment data available.",
        }
