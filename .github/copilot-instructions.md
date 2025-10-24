## TrikeGo — Copilot instructions (concise)

This file contains focused, actionable guidance for AI coding agents working in the TrikeGo repository.

- Project type: Django web app (Django 5.x) with REST API pieces and simple fare-estimation utilities.
- Key app folders: `apps/user` (custom user model + auth), `apps/booking` (booking endpoints/templates).
- Important modules:
  - `trikeGo/settings.py` — central config (loads .env via python-dotenv). DB points to Supabase Postgres; prefer .env overrides for secrets.
  - `fare_estimation/fare.py` and `fare_estimation/distance.py` — single-source fare logic. Use `calculate_fare(lat1, lon1, lat2, lon2)` when you need fare estimates.
  - `templates/` and `static/` — server-rendered front-end (no heavy JS build system).

Dev/run commands (Windows PowerShell):
  - Create venv: `python -m venv env`
  - Activate: `env\Scripts\Activate.ps1` (PowerShell) or `env\Scripts\activate` (cmd)
  - Install: `pip install -r requirements.txt`
  - Migrate DB: `python manage.py migrate`
  - Create admin: `python manage.py createsuperuser`
  - Run server: `python manage.py runserver`

Notes about architecture & patterns (do not invent):
- Auth: `AUTH_USER_MODEL = "user.CustomUser"` (see `apps/user`) — treat `apps/user` as the source of truth for user fields and serializers.
- API: Django REST Framework is configured with `SessionAuthentication` + `IsAuthenticated` by default. Endpoints live under `apps/*/views.py` and serializers under `apps/*/serializers.py` where present.
- External services:
  - Supabase/Postgres: DB credentials are currently in `settings.py` but `python-dotenv` is loaded — prefer .env to override sensitive values.
  - OpenRouteService: `OPENROUTESERVICE_API_KEY` is read from env; usage typically occurs in route/distance helpers. See `fare_estimation` for distance logic; OpenRouteService usage may be found in booking-related modules.

Project-specific conventions to follow:
- Keep fare/business logic in `fare_estimation/` (pure python functions, easy to unit test).
- UI templates live in `trikeGo/templates/booking` and `trikeGo/templates/user` — modify server-side templates rather than adding a frontend build pipeline.
- Static assets: `static/` for development, `staticfiles/` is the collect target defined in settings.

Quick examples for code edits:
- To change base fare or per-km rate, edit constants in `fare_estimation/fare.py` (`BASE_FARE`, `PER_KM_RATE`).
- To compute fare in code: `from fare_estimation.fare import calculate_fare` then `calculate_fare(lat1, lon1, lat2, lon2)`.
- To add a protected API endpoint, follow existing `apps.booking` view patterns and rely on DRF's session auth; check `trikeGo/settings.py` for REST_FRAMEWORK defaults.

Testing & quick checks:
- There is a simple script `fare_estimation/example_test.py` — run with `python fare_estimation/example_test.py` to sanity-check fare calculations.
- There are no heavy JS test or build steps detected — focus on Django unit tests and small scripts.

Safety and secrets:
- Do NOT commit secrets. If you find keys in `settings.py`, prefer moving them to `.env` and reference `os.environ`.

If anything here is unclear or you need deeper app-level guidance (models, serializers, or booking flows), tell me which part (e.g., `apps/booking/views.py`) and I'll expand with concrete call sites and examples.
