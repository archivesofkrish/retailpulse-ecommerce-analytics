# RetailPulse container deployment

## Deployment model

The Docker image runs the Streamlit dashboard as a non-root user. It contains application code, runtime Python dependencies and the small synthetic demonstration dataset. It deliberately does **not** contain the UCI workbook, generated transaction exports, customer-level files or Phase 3 reports.

The recommended workflow is to generate analytics on a trusted host or data-processing job, then mount the source workbook and required derived outputs read-only into the dashboard container. This separates data processing from presentation and avoids baking data into the image.

## Prerequisites

- Docker Engine with the Compose plugin.
- The repository checked out locally.
- Python 3.10+ on the host if you intend to run the analytics pipeline outside Docker.

## Build the analytical outputs

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

mkdir -p data/raw data/processed reports/phase3
python scripts/download_data.py
python scripts/run_analysis.py
python scripts/validate_real_data.py
python scripts/run_phase3_analysis.py
```

The full UCI workbook remains in `data/raw/` and generated outputs remain in `data/processed/` and `reports/phase3/`. These locations are excluded from the Docker build context and are mounted read-only at runtime.

To run with the included synthetic sample, omit the download step. The dashboard will identify this as DEMO MODE. A synthetic sample is suitable for smoke testing and interface exploration, not for presenting the UCI findings or asserting a meaningful inactivity-model result.

## Start the dashboard

```bash
docker compose up --build -d
docker compose ps
docker compose logs -f retailpulse
```

Open [http://localhost:8501](http://localhost:8501). The default Compose port binding is restricted to loopback (127.0.0.1).

Stop the service with:

```bash
docker compose down
```

Rebuild after application changes with:

```bash
docker compose up --build -d
```

## Health and runtime behaviour

The image includes a Docker health check against Streamlit's `/_stcore/health` endpoint. GitHub Actions builds the image, starts the dashboard, and verifies that endpoint as a separate CI job. The image runs as the unprivileged `retailpulse` user and Compose drops Linux capabilities and enables `no-new-privileges`.

The raw workbook, core exports and Phase 3 outputs are mounted read-only. Run ingestion and analytics before starting or refreshing the dashboard. If the source workbook changes, rebuild the core and Phase 3 outputs using the commands above; provenance checks keep stale Phase 3 panels disabled. The source's absolute path may differ between the host and container. Freshness is verified using file size, modification signature and the SHA-256 content digest; the dashboard caches the digest against the file signature to avoid rehashing on every UI interaction.

## Security considerations

- Do not add the UCI workbook, customer-level exports, secrets or local environment files to the image.
- Keep the default localhost-only binding for local use.
- Streamlit in this project does not implement application user authentication or role-based access control. Do not expose port 8501 directly to the public internet. For remote or multi-user deployments, place the service behind an appropriately configured TLS reverse proxy and authentication/authorization layer.
- Restrict access to the host directories containing source and processed data.
- Keep Docker Engine, the base image and Python dependencies patched; rebuild the image when dependencies or source code change.
- Use a separate private data store and access controls before adapting the case study to real customer data.

## Troubleshooting

**Dashboard is in DEMO MODE:** the mounted `data/raw/` directory does not contain `online_retail_II.xlsx`. Download the UCI workbook and rebuild the analytical outputs.

**Advanced panels are unavailable:** check `data/processed/pipeline_manifest.json` and `reports/phase3/phase3_manifest.json`. Run the core pipeline followed by Phase 3. The dashboard intentionally refuses stale or incomplete advanced outputs.

**Port 8501 is already in use:** change the host side of the Compose mapping, for example `127.0.0.1:8502:8501`, then open `http://localhost:8502`.

**Container reports unhealthy:** inspect `docker compose logs retailpulse` and confirm the application can read the mounted data folders.
