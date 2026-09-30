---
description: API handler conventions for files under src/api/
paths:
  - "src/api/**/*"
---

# API handler rules

- API handlers must use the `(req, res)` signature.
- Every handler must return a response on every execution path.
- Validate required request parameters before calling application services.
- Keep request parsing and HTTP response formatting inside the handler layer.
- API handlers must not contain direct PostgreSQL queries.
- API handlers must not import the PostgreSQL client directly.
- Database access must go through repository modules under `src/db/`.
- Keep business logic out of the HTTP handler when an application service already exists.
- Expected API failures must use the project's defined API error type.
- Do not return ad-hoc error objects from API handlers.
- Preserve consistent HTTP status codes for equivalent error conditions.
- Keep authentication and authorization checks before protected operations.