FROM python:3.14-slim AS builder

WORKDIR /app
COPY pyproject.toml .
COPY src/ src/
COPY app.py .
COPY pages/ pages/
COPY .streamlit/ .streamlit/

RUN pip install --no-cache-dir .

FROM python:3.14-slim

RUN useradd -m -r appuser
WORKDIR /app

COPY --from=builder /usr/local/lib/python3.14/site-packages /usr/local/lib/python3.14/site-packages
COPY --from=builder /usr/local/bin/streamlit /usr/local/bin/streamlit
COPY --from=builder /app/ .

RUN mkdir -p data/outputs data/uploads && chown -R appuser:appuser /app
USER appuser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"

ENTRYPOINT ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
