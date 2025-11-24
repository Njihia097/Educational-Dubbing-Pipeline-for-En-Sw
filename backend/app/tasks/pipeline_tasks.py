"""
Celery tasks aligned with external_ai microservice.

Everything heavy (ASR, MT, TTS, Demucs, Muxing) runs in external_ai.
This worker:
  - downloads files from MinIO
  - calls external_ai endpoints
  - uploads final outputs
  - updates JobStep state via progress_tracker
"""

import os
import tempfile
from pathlib import Path

import requests
from celery import shared_task

from app.utils.minio_downloader import download_minio_uri
from app.utils.minio_client import upload_file
from app.config import config
from app.tasks.progress_tracker import pipeline_step


EXTERNAL_AI_URL = os.getenv("EXTERNAL_AI_URL", "http://host.docker.internal:7001")


# ============================================================================
# 🔄 NEW: Single full-chain local dubbing task (Option A)
# ============================================================================
@shared_task(bind=True)
@pipeline_step("asr")
def task_full_chain(self, video_s3_uri: str):
    """
    Single-call pipeline:
      1) Download source video from MinIO
      2) POST to external_ai /full
      3) Download the produced dubbed video via /files
      4) Upload final video to MinIO outputs bucket
      5) Return payload with output_s3_uri (and transcripts)
    """

    # 1) Download source video from MinIO
    local_video = download_minio_uri(video_s3_uri)

    # 2) Call external_ai /full with the video file
    with open(local_video, "rb") as fh:
        resp = requests.post(
            f"{EXTERNAL_AI_URL}/full",
            files={"video": fh},
        )

    if resp.status_code != 200:
        raise Exception(f"/full pipeline failed: {resp.text}")

    data = resp.json()
    if data.get("status") != "success":
        raise Exception(f"/full pipeline returned error: {data}")

    # Local path (on external_ai machine) to the dubbed video
    output_local = data.get("output")
    if not output_local:
        raise Exception(f"/full did not return 'output' path: {data}")

    # 3) Download the dubbed video from external_ai via /files
    download_resp = requests.get(
        f"{EXTERNAL_AI_URL}/files",
        params={"path": output_local},
        stream=True,
    )

    if download_resp.status_code != 200:
        raise Exception(f"Failed to download dubbed video: {download_resp.text}")

    tmp_dir = Path(tempfile.gettempdir()) / "pipeline_outputs_full"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_file = tmp_dir / Path(output_local).name

    with open(tmp_file, "wb") as fh:
        for chunk in download_resp.iter_content(1024 * 1024):
            if chunk:
                fh.write(chunk)

    # 4) Normalize path & upload to MinIO (same pattern as old replace_audio)
    # Fix Windows slashes and remove any bucket prefix to avoid duplication
    clean = output_local.replace("\\", "/").lstrip("/")
    
    # Remove any leading "outputs/" prefix since we're uploading to the outputs bucket
    # This prevents paths like "outputs/demo_videos/..." from becoming "outputs/outputs/demo_videos/..."
    if clean.startswith("outputs/"):
        clean = clean[len("outputs/"):]
    
    # Ensure the path doesn't have leading slashes
    clean = clean.lstrip("/")
    
    object_name = clean


    s3_uri = upload_file(
        bucket=config.S3_BUCKET_OUTPUTS,
        object_name=object_name,
        file_path=str(tmp_file),
    )

    tmp_file.unlink(missing_ok=True)

    # 5) Build payload forwarded into _finalize_job
    # Include both plain text and timestamped segments, plus pipeline metrics
    payload = {
        "video_s3_uri": video_s3_uri,
        "output_s3_uri": s3_uri,
        "english": data.get("english", ""),
        "swahili": data.get("swahili", ""),
        "english_segments": data.get("english_segments", []),
        "swahili_segments": data.get("swahili_segments", []),
        "pipeline_metrics": data.get("pipeline_metrics"),  # Optional: ASR confidence, model versions, processing time, etc.
    }
    return payload


# ============================================================================
# LEGACY MULTI-STAGE TASKS (kept for compatibility / future use)
#   NOTE: run_chain() no longer uses these; they remain here so nothing else
#   breaks if you still call them manually.
# ============================================================================

@shared_task(bind=True)
@pipeline_step("asr")
def task_asr(self, video_s3_uri: str):

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
        "wav_path": data["wav_path"],
    }


@shared_task(bind=True)
@pipeline_step("punctuate")
def task_punctuate(self, payload: dict):

    resp = requests.post(
        f"{EXTERNAL_AI_URL}/punctuate",
        json={"text": payload.get("text", "")},
    )

    if resp.status_code != 200:
        raise Exception(f"Punctuation failed: {resp.text}")

    payload["sentences"] = resp.json()["sentences"]
    return payload


@shared_task(bind=True)
@pipeline_step("translate")
def task_translate(self, payload: dict):

    resp = requests.post(
        f"{EXTERNAL_AI_URL}/mt",
        json={"sentences": payload.get("sentences", [])},
    )

    if resp.status_code != 200:
        raise Exception(f"Translation failed: {resp.text}")

    data = resp.json()
    payload["sw_sentences"] = data["sw_sentences"]
    payload["sw_text"] = data["sw_text"]
    return payload


@shared_task(bind=True)
@pipeline_step("tts")
def task_tts(self, payload: dict):

    resp = requests.post(
        f"{EXTERNAL_AI_URL}/tts",
        json={"sw_sentences": payload.get("sw_sentences", [])},
    )

    if resp.status_code != 200:
        raise Exception(f"TTS failed: {resp.text}")

    payload["tts_path"] = resp.json()["tts_path"]
    return payload


@shared_task(bind=True)
@pipeline_step("separate_music")
def task_separate_music(self, payload: dict):

    resp = requests.post(
        f"{EXTERNAL_AI_URL}/separate_music",
        json={"wav_path": payload.get("wav_path")},
    )

    if resp.status_code != 200:
        raise Exception(f"Music separation failed: {resp.text}")

    payload["music_path"] = resp.json()["music_path"]
    return payload


@shared_task(bind=True)
@pipeline_step("mix")
def task_mix(self, payload: dict):

    resp = requests.post(
        f"{EXTERNAL_AI_URL}/mix",
        json={
            "music_path": payload.get("music_path"),
            "voice_path": payload.get("tts_path"),
        },
    )

    if resp.status_code != 200:
        raise Exception(f"Mix failed: {resp.text}")

    payload["mixed_path"] = resp.json()["mixed_path"]
    return payload


@shared_task(bind=True)
@pipeline_step("replace_audio")
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

    # Download muxed final file
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
        for chunk in download_resp.iter_content(1024 * 1024):
            if chunk:
                fh.write(chunk)

    # --- FIX: Normalize path from external_ai ---
    clean = output_local.replace("\\", "/")            # fix Windows separators
    clean = clean.replace("outputs/", "")              # remove accidental prefix
    clean = clean.lstrip("/")                          # ensure no leading slash

    # Expected final structure:
    # demo_videos/dubbed_<id>.mp4
    if not clean.startswith("demo_videos/"):
        clean = "demo_videos/" + clean

    object_name = clean

    # Upload to MinIO
    s3_uri = upload_file(
        bucket=config.S3_BUCKET_OUTPUTS,
        object_name=object_name,
        file_path=str(tmp_file),
    )

    tmp_file.unlink(missing_ok=True)

    payload["output_s3_uri"] = s3_uri
    return payload
