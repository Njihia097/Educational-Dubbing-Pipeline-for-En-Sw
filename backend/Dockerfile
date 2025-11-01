# syntax=docker/dockerfile:1
FROM python:3.13.7-slim

WORKDIR /app

# System dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpq-dev \
        gcc \
        curl \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY alembic.ini /app/alembic.ini
COPY . .

RUN adduser --disabled-password --gecos '' appuser && chown -R appuser /app
USER appuser


# Ensure entrypoint is executable
RUN chmod +x /app/entrypoint.sh



EXPOSE 5000

# Use entrypoint which waits for deps, migrates, then runs the app
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]


