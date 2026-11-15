# Publishing RetailPulse to GitHub

This release package is prepared for publication, but it has **not** been pushed to GitHub. Review the repository contents locally before making it public.

## 1. Create an empty GitHub repository

Create a new repository named `RetailPulse` under your GitHub account. Do not initialise it with a README, licence or `.gitignore`, because those files are already included here.

## 2. Initialise and inspect locally

From the project root:

```bash
git init
git branch -M main
git status --short
```

Check that the status does **not** include:

- `data/raw/online_retail_II.xlsx`
- files under `data/processed/`
- `reports/phase3/*.csv` or `reports/phase3/*.json`
- `.venv/`, `.env`, API keys or credentials
- `test-results/real_data_validation.json`

The `.gitignore` excludes these generated/local files. Do not force-add them.

## 3. Commit the release

```bash
git add .
git status --short
git commit -m "Release RetailPulse Professional Edition v1.0.0"
```

Review the staged file list before committing. The source workbook is separately licensed and deliberately not included.

## 4. Connect and push

Replace the placeholder with your repository URL:

```bash
git remote add origin https://github.com/<your-account>/RetailPulse.git
git push -u origin main
```

## 5. Verify GitHub Actions

After the push, open the repository's **Actions** tab. The `RetailPulse CI` workflow should compile Python sources and run pytest with deprecation warnings treated as errors.

## 6. Publish a GitHub release

After CI passes, create a GitHub Release tagged `v1.0.0`, using `RELEASE_NOTES.md` as the release description. Attach the executive presentation if desired; do not attach the raw UCI workbook or customer-level generated extracts.

## 7. Suggested repository description

> End-to-end e-commerce business intelligence using UCI Online Retail II: Python, SQL/DuckDB, RFM segmentation, cohort activity, revenue concentration, historical inactivity backtesting and a Streamlit dashboard.

## 8. Before sharing publicly

- Confirm the UCI dataset attribution and CC BY 4.0 note remain visible.
- Confirm all six dashboard tabs are generated and usable after following the README.
- Check that no local user information, absolute machine paths, credentials or raw datasets were committed.
- Be explicit that the data is historical (2009–2011) and the inactivity model is not a live churn predictor.
