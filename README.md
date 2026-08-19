# Food Order Agent Backend

Production Django API for the Food Order Agent. Its ordering workflow runs on LangChain with Gemini, while Django tools enforce cart and checkout rules. The backend also owns server-side speech synthesis, cart and order state, and PostgreSQL persistence.

## Render deployment

The repository includes a `render.yaml` Blueprint. In Render, create a new Blueprint from this repository and provide the two secret values requested during setup:

- `DATABASE_URL`: the pooled Neon PostgreSQL connection string for the `food_order_agent` database, including `sslmode=require`
- `GEMINI_API_KEY`: the server-side Gemini API key

The Blueprint installs dependencies, collects Django static files, applies migrations, seeds the menu idempotently, starts Gunicorn, and checks `/health/` for service readiness.

The default Blueprint plan is Render Free to prevent accidental charges. Upgrade the web service to a paid instance before using it for a real production workload.

If Render assigns a different frontend URL, update `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` in the backend service environment.

## Local verification

```powershell
.venv\Scripts\python.exe manage.py check
.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.venv\Scripts\python.exe manage.py test
```
