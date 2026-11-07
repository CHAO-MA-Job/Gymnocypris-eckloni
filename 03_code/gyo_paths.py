"""Resolve the detection-table directory for regional postprocessing."""
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
QUANT=str(Path(os.environ.get("FISH_DETECTION_DIR", ROOT / "04_analysis_data" / "detection_tables")).resolve())
