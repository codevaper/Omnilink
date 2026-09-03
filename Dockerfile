FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ARG SERVICE
ENV SERVICE=${SERVICE}

CMD sh -c 'exec gunicorn \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers ${WEB_CONCURRENCY:-2} \
    --timeout ${GUNICORN_TIMEOUT:-120} \
    services.${SERVICE}.app:app'