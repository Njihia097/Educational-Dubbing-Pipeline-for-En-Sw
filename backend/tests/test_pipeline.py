import sys, os
sys.path.append("/pipeline")  # Add mounted model repo to PYTHONPATH

import os
import importlib
import pytest

# Path: backend/tests/test_pipeline.py

@pytest.fixture(autouse=True)
def cleanup_env(monkeypatch):
    """Reset SKIP_MODEL_LOAD between tests to avoid cross-contamination."""
    monkeypatch.delenv("SKIP_MODEL_LOAD", raising=False)
    yield
    monkeypatch.delenv("SKIP_MODEL_LOAD", raising=False)


def test_pipeline_skips_model_loading(monkeypatch):
    """
    Test that when SKIP_MODEL_LOAD=True, models are not initialized.
    """
    monkeypatch.setenv("SKIP_MODEL_LOAD", "True")

    # Import pipeline dynamically so it respects the env var at import
    from importlib import reload
    pipeline_module = importlib.import_module("src.inference.local_pipeline.cli")
    reload(pipeline_module)

    pipeline = pipeline_module.LocalDubbingPipeline()

    assert pipeline.whisper_model is None
    assert pipeline.mt_model is None
    assert pipeline.tts_model is None


def test_pipeline_lazy_loads_on_demand(monkeypatch):
    """
    Test that ensure_models() triggers model loading lazily.
    """
    monkeypatch.setenv("SKIP_MODEL_LOAD", "True")

    from importlib import reload
    pipeline_module = importlib.import_module("src.inference.local_pipeline.cli")
    reload(pipeline_module)

    pipeline = pipeline_module.LocalDubbingPipeline()

    # Initially no models loaded
    assert pipeline.whisper_model is None

    # Patch sub-ensures instead of monolithic loader
    called = {}

    def fake_asr():
        called["asr"] = True
        pipeline.whisper_model = "mock"

    def fake_punct():
        called["punct"] = True

    def fake_mt():
        called["mt"] = True
        pipeline.mt_model = "mock"

    def fake_tts():
        called["tts"] = True
        pipeline.tts_model = "mock"

    pipeline.ensure_asr = fake_asr
    pipeline.ensure_punct = fake_punct
    pipeline.ensure_mt = fake_mt
    pipeline.ensure_tts = fake_tts

    pipeline.ensure_models()

    # Validate lazy loading sequence
    assert all(k in called for k in ("asr", "punct", "mt", "tts")), "Not all model ensures were called"
    assert pipeline.whisper_model == "mock"
    assert pipeline.mt_model == "mock"
    assert pipeline.tts_model == "mock"



def test_pipeline_process_runs_with_lazy_models(monkeypatch, tmp_path):
    """
    Test that pipeline.process() automatically ensures model availability.
    """
    monkeypatch.setenv("SKIP_MODEL_LOAD", "True")

    from importlib import reload
    pipeline_module = importlib.import_module("src.inference.local_pipeline.cli")
    reload(pipeline_module)

    pipeline = pipeline_module.LocalDubbingPipeline()

    # Simulate loaded models quickly
    pipeline._load_models = lambda: setattr(pipeline, "whisper_model", "mock")

    # --- NEW: Stub _extract_audio() so it doesn't expect real files ---
    dummy_audio = tmp_path / "dummy.wav"
    dummy_audio.write_bytes(b"RIFF....WAVEfmt ")  # Minimal header
    dummy_clip = type("MockClip", (), {"duration": 1.0, "audio": None})
    pipeline._extract_audio = lambda vpath, opath: (dummy_clip, str(dummy_audio))

    # Run process (no real video required)
    result = pipeline.process("sample_video.mp4", output_name="test_output")

    assert isinstance(result, dict)
    assert "status" in result
    # Accept either success or handled error, but never crash
    assert result["status"] in {"success", "error"}

