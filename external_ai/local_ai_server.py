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
# Lightweight local .env loader (no extra dependency needed)
# Looks for external_ai/.env and sets env vars if not already set.
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
        # Do not override existing env vars
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

# Import the real pipeline singleton
from pipeline_core_loader import get_pipeline  # noqa: E402

# Flask app
app = Flask(__name__)


# -----------------------------------------------------------------------------
# Helper: FFmpeg-based audio extraction, used only in this microservice
# (Most heavy lifting is delegated to LocalDubbingPipeline methods.)
# -----------------------------------------------------------------------------
def extract_audio_ffmpeg(input_path: str, output_path: str) -> str:
    """
    Extract 16 kHz mono PCM WAV from video using ffmpeg.
    This is used only when we want a totally standalone ASR endpoint.
    In most cases, we prefer LocalDubbingPipeline._extract_audio.
    """
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
    logger.info("[ASR] Extracting audio via FFmpeg from %s", input_path)
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    logger.info("[ASR] Extracted audio via FFmpeg -> %s", output_path)
    return output_path


# -----------------------------------------------------------------------------
# Routes
# -----------------------------------------------------------------------------
@app.get("/health")
def health():
    """
    Simple liveness + basic device check.
    Does *not* force-load the heavy pipeline models.
    """
    return jsonify(
        {
            "status": "ok",
            "device": DEVICE,
            "whisper_model": WHISPER_MODEL_NAME,
        }
    ), 200


# ─────────────────────────────────────────────────────────────
# 1) ASR: video → wav → transcription (+ timings)
# ─────────────────────────────────────────────────────────────
@app.post("/asr")
def asr_from_video():
    """
    Accepts multipart/form-data:

      - video: file (mp4/mkv/etc.)

    Returns JSON:
      {
        "text": str,
        "start": float,
        "end": float,
        "wav_path": str   # path on external_ai / pipeline filesystem
      }

    This uses your real LocalDubbingPipeline._extract_audio + _transcribe,
    and stores audio under data/processed/asr/...
    """
    if "video" not in request.files:
        return jsonify({"error": "Missing 'video' file field"}), 400

    video_file = request.files["video"]
    if video_file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    # Save video to a temp location (under system temp)
    tmp_dir = Path(tempfile.gettempdir()) / "local_ai_asr"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    tmp_id = uuid.uuid4().hex
    tmp_video_path = tmp_dir / f"{tmp_id}.mp4"

    try:
        video_file.save(tmp_video_path)
        logger.info("[ASR] Saved temp video to %s", tmp_video_path)

        # Use the real pipeline
        pipe = get_pipeline()

        # Use pipeline's own extract helper, but with a unique wav per request
        wav_out = Path("data/processed/asr") / f"asr_{tmp_id}.wav"
        wav_out.parent.mkdir(parents=True, exist_ok=True)

        clip, wav_path = pipe._extract_audio(str(tmp_video_path), str(wav_out))
        logger.info("[ASR] Extracted audio → %s", wav_path)

        text, start, end = pipe._transcribe(wav_path)
        logger.info("[ASR] Transcription done (len=%d chars)", len(text))

        return jsonify(
            {
                "text": text,
                "start": float(start),
                "end": float(end),
                "wav_path": wav_path,
            }
        )

    except Exception as exc:
        logger.exception("[ASR] Error during ASR: %s", exc)
        return jsonify({"error": str(exc)}), 500

    finally:
        try:
            if tmp_video_path.exists():
                tmp_video_path.unlink()
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────
# 2) Punctuation: raw text → sentence list
# ─────────────────────────────────────────────────────────────
@app.post("/punctuate")
def punctuate():
    """
    Accepts JSON:
      { "text": "raw ASR text ..." }

    Returns JSON:
      { "sentences": [ "...", "..." ] }
    """
    data = request.get_json(silent=True) or {}
    raw_text = data.get("text", "")

    if not isinstance(raw_text, str) or not raw_text.strip():
        return jsonify({"error": "Field 'text' must be a non-empty string"}), 400

    try:
        pipe = get_pipeline()
        sentences = pipe._restore_punctuation(raw_text)
        return jsonify({"sentences": sentences})
    except Exception as exc:
        logger.exception("[PUNCT] Error restoring punctuation: %s", exc)
        return jsonify({"error": str(exc)}), 500


# ─────────────────────────────────────────────────────────────
# 3) MT: English → Swahili (sentences OR full text)
# ─────────────────────────────────────────────────────────────
@app.post("/mt")
def translate():
    """
    Accepts JSON:
      { "sentences": ["...", "..."] }
        OR
      { "text": "full english text" }

    Returns JSON:
      {
        "sw_text": "full swahili text",
        "sw_sentences": ["...", "..."]
      }
    """
    data = request.get_json(silent=True) or {}
    sentences = data.get("sentences")
    text = data.get("text")

    if sentences is None and text is None:
        return jsonify({"error": "Provide either 'sentences' (list) or 'text' (str)"}), 400

    try:
        pipe = get_pipeline()
        if isinstance(sentences, list):
            sw_sentences = pipe._translate_sentences(sentences)
            sw_text = " ".join(sw_sentences)
        else:
            sw_text = pipe._translate(text)
            sw_sentences = [sw_text]

        return jsonify(
            {
                "sw_text": sw_text,
                "sw_sentences": sw_sentences,
            }
        )
    except Exception as exc:
        logger.exception("[MT] Translation error: %s", exc)
        return jsonify({"error": str(exc)}), 500


# ─────────────────────────────────────────────────────────────
# 4) TTS: Swahili text/sentences → WAV path
# ─────────────────────────────────────────────────────────────
@app.post("/tts")
def tts():
    """
    Accepts JSON:
      { "sw_sentences": ["...", "..."] }
        OR
      { "sw_text": "full swahili text" }

    Returns JSON:
      { "tts_path": "data/processed/tts/tts_<id>.wav" }

    The path is on the external_ai/pipeline filesystem and will be used
    by later /mix or /mux calls.
    """
    data = request.get_json(silent=True) or {}
    sw_sentences = data.get("sw_sentences")
    sw_text = data.get("sw_text")

    if sw_sentences is None and sw_text is None:
        return jsonify({"error": "Provide either 'sw_sentences' (list) or 'sw_text' (str)"}), 400

    tmp_id = uuid.uuid4().hex
    out_wav = Path("data/processed/tts") / f"tts_{tmp_id}.wav"
    out_wav.parent.mkdir(parents=True, exist_ok=True)

    try:
        pipe = get_pipeline()
        if isinstance(sw_sentences, list):
            pipe._tts_segments(sw_sentences, str(out_wav))
        else:
            pipe._tts(sw_text, str(out_wav))

        logger.info("[TTS] Synthesized audio → %s", out_wav)
        return jsonify({"tts_path": str(out_wav)})

    except Exception as exc:
        logger.exception("[TTS] Error during TTS: %s", exc)
        return jsonify({"error": str(exc)}), 500


# ─────────────────────────────────────────────────────────────
# 5) Demucs: separate music track from a WAV
# ─────────────────────────────────────────────────────────────
@app.post("/separate_music")
def separate_music():
    """
    Accepts JSON:
      { "wav_path": "data/processed/asr/asr_<id>.wav" }

    Returns JSON:
      { "music_path": "data/processed/asr/demucs_out/.../no_vocals.wav" }
    """
    data = request.get_json(silent=True) or {}
    wav_path = data.get("wav_path")

    if not isinstance(wav_path, str) or not wav_path.strip():
        return jsonify({"error": "Field 'wav_path' must be a non-empty string"}), 400

    try:
        pipe = get_pipeline()
        music_path = pipe._separate_music(wav_path, out_dir="data/processed/asr/demucs_out")
        logger.info("[DEMUX] Music stem: %s", music_path)
        return jsonify({"music_path": music_path})
    except Exception as exc:
        logger.exception("[DEMUX] Error separating music: %s", exc)
        return jsonify({"error": str(exc)}), 500


# ─────────────────────────────────────────────────────────────
# 6) Mix: music + voice ⇒ mixed WAV
# ─────────────────────────────────────────────────────────────
@app.post("/mix")
def mix_music_and_voice():
    """
    Accepts JSON:
      {
        "music_path": "path/to/music.wav",
        "voice_path": "path/to/voice.wav"
      }

    Returns JSON:
      { "mixed_path": "data/processed/tts/mixed_<id>.wav" }
    """
    data = request.get_json(silent=True) or {}
    music_path = data.get("music_path")
    voice_path = data.get("voice_path")

    if not music_path or not voice_path:
        return jsonify({"error": "Fields 'music_path' and 'voice_path' are required"}), 400

    tmp_id = uuid.uuid4().hex
    out_wav = Path("data/processed/tts") / f"mixed_{tmp_id}.wav"
    out_wav.parent.mkdir(parents=True, exist_ok=True)

    try:
        pipe = get_pipeline()
        mixed = pipe._mix_music_and_voice(music_path, voice_path, str(out_wav))
        logger.info("[MIX] Mixed audio → %s", mixed)
        return jsonify({"mixed_path": mixed})
    except Exception as exc:
        logger.exception("[MIX] Error mixing: %s", exc)
        return jsonify({"error": str(exc)}), 500


# ─────────────────────────────────────────────────────────────
# 7) Mux: replace video audio with given WAV
# ─────────────────────────────────────────────────────────────
@app.post("/mux")
def mux_video():
    """
    Accepts multipart/form-data:

      - video: file (mp4/mkv/etc.)  → original source video
      - audio_path: text field      → path to WAV produced by /mix or /tts

    Returns JSON:
      { "output_video": "outputs/demo_videos/dubbed_<id>.mp4" }
    """
    if "video" not in request.files:
        return jsonify({"error": "Missing 'video' file field"}), 400

    audio_path = request.form.get("audio_path")
    if not audio_path:
        return jsonify({"error": "Missing 'audio_path' form field"}), 400

    video_file = request.files["video"]
    if video_file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    tmp_dir = Path(tempfile.gettempdir()) / "local_ai_mux"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    tmp_id = uuid.uuid4().hex
    tmp_video_path = tmp_dir / f"{tmp_id}.mp4"
    tmp_wav = Path("data/processed/asr") / f"mux_{tmp_id}.wav"
    tmp_wav.parent.mkdir(parents=True, exist_ok=True)

    out_video = Path("outputs/demo_videos") / f"dubbed_{tmp_id}.mp4"
    out_video.parent.mkdir(parents=True, exist_ok=True)

    try:
        video_file.save(tmp_video_path)
        logger.info("[MUX] Saved temp video to %s", tmp_video_path)

        pipe = get_pipeline()
        # Reuse _extract_audio only to get a VideoFileClip object
        clip, _ = pipe._extract_audio(str(tmp_video_path), str(tmp_wav))

        # Replace audio with the provided WAV
        pipe._replace_audio(clip, audio_path, str(out_video))
        logger.info("[MUX] Wrote output video → %s", out_video)

        return jsonify({"output_video": str(out_video)})

    except Exception as exc:
        logger.exception("[MUX] Error muxing video: %s", exc)
        return jsonify({"error": str(exc)}), 500

    finally:
        for p in (tmp_video_path, tmp_wav):
            try:
                if p.exists():
                    p.unlink()
            except Exception:
                pass


# -----------------------------------------------------------------------------
# 9) File download helper for backend (allows uploading final outputs to MinIO)
# -----------------------------------------------------------------------------
@app.get("/files")
def download_file():
    rel_path = request.args.get("path")
    if not rel_path:
        return jsonify({"error": "Missing 'path' parameter"}), 400

    file_path = Path(rel_path)
    if not file_path.is_absolute():
        file_path = Path.cwd() / file_path

    file_path = file_path.resolve()
    if not file_path.exists():
        return jsonify({"error": f"File not found: {file_path}"}), 404

    try:
        return send_file(file_path, as_attachment=True)
    except Exception as exc:
        logger.exception("[FILES] Error serving %s: %s", file_path, exc)
        return jsonify({"error": str(exc)}), 500


# ─────────────────────────────────────────────────────────────
# 8) Optional: full-chain endpoint using pipe.process()
#     (for debugging / manual runs)
# ─────────────────────────────────────────────────────────────
@app.post("/full")
def full_chain():
    """
    Accepts multipart/form-data:

      - video: file

    Runs the full LocalDubbingPipeline.process() as-is and returns
    the same dict it returns (status, english, swahili, output path, etc.)
    """
    if "video" not in request.files:
        return jsonify({"error": "Missing 'video' file field"}), 400

    video_file = request.files["video"]
    if video_file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    tmp_dir = Path(tempfile.gettempdir()) / "local_ai_full"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    tmp_id = uuid.uuid4().hex
    tmp_video_path = tmp_dir / f"{tmp_id}.mp4"

    try:
        video_file.save(tmp_video_path)
        logger.info("[FULL] Saved temp video to %s", tmp_video_path)

        pipe = get_pipeline()
        result = pipe.process(str(tmp_video_path), output_name=f"full_{tmp_id}")
        logger.info("[FULL] Pipeline result: %s", result.get("status"))

        return jsonify(result)

    except Exception as exc:
        logger.exception("[FULL] Error in full-chain call: %s", exc)
        return jsonify({"status": "error", "error": str(exc), "pipeline": "local"}), 500

    finally:
        try:
            if tmp_video_path.exists():
                tmp_video_path.unlink()
        except Exception:
            pass


# -----------------------------------------------------------------------------
# Main entry
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("EXTERNAL_AI_PORT", "7001"))
    logger.info("Starting Local AI Server on http://0.0.0.0:%d (device=%s)", port, DEVICE)
    app.run(host="0.0.0.0", port=port)
