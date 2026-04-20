# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest  | ✅        |
| Older   | ❌        |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **Do NOT open a public issue**
2. Email: [open an issue with the "security" label on this repository]
3. Include: description, steps to reproduce, potential impact

We aim to respond within 48 hours and will credit reporters unless anonymity is preferred.

## Scope

This project runs as a Home Assistant add-on or standalone Docker container on a local network. The threat model assumes:

- The instance is **not exposed to the public internet**
- Access is controlled by Home Assistant's authentication (ingress mode) or network-level controls (standalone mode)
- The HA long-lived access token is treated as a secret

## Architecture Notes

- **Add-on mode**: All API traffic goes through HA's ingress proxy, which handles authentication
- **Standalone mode**: The API has no built-in authentication — secure it via reverse proxy or network controls
- **No secrets in source**: Credentials are passed via environment variables only
- **Pydantic validation**: All API inputs are validated against strict schemas
- **SQLAlchemy ORM**: No raw SQL — parameterized queries only
