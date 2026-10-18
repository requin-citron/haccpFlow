# Project instructions

You are working on an open-source HACCP management platform.

## Stack
- Backend: FastAPI
- Frontend: Next.js
- Database: PostgreSQL
- MQTT: Mosquitto
- Zigbee ingestion: Zigbee2MQTT
- Deployment: Docker Compose

## Development rules
- Prefer simple, maintainable code.
- Use strict typing.
- Add tests for new business logic.
- Do not introduce new dependencies unless necessary.
- Preserve backward compatibility unless explicitly asked otherwise.
- Never hardcode tenant IDs, credentials, thresholds, or secrets.
- HACCP thresholds must be configurable, not embedded in application logic.
- All measurement edits must remain auditable.
- Use UTC timestamps internally.
- Keep the application multi-tenant ready.

## Security
- Validate all user-controlled inputs.
- Enforce tenant isolation at the backend level.
- Never trust frontend authorization checks.
- Use least privilege.
- Secrets must come from environment variables or a secret manager.

## Documentation
- The reference wiki lives in `doc/`; its index is `doc/README.md`.
- Every change to an API, data model, configuration, deployment, or business
  rule must update the relevant wiki page in the same change.
- The change-to-documentation matrix is in `doc/09-maintenance.md`.
- Add every new wiki page to the index and update the "last reviewed" date.

## Before changing code
1. Inspect the relevant files.
2. Understand the current architecture.
3. Explain briefly what you intend to modify.
4. Implement the smallest coherent change.
5. Run relevant tests and linters.
6. Update the wiki when behavior, interfaces, configuration, or deployment
   change.
