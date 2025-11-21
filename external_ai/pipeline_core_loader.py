# external_ai/pipeline_core_loader.py
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger("pipeline_loader")

# ---------------------------------------------------------------------------
# 🔥 FIXED: FORCE REAL WINDOWS PATH — NO WSL, NO AUTO-CHDIR
# ---------------------------------------------------------------------------
# Replace this path with your real pipeline path.
# In your case it is EXACTLY here:
# C:\Users\hp omen 16\Projects\4.2\CSII\educational_dubbing_pipeline_tr
PIPELINE_ROOT = Path(
    r"C:\Users\hp omen 16\Projects\4.2\CSII\educational_dubbing_pipeline_tr"
).resolve()

if not PIPELINE_ROOT.exists():
    raise RuntimeError(f"Pipeline root does not exist: {PIPELINE_ROOT}")

# Add pipeline repo to Python import path
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

logger.info(f"📁 Using fixed pipeline root: {PIPELINE_ROOT}")

# IMPORTANT:
# ❌ Do NOT change directory
# ❌ Do NOT call os.chdir()
# These break Windows path resolution
# ---------------------------------------------------------------------------
# Import LocalDubbingPipeline from the pipeline
try:
    
    from src.inference.local_pipeline.core import LocalDubbingPipeline  # pyright: ignore[reportMissingImports]
except Exception as e:
    logger.error("❌ Failed to import LocalDubbingPipeline: %s", e)
    raise

# ---------------------------------------------------------------------------
# Singleton Loader
# ---------------------------------------------------------------------------
_PIPELINE = None

def get_pipeline() -> "LocalDubbingPipeline":
    """
    Return a single instance of LocalDubbingPipeline across the process.
    Heavy models (Whisper, NLLB, MMS-TTS) will only load once.
    """
    global _PIPELINE
    if _PIPELINE is None:
        logger.info("🔥 Instantiating LocalDubbingPipeline (once only)")
        _PIPELINE = LocalDubbingPipeline()
        logger.info("✅ LocalDubbingPipeline initialized")
    return _PIPELINE
