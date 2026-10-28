from typing import Any
from pydantic import BaseModel, Field

class EnrichmentRequest(BaseModel):
    company_domain: str | None = None
    company_name: str | None = None
    job_titles: list[str] = Field(default_factory=list)
    limit: int = Field(default=5, ge=1, le=25)

class WebhookEvent(BaseModel):
    subscriptionType: str | None = None
    eventId: int | None = None
    objectId: int | str | None = None
    propertyName: str | None = None
    propertyValue: str | None = None
    portalId: int | None = None
    appId: int | None = None
    occurredAt: int | None = None
    attemptNumber: int | None = None
    changeSource: str | None = None
    sourceId: str | None = None

class EnrichmentResult(BaseModel):
    status: str
    object_type: str
    record_id: str | None = None
    updated_fields: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    data: dict[str, Any] = Field(default_factory=dict)
