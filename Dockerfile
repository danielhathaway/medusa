FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt requirements-docker.txt ./
RUN pip install --no-cache-dir -r requirements-docker.txt \
    && groupadd --gid 10001 medusa \
    && useradd --uid 10001 --gid medusa --create-home medusa \
    && mkdir /app/modules \
    && chown medusa:medusa /app/modules

COPY medusa.py medusa.conf ./
COPY templates/ ./templates/
COPY static/ ./static/

USER medusa
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=3).close()"

# Threads keep the UI responsive while scripts run beyond the worker timeout.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4", "--access-logfile", "-", "--error-logfile", "-", "medusa:app"]
