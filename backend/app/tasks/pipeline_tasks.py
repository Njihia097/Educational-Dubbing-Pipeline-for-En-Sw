"""
Celery tasks aligned with:
 - LocalDubbingPipeline (core.py)
 - external_ai/local_ai_server.py

These tasks:
  - Download video/audio from MinIO (S3-style)
  - Call external AI microservice endpoints
  - Work only with returned filesystem paths
  - Upload final output back to MinIO
"""

import os
import tempfile
from pathlib import Path

import requests
from celery import shared_task

# Correct MinIO utilities for your project
from app.utils.minio_downloader import download_minio_uri
from app.utils.minio_client import upload_file
from app.config import config


EXTERNAL_AI_URL = os.getenv("EXTERNAL_AI_URL", "http://host.docker.internal:7001")


# ============================================================================
# 1. ASR — video → audio.wav + text + timings
# ============================================================================
@shared_task(bind=True)
def task_asr(self, video_s3_uri: str):
    """
    Returns a payload dict that subsequent tasks enrich as the pipeline progresses.
    """
    local_video = download_minio_uri(video_s3_uri)

    with open(local_video, "rb") as fh:
        resp = requests.post(
            f"{EXTERNAL_AI_URL}/asr",
            files={"video": fh},
        )

    if resp.status_code != 200:
        raise Exception(f"ASR failed: {resp.text}")

    data = resp.json()
    return {
        "video_s3_uri": video_s3_uri,
        "text": data["text"],
        "start": data["start"],
        "end": data["end"],
        "wav_path": data["wav_path"],  # filesystem path inside external_ai
    }


# ============================================================================
# 2. Punctuation — raw text → list of sentences
# ============================================================================
@shared_task(bind=True)
def task_punctuate(self, payload: dict):
    raw_text = payload.get("text", "")
    resp = requests.post(
        f"{EXTERNAL_AI_URL}/punctuate",
        json={"text": raw_text},
    )

    if resp.status_code != 200:
        raise Exception(f"Punctuation failed: {resp.text}")

    payload["sentences"] = resp.json()["sentences"]
    return payload


# ============================================================================
# 3. Translate EN → SW
# ============================================================================
@shared_task(bind=True)
def task_translate(self, payload: dict):
    sentences = payload.get("sentences", [])
    resp = requests.post(
        f"{EXTERNAL_AI_URL}/mt",
        json={"sentences": sentences},
    )

    if resp.status_code != 200:
        raise Exception(f"Translation failed: {resp.text}")

    data = resp.json()
    payload["sw_sentences"] = data["sw_sentences"]
    payload["sw_text"] = data["sw_text"]
    return payload


# ============================================================================
# 4. TTS → Swahili WAV path
# ============================================================================
@shared_task(bind=True)
def task_tts(self, payload: dict):
    sentences = payload.get("sw_sentences") or []
    resp = requests.post(
        f"{EXTERNAL_AI_URL}/tts",
        json={"sw_sentences": sentences},
    )

    if resp.status_code != 200:
        raise Exception(f"TTS failed: {resp.text}")

    payload["tts_path"] = resp.json()["tts_path"]
    return payload


# ============================================================================
# 5. Separate background music (Demucs)
# ============================================================================
@shared_task(bind=True)
def task_separate_music(self, payload: dict):
    wav_path = payload.get("wav_path")
    resp = requests.post(
        f"{EXTERNAL_AI_URL}/separate_music",
        json={"wav_path": wav_path},
    )

    if resp.status_code != 200:
        raise Exception(f"Music separation failed: {resp.text}")

    payload["music_path"] = resp.json()["music_path"]
    return payload


# ============================================================================
# 6. Mix music + dubbed voice
# ============================================================================
@shared_task(bind=True)
def task_mix(self, payload: dict):
    music_path = payload.get("music_path")
    voice_path = payload.get("tts_path")
    resp = requests.post(
        f"{EXTERNAL_AI_URL}/mix",
        json={"music_path": music_path, "voice_path": voice_path},
    )

    if resp.status_code != 200:
        raise Exception(f"Mix failed: {resp.text}")

    payload["mixed_path"] = resp.json()["mixed_path"]
    return payload


# ============================================================================
# 7. Replace video audio
# ============================================================================
@shared_task(bind=True)
def task_replace_audio(self, payload: dict):
    video_s3_uri = payload.get("video_s3_uri")
    mixed_path = payload.get("mixed_path")
    local_video = download_minio_uri(video_s3_uri)

    with open(local_video, "rb") as fh:
        resp = requests.post(
            f"{EXTERNAL_AI_URL}/mux",
            files={"video": fh},
            data={"audio_path": mixed_path},
        )

    if resp.status_code != 200:
        raise Exception(f"Audio mux failed: {resp.text}")

    output_local = resp.json()["output_video"]

    download_resp = requests.get(
        f"{EXTERNAL_AI_URL}/files",
        params={"path": output_local},
        stream=True,
    )

    if download_resp.status_code != 200:
        raise Exception(f"Failed to download muxed video: {download_resp.text}")

    tmp_dir = Path(tempfile.gettempdir()) / "pipeline_outputs"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_file = tmp_dir / Path(output_local).name

    with open(tmp_file, "wb") as fh:
        for chunk in download_resp.iter_content(chunk_size=1024 * 1024):
            if chunk:
                fh.write(chunk)

    object_name = os.path.basename(output_local)

    s3_uri = upload_file(
        bucket=config.S3_BUCKET_OUTPUTS,
        object_name=object_name,
        file_path=str(tmp_file),
    )

    tmp_file.unlink(missing_ok=True)

    payload["output_s3_uri"] = s3_uri
    return payload
