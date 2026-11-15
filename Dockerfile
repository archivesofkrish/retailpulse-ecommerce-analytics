FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

# Install only runtime dependencies declared in pyproject.toml.
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN python -m pip install --no-cache-dir .

# Copy only the application and the deliberately small synthetic fallback sample.
COPY dashboard/ ./dashboard/
COPY data/sample/ ./data/sample/

RUN mkdir -p data/raw data/processed reports/phase3 \
    && groupadd --system retailpulse \
    && useradd --system --create-home --gid retailpulse --uid 10001 retailpulse \
    && chown -R retailpulse:retailpulse /app

USER retailpulse

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3)" || exit 1

CMD ["streamlit", "run", "dashboard/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
