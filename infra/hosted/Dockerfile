# The hosted observatory (oddsky.hosted) on Cloud Run. Built by infra/hosted/deploy.sh with Cloud Build.
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 ODDSKY_HOME=/app ODDSKY_CACHE=/tmp/oddsky-cache ODDSKY_WORKSPACES=/tmp/oddsky-ws MPLBACKEND=Agg
WORKDIR /app
RUN pip install uv
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN uv pip install --system ".[hosted,asassn]"
COPY cases ./cases
EXPOSE 8080
CMD ["sh", "-c", "uvicorn oddsky.hosted.app:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers --forwarded-allow-ips='*' --timeout-keep-alive 75"]
