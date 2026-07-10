# Recreating the Workflow in Make.com

Do not import these n8n JSON files into Make.com. Recreate the scenario with native Make modules.

Modules:

1. Custom Webhook receives the service request payload.
2. Tools module validates required fields and maps correlation ID.
3. HTTP module calls `POST /api/v1/automation/classify` with `x-serviceflow-signature`.
4. JSON parser validates the AI response fields.
5. Router sends low-confidence items to manual review and normal items to ticket creation.
6. HTTP module calls `POST /api/v1/tickets`.
7. Email module sends customer confirmation.
8. HTTP module calls Telegram Bot API when token and chat ID are configured.
9. Error handler route calls `POST /api/v1/automation/runs`.

Filters:

- `confidence < 0.75` routes to manual review.
- HTTP status `>= 500` retries with exponential backoff.
- HTTP status `400` or schema validation errors do not retry.

Webhook payload:

```json
{"customer_name":"Anna Kowalska","customer_email":"anna@example.com","customer_phone":"+48123","device_type":"printer","device_model":"HP LaserJet","description":"Printer toner error and urgent administration request."}
```

Variable mapping:

- `public_reference` from ticket response to email subject and Telegram text.
- `correlation_id` from webhook headers or Make execution ID to automation run records.
- `requires_manual_review` controls the router branch.
