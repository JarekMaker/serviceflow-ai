# API Examples

Login:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login -H "content-type: application/json" -d '{"email":"admin@serviceflow.local","password":"Admin123!ChangeMe"}'
```

List tickets:

```bash
curl http://localhost:8000/api/v1/tickets -H "authorization: Bearer TOKEN"
```

Submit request:

```bash
curl -X POST http://localhost:8000/api/v1/tickets -H "content-type: application/json" -d '{"customer_name":"Anna","customer_email":"anna@example.com","device_type":"printer","description":"Printer displays toner error and urgently needs service for administration."}'
```
