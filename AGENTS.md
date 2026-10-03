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

## Before changing code
1. Inspect the relevant files.
2. Understand the current architecture.
3. Explain briefly what you intend to modify.
4. Implement the smallest coherent change.
5. Run relevant tests and linters.ls