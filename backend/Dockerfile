# syntax=docker/dockerfile:1
FROM python:3.13.7-slim

WORKDIR /app

# ─────────────────────────────────────────────────────────────
# 1️⃣ Environment variables for model/data caches
# ─────────────────────────────────────────────────────────────
# Use /tmp for writable caches even under non-root user
ENV HF_HOME=/tmp/hf_cache/huggingface \
    HF_HUB_CACHE=/tmp/hf_cache/huggingface \
    TORCH_HOME=/tmp/hf_cache/torch \
    TRANSFORMERS_CACHE=/tmp/hf_cache/huggingface/transformers \
    NLTK_DATA=/tmp/nltk_data \
    XDG_CACHE_HOME=/tmp/.cache \
    PYTHONPATH="/app:/pipeline:${PYTHONPATH}" \
    PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

# ─────────────────────────────────────────────────────────────
# 2️⃣ Create cache directories and fix permissions
# ─────────────────────────────────────────────────────────────
RUN mkdir -p /tmp/hf_cache /tmp/nltk_data /tmp/.cache && \
    chmod -R 777 /tmp/hf_cache /tmp/nltk_data /tmp/.cache

# ─────────────────────────────────────────────────────────────
# 3️⃣ System dependencies (moviepy, whisper, demucs, soundfile)
# ─────────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libsndfile1 git curl gcc postgresql-client \
 && rm -rf /var/lib/apt/lists/*

# ─────────────────────────────────────────────────────────────
# 4️⃣ CUDA PyTorch wheels (GPU build)
# ─────────────────────────────────────────────────────────────
# Keep torch/vision/audio OUT of requirements.txt
RUN pip install --no-cache-dir \
    torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 \
    --index-url https://download.pytorch.org/whl/cu124

# ─────────────────────────────────────────────────────────────
# 5️⃣ Core model libs (Transformers / Accelerate / PEFT)
# ─────────────────────────────────────────────────────────────
RUN pip install --no-cache-dir \
    transformers==4.45.2 accelerate==0.34.2 sentencepiece
RUN pip install --no-cache-dir peft==0.17.1

# ─────────────────────────────────────────────────────────────
# 6️⃣ Application requirements
# ─────────────────────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ─────────────────────────────────────────────────────────────
# 7️⃣ Copy application code and entrypoint
# ─────────────────────────────────────────────────────────────
COPY alembic.ini /app/alembic.ini
COPY entrypoint.sh /app/entrypoint.sh
COPY . .

RUN chmod x /app/entrypoint.sh

# ─────────────────────────────────────────────────────────────
# 8️⃣ Create non-root user for safer runtime
# ─────────────────────────────────────────────────────────────
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser /app /tmp/hf_cache /tmp/nltk_data /tmp/.cache

USER appuser
EXPOSE 5000

# ─────────────────────────────────────────────────────────────
# 9️⃣ Default HuggingFace settings to avoid root permission issues
# ─────────────────────────────────────────────────────────────
ENV HF_HOME=/tmp/hf_cache/huggingface
ENV HF_HUB_CACHE=/tmp/hf_cache/huggingface

# Default to prod in containers; compose can override for dev/CI
ENV FLASK_ENV=production FLASK_DEBUG=0


ENTRYPOINT ["/app/entrypoint.sh"]
