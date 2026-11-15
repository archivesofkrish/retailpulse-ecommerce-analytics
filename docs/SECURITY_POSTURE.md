# RetailPulse security posture and maintenance

## Automated controls

| Control | Repository implementation | Operational expectation |
|---|---|---|
| Static code analysis | CodeQL Python workflow | Review and resolve actionable code-scanning alerts |
| Dependency update proposals | Dependabot for pip and GitHub Actions | Review, test and merge update PRs |
| Runtime support | Python 3.11, 3.12 and 3.13 CI matrix | Do not use end-of-life Python releases |
| Dependency consistency | pip check in CI | Investigate incompatible dependency sets |
| Regression assurance | Pytest matrix with strict deprecation warnings | Keep all jobs green before merge |
| Test evidence | JUnit XML uploaded as GitHub Actions artifacts | Download per-runtime reports from workflow runs |
| Container security | Non-root image, read-only data mounts, loopback port, dropped capabilities | Do not expose the demo app directly to the internet |
| Data provenance | Source SHA-256 and core/Phase 3 run manifests | Rebuild analytics after replacing source data |

## Repository settings still requiring an administrator

The GitHub main branch was not protected when this posture was reviewed. Workflow files do not turn on repository branch protection automatically. Configure a branch protection rule or repository ruleset for main with these settings:

1. Require pull requests before merging; require at least one approval when collaborators are available.
2. Require the successful status checks: Tests (Python 3.11), Tests (Python 3.12), Tests (Python 3.13), Docker build and dashboard health smoke test, and the CodeQL analysis job.
3. Require conversation resolution.
4. Block force pushes and deletion of main.
5. Restrict bypass permissions to repository administrators and explicitly designated release automation only.

Enable private vulnerability reporting in Settings → Code security and analysis. Confirm that code scanning alerts are enabled for the repository and that maintainers review alerts.

## Scope and limitations

These controls improve the repository's engineering posture but are not a formal security certification. The dashboard has no built-in user authentication or authorization. The UCI source data are historical and public, but real retail data may contain commercially sensitive or personal information; use a separate access-controlled deployment and data store before adapting the project to live customer data.
