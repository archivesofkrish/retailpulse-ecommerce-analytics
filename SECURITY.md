# Security Policy

## Scope

RetailPulse is a portfolio and analytical case-study project. The checked-in sample is synthetic. The full UCI Online Retail II dataset is retrieved separately and is not committed to this repository.

The project is not an authenticated, production retail service. Do not expose the Streamlit service directly to the public internet or use it to process sensitive production customer data without adding appropriate authentication, authorization, privacy controls and operational review.

## Reporting a vulnerability

Please do not publish exploitable vulnerability details, credentials, personal information or proof-of-concept payloads in a public issue or pull request.

Use GitHub's private vulnerability reporting for this repository when it is enabled (repository **Security** tab → **Advisories** → **Report a vulnerability**). If private reporting is unavailable, contact the repository owner privately through their GitHub profile and ask for a secure reporting channel.

Include the affected commit or version, impact, reproducible steps that do not expose real data, and any suggested mitigation. Do not include secrets, customer records or private datasets.

## Supported version

Security fixes are applied to the current default branch. Older commits and untagged development branches are not maintained release lines.

## Security automation

GitHub Actions runs CodeQL static analysis and a Python dependency vulnerability audit. Dependabot checks the Python dependencies, GitHub Actions and Docker base image for updates. Automated findings and updates still require human review and passing tests before merge.
