# Architecture

FastAPI is the system of record. It owns validation, authentication, ticket state, AI output validation, duplicate detection, SLA calculation, and audit events. n8n coordinates external workflow steps and can retry transient integration failures without moving domain rules into low-code nodes.

The frontend talks only to versioned `/api/v1` endpoints. PostgreSQL stores durable state, Redis is available for rate limits and future queues, MailHog receives local email, and MinIO represents S3-compatible attachment storage.
