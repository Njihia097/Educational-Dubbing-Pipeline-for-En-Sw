# external_ai/local_ai_server.py

import logging
import os
import subprocess
import tempfile
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_file
import torch

# -----------------------------------------------------------------------------
# Lightweight .env loader
# -----------------------------------------------------------------------------
def load_local_env():
    env_path = Path(__file__).with_name(".env")
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        os.environ.setdefault(key, val)


load_local_env()

# -----------------------------------------------------------------------------
# Logging setup
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("local_ai_server")

# -----------------------------------------------------------------------------
# Device & model config
# -----------------------------------------------------------------------------
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
WHISPER_MODEL_NAME = os.getenv("WHISPER_MODEL_NAME", "small")

from pipeline_core_loader import get_pipeline  # noqa: E402

app = Flask(__name__)

# -----------------------------------------------------------------------------
# FFmpeg helper (rarely used; pipeline handles extraction itself)
# -----------------------------------------------------------------------------
def extract_audio_ffmpeg(input_path: str, output_path: str) -> str:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        output_path,
    ]
    logger.info("[ASR] Extracting audio via FFmpeg")
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_path


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.get("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "device": DEVICE,
            "whisper_model": WHISPER_MODEL_NAME,
        }
    ), 200


# -----------------------------------------------------------------------------
# (ASR, punctuation, MT, TTS, mix, mux unchanged)
# Entire sections preserved exactly as you shared
# -----------------------------------------------------------------------------
# [NO CHANGES TO THESE ROUTES — OMITTED HERE FOR BREVITY]
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# 8) FULL pipeline: single-call end-to-end dubbing
# -----------------------------------------------------------------------------
@app.post("/full")
def full_chain():
    """
    Accepts:
        multipart/form-data { video: file }

    Returns:
        {
            "status": "success",
            "english": "...",
            "swahili": "...",
            "output": "outputs/demo_videos/dubbed_abc123.mp4"
        }
    """

    if "video" not in request.files:
        return jsonify({"error": "Missing 'video'"}), 400

    video_file = request.files["video"]
    if video_file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    tmp_dir = Path(tempfile.gettempdir()) / "local_ai_full"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    tmp_id = uuid.uuid4().hex
    tmp_path = tmp_dir / f"{tmp_id}.mp4"

    try:
        # Save temp upload
        video_file.save(tmp_path)
        logger.info(f"[FULL] Running full pipeline → {tmp_path}")

        pipe = get_pipeline()
        result = pipe.process(str(tmp_path), output_name=f"full_{tmp_id}")

        if not isinstance(result, dict):
            return jsonify({"status": "error", "error": "Pipeline returned non-dict"}), 500

        # ------------------------------------------------------------------
        # Normalize output path
        # ------------------------------------------------------------------
        out_path = result.get("output")
        if not out_path:
            return jsonify({"status": "error", "error": "Pipeline returned no output file"}), 500

        # Convert backslashes → forward slashes
        out_path = out_path.replace("\\", "/")
        # Remove accidental leading slash
        out_path = out_path.lstrip("/")

        # ------------------------------------------------------------------
        # Extract timestamped segments from pipeline response
        # The pipeline now returns english_segments and swahili_segments directly
        # ------------------------------------------------------------------
        english_segments = result.get("english_segments", [])
        swahili_segments = result.get("swahili_segments", [])
        
        # Fallback: If segments not present (backward compatibility), try extracting from _block_timeline
        if not english_segments and hasattr(pipe, '_block_timeline') and pipe._block_timeline:
            blocks = pipe._block_timeline
            for block in blocks:
                en_text = block.get("text", "").strip()
                if en_text:
                    english_segments.append({
                        "text": en_text,
                        "start": float(block.get("start", 0.0)),
                        "end": float(block.get("end", 0.0))
                    })
        
        return jsonify(
            {
                "status": "success",
                "english": result.get("english", ""),
                "swahili": result.get("swahili", ""),
                "english_segments": english_segments,  # List of {text, start, end}
                "swahili_segments": swahili_segments,  # List of {text, start, end}
                "output": out_path,  # backend expects this
            }
        )

    except Exception as exc:
        logger.exception("[FULL] Error: %s", exc)
        return jsonify({"status": "error", "error": str(exc)}), 500

    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except:
            pass


# -----------------------------------------------------------------------------
# File download
# -----------------------------------------------------------------------------
@app.get("/files")
def download_file():
    rel_path = request.args.get("path")
    if not rel_path:
        return jsonify({"error": "Missing 'path'"}), 400

    file_path = Path(rel_path)
    if not file_path.is_absolute():
        file_path = Path.cwd() / file_path

    file_path = file_path.resolve()
    if not file_path.exists():
        return jsonify({"error": f"File not found: {file_path}"}), 404

    try:
        return send_file(file_path, as_attachment=True)
    except Exception as exc:
        logger.exception("[FILES] %s", exc)
        return jsonify({"error": str(exc)}), 500


# -----------------------------------------------------------------------------
# Main entry
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("EXTERNAL_AI_PORT", "7001"))
    logger.info(f"Starting Local AI Server on 0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port)
