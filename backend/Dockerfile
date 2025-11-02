# syntax=docker/dockerfile:1
FROM python:3.13.7-slim

WORKDIR /app

# System deps: ffmpeg (moviepy/whisper), libsndfile (soundfile), git (hf),
# and build basics
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libsndfile1 git curl gcc \
 && rm -rf /var/lib/apt/lists/*

# --- Install CUDA PyTorch wheels first (GPU build) ---
# IMPORTANT: keep torch/vision/audio OUT of requirements.txt
RUN pip install --no-cache-dir \
    torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 \
    --index-url https://download.pytorch.org/whl/cu124

# --- Install Transformers + Accelerate before PEFT ---
RUN pip install --no-cache-dir \
    transformers==4.45.2 accelerate==0.34.2 sentencepiece

# --- Install PEFT now (after torch + transformers) ---
RUN pip install --no-cache-dir peft==0.17.1

# --- Install remaining lightweight packages ---
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY alembic.ini /app/alembic.ini
COPY . .

# Install PostgreSQL client for pg_isready health-check
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user and set ownership
RUN adduser --disabled-password --gecos '' appuser && chown -R appuser /app

# Copy entrypoint and mark executable
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

USER appuser
EXPOSE 5000

ENV PYTHONPATH="/app:/pipeline:${PYTHONPATH}"


ENTRYPOINT ["/app/entrypoint.sh"]
