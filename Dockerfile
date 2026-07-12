# QuantRadar path-C product shell (stdlib Python, no heavy deps)
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8765 \
    QUANTRADAR_MODE=artifact

COPY app ./app
COPY static ./static
COPY fixtures ./fixtures
COPY schemas ./schemas
COPY scripts ./scripts

# Non-root
RUN useradd -m -u 10001 qr && chown -R qr:qr /app
USER qr

EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/health', timeout=3)"

CMD ["python", "-m", "app"]
