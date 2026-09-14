# Future integrations

These modules are **interfaces only**. Nothing here is wired up or called by
the V1 application — they exist so the next phase (cloud storage, Gmail
ingestion, Google OAuth, TSE export) can be implemented by filling in a
class that already matches the shape the rest of the backend expects,
instead of redesigning call sites across the codebase.

Do not import these from `app/api` or `app/services` in V1. Do not add
credentials, SDKs, or network calls here until the integration is actually
being built.
