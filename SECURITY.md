# Security Policy

## Supported versions

The current main branch is the supported development line. RetailPulse requires Python 3.11 or newer. Python 3.10 reached upstream end-of-life on 1 October 2026 and no longer receives Python security updates.

## Reporting a vulnerability

Please do not publish credentials, customer-level data or an exploitable vulnerability in a public issue.

Use GitHub's **Report a vulnerability** flow in the repository's Security tab when private vulnerability reporting is enabled. If the option is unavailable, contact the repository maintainer through GitHub and request a private reporting channel before sharing sensitive technical details.

Reports should include the affected commit or version, component, impact, reproduction steps and any suggested mitigation. Do not attach the UCI workbook or customer-level transaction extracts.

## Data and deployment safety

- Do not commit the downloaded workbook, processed transaction files, customer-level exports, secrets or local environment files.
- Treat customer identifiers and invoice-level records as sensitive operational data even when the supplied public dataset is historical.
- Keep source and processed-data directories access-controlled.
- The Docker Compose setup binds to loopback and mounts data read-only.
- The Streamlit application does not provide authentication or role-based access control. Do not expose port 8501 directly to the public internet; remote deployment requires a TLS reverse proxy and an authentication/authorization layer.
- Rebuild images and update dependencies when security updates are released.
