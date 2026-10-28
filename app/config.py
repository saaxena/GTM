from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    hubspot_access_token: str = ""
    hubspot_webhook_secret: str = ""
    public_base_url: str = ""
    forager_api_key: str = ""
    forager_base_url: str = "https://api-v2.forager.ai"
    forager_account_id: str = ""
    forager_enrich_company_path: str = "/v1/companies/enrich"
    forager_enrich_contact_path: str = "/v1/contacts/enrich"
    forager_find_contacts_path: str = "/v1/contacts/search"
    request_timeout_seconds: float = 30.0
    allowed_job_titles: str = "CEO,CTO,Chief Technology Officer,VP Engineering,Head of Sales"
    demo_mode: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def allowed_titles(self) -> list[str]:
        return [item.strip().lower() for item in self.allowed_job_titles.split(",") if item.strip()]

settings = Settings()
