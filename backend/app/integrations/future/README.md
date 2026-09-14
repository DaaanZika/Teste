# Future integrations

These modules are **interfaces only**. Nothing here is wired up or called by
the application — they exist so the next phase (cloud storage, Gmail
ingestion, TSE export) can be implemented by filling in a class that
already matches the shape the rest of the backend expects, instead of
redesigning call sites across the codebase.

Google OAuth login is **no longer here** — it moved to a real
implementation once it was actually built: see `app/services/auth/`
(`google_oauth.py`, `session_service.py`) and `app/api/routes/auth.py`.
It is functional whenever `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`/
`GOOGLE_REDIRECT_URI` are configured, and raises `NotConfiguredError`
(never a fake success) otherwise.

Do not import the remaining stubs here from `app/api` or `app/services`.
Do not add credentials, SDKs, or network calls to them until the
integration is actually being built.
