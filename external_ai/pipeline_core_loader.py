# external_ai/pipeline_core_loader.py

import logging
import sys
from pathlib import Path

logger = logging.getLogger("pipeline_loader")

# -----------------------------------------------------------------------------
# Fixed absolute pipeline root
# -----------------------------------------------------------------------------
PIPELINE_ROOT = Path(
    r"C:\Users\hp omen 16\Projects\4.2\CSII\educational_dubbing_pipeline_tr"
).resolve()

if not PIPELINE_ROOT.exists():
    raise RuntimeError(f"Pipeline root does not exist: {PIPELINE_ROOT}")

# Add root to module import path
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

logger.info(f"📁 Using pipeline root: {PIPELINE_ROOT}")

# -----------------------------------------------------------------------------
# Import LocalDubbingPipeline
# -----------------------------------------------------------------------------
try:
    from src.inference.local_pipeline.core import LocalDubbingPipeline # pyright: ignore[reportMissingImports]
except Exception as e:
    logger.error("❌ Failed to import LocalDubbingPipeline: %s", e)
    raise

# -----------------------------------------------------------------------------
# Singleton loader
# -----------------------------------------------------------------------------
_PIPELINE = None

def get_pipeline() -> "LocalDubbingPipeline":
    """
    Instantiate only once.
    Heavy models (Whisper, MT, TTS) load a single time.
    """
    global _PIPELINE

    if _PIPELINE is None:
        logger.info("🔥 Initializing LocalDubbingPipeline")
        _PIPELINE = LocalDubbingPipeline()
        logger.info("✅ LocalDubbingPipeline initialized")

    return _PIPELINE
