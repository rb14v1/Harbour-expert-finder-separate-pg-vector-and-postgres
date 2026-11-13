FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN adduser --system --uid 10001 --group --no-create-home app \
    && chown -R app:app /app

EXPOSE 8000

USER app

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
