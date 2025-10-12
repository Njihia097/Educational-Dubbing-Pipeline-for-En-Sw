# syntax=docker/dockerfile:1
FROM python:3.13.7-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY alembic.ini /app/alembic.ini
COPY . .



EXPOSE 5000
CMD flask db upgrade || echo "DB migration failed, continuing..." && flask run --host=0.0.0.0 --port=5000

