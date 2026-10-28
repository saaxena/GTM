# Forager × HubSpot Enrichment Automation

Python/FastAPI implementation scaffold for the OneGTM Lab AI Automation Engineer evaluation.

## What it does

- Exposes company and contact enrichment endpoints.
- Receives HubSpot webhook events at `/webhooks/hubspot`.
- Enriches company records and discovers contacts filtered by job title.
- Updates existing contacts by email or creates new contacts and associates them to the company.
- Avoids overwriting fields with empty values.
- Supports Railway deployment using the included Dockerfile.

## Important before live use

**This is a starter implementation, not a verified live integration yet.** Your Forager account's current API documentation must be checked for the correct base URL, authentication scheme, endpoint paths, request payloads, and response field names. Configure the `FORAGER_*` environment variables accordingly. The example endpoint paths are placeholders and may need changes.

The app intentionally does not fabricate real people, emails, phone numbers, or revenue. Demo mode only returns labelled synthetic company data and does not invent contacts.

HubSpot v3 webhook signature validation checks the signature and timestamp. Set `HUBSPOT_WEBHOOK_SECRET` and ensure the URI used in signature verification exactly matches the externally registered URL; configure reverse-proxy/public URL handling before enabling live webhooks. Do not disable signature validation in production.

## Requirements

- Python 3.11+
- A HubSpot private app access token with CRM read/write scopes for companies and contacts, plus permissions needed for associations.
- Forager API key and access to company enrichment, contact enrichment, and contact search endpoints.
- A public HTTPS deployment URL for webhooks.

## Run locally

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1

pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials and verified Forager API paths.
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` to view the API documentation and `http://127.0.0.1:8000/health` for health status.

## Test

```bash
pytest -q
```

## Manual test endpoints

Use your own existing HubSpot company/contact IDs only after credentials are configured:

```bash
curl -X POST http://127.0.0.1:8000/enrich/company/YOUR_COMPANY_ID
curl -X POST http://127.0.0.1:8000/enrich/contact/YOUR_CONTACT_ID
curl -X POST http://127.0.0.1:8000/enrich/company-and-contacts/YOUR_COMPANY_ID \
  -H "Content-Type: application/json" \
  -d '{"job_titles":["CTO","VP Engineering"],"limit":5}'
```

## HubSpot webhook setup

1. Deploy the app to a public HTTPS URL.
2. Configure a HubSpot app/webhook subscription for company creation and contact creation events.
3. Set the webhook target to `https://YOUR_PUBLIC_DOMAIN/webhooks/hubspot`.
4. Configure the correct webhook signing secret in `HUBSPOT_WEBHOOK_SECRET`.
5. Make sure the exact public URI used for signature validation matches HubSpot's signature scheme and proxy behavior.
6. Verify events using a test company/contact before relying on production records.

HubSpot webhook subscriptions and app-specific configuration vary by app type/plan. Confirm the exact event names and webhook setup options in your HubSpot developer account.

## Railway deployment

1. Push this repository to GitHub.
2. In Railway, create a new project from the repository.
3. Add all required environment variables in Railway's Variables panel.
4. Set a public domain and wait for `/health` to return `{"status":"healthy"}`.
5. Complete a live test using a dedicated test company/contact before registering the webhook in a production portal.

## Required evaluation checklist

- [ ] Verify Forager API schema and endpoint configuration.
- [ ] Confirm HubSpot property internal names and required scopes.
- [ ] Enrich the OpenAI dummy/test company using real Forager response data.
- [ ] Enrich/create five contacts with available contact details; do not fabricate unavailable data.
- [ ] Verify job-title filtering with matching and non-matching titles.
- [ ] Verify company-created and contact-created webhook events end-to-end.
- [ ] Record a demo video showing the service logs, webhook firing, HubSpot updates, and title filtering.
- [ ] Document any useful extra Forager fields for discussion.

## Security / reliability notes

- Never commit `.env` or API keys.
- Add retries with bounded backoff and idempotency before production rollout.
- Consider asynchronous webhook processing for larger event batches and return quickly to HubSpot.
- Add audit logging without logging tokens or unnecessary personal data.
- Review data-provider terms and applicable privacy requirements before enriching or storing personal contact data.
