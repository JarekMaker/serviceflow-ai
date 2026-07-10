# Security

Threat model: public request submission, administrator access, internal automation webhooks, file uploads, and third-party notification channels.

Controls include JWT authentication, Argon2 password hashing, CORS allow-listing, Pydantic validation, HMAC signatures for automation endpoints, attachment type and size validation, request IDs, structured logs, and masking of customer email and phone data in logs.

Secrets are loaded from environment variables and `.env.example` contains only development placeholders. AI output is untrusted and cannot update tickets unless it validates against the schema.
