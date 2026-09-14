# Future integrations

These modules are **interfaces only**. Nothing here is wired up or called by
the application — they exist so the next phase (cloud storage, Gmail
ingestion, TSE export) can be implemented by filling in a class that
already matches the shape the rest of the backend expects, instead of
redesigning call sites across the codebase.

Two integrations are **no longer here** — they moved to real
implementations once actually built:

- Google OAuth login: `app/services/auth/` (`google_oauth.py`,
  `session_service.py`) and `app/api/routes/auth.py`.
- Google Drive storage: `app/integrations/google_drive_storage.py`
  (`GoogleDriveStorage`, selected via `STORAGE_PROVIDER=google_drive` or
  `BACKUP_STORAGE_PROVIDER=google_drive`), token storage in
  `app/services/integrations/google_tokens.py`, connect/disconnect routes
  in `app/api/routes/integrations.py`.

Both are functional whenever their required configuration is present and
raise `NotConfiguredError` (never a fake success) otherwise.

Do not import the remaining stubs here (`cloud_storage_provider.py`,
`gmail_provider.py`, `tse_exporter.py`) from `app/api` or `app/services`.
Do not add credentials, SDKs, or network calls to them until the
integration is actually being built.
