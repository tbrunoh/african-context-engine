# Security policy

## Reporting a vulnerability

Please do not open a public issue for security problems. Use GitHub private vulnerability reporting on this repository (Security tab, Report a vulnerability). Maintainers acknowledge reports within three business days and aim to publish a fix and advisory within 90 days.

## In scope

- Exposure of personal data or session history across users or channels
- Bypass of the safety escalation path
- Access to verified tier facts without entitlement
- Injection through channel payloads, context packs or MCP tool arguments
- Leaks of payment credentials or tampering with payment requests

## Deployment guidance

- Never commit Daraja or other payment credentials. Inject them at runtime from a secrets manager.
- Verify webhook signatures from every channel provider before passing payloads to adapters.
- Treat context pack content and MCP arguments as untrusted input.
