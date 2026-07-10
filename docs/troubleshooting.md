# Troubleshooting

- Backend cannot connect to PostgreSQL: run `docker compose ps` and check the `postgres` health check.
- Login fails: run `make seed` or inspect `ADMIN_EMAIL` and `ADMIN_PASSWORD`.
- No emails appear: open MailHog at http://localhost:8025 and verify `SMTP_HOST=mailhog` inside Docker.
- Telegram does nothing: set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
- n8n HMAC errors: make sure the same `N8N_WEBHOOK_SECRET` is used by n8n and the API.
