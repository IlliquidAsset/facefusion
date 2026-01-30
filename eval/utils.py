"""
Shared utilities for the WatserFace evaluation harness.

Standalone — no watserface/ or FaceFusion dependencies.
Uses insightface (Apache 2.0) for RetinaFace detection + ArcFace embeddings.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np

logger = logging.getLogger("eval")

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}


def _check_embedding_model(model_name: str) -> None:
    if model_name == "arcface":
        return
    if model_name == "auraface":
        raise NotImplementedError(
            "AuraFace embeddings are not yet implemented. "
            "This flag is reserved for future AuraFace swap evaluation. "
            "Use --embedding-model arcface (the default) for now."
        )
    raise ValueError(f"Unknown embedding model: {model_name!r}. Supported: arcface, auraface")


_face_app = None


def get_face_app() -> Any:
    global _face_app
    if _face_app is not None:
        return _face_app

    import insightface

    app = insightface.app.FaceAnalysis(
        name="buffalo_l",
        providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
    )
    app.prepare(ctx_id=0, det_size=(640, 640))
    _face_app = app
    return _face_app


def load_image(path: str | Path) -> np.ndarray:
    import cv2

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")
    img = cv2.imread(str(path))
    if img is None:
        raise ValueError(f"Failed to decode image: {path}")
    return img


def detect_largest_face(img: np.ndarray) -> Any | None:
    app = get_face_app()
    faces = app.get(img)
    if not faces:
        return None

    def _area(f: Any) -> float:
        bbox = f.bbox
        return (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])

    return max(faces, key=_area)


def extract_embedding(img: np.ndarray, embedding_model: str = "arcface") -> np.ndarray | None:
    import numpy as np

    _check_embedding_model(embedding_model)
    face = detect_largest_face(img)
    if face is None:
        return None
    emb: np.ndarray = face.normed_embedding
    return emb.astype(np.float32)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity clamped to [0, 1]. Inputs must be L2-normalised."""
    import numpy as np

    sim = float(np.dot(a, b))
    return max(0.0, min(1.0, sim))


def compute_identity_score(
    source_path: str | Path,
    target_path: str | Path,
    embedding_model: str = "arcface",
) -> dict[str, Any]:
    src_img = load_image(source_path)
    tgt_img = load_image(target_path)

    src_emb = extract_embedding(src_img, embedding_model)
    if src_emb is None:
        return {
            "identity_score": None,
            "source": str(source_path),
            "target": str(target_path),
            "embedding_model": embedding_model,
            "error": "No face detected in source image",
        }

    tgt_emb = extract_embedding(tgt_img, embedding_model)
    if tgt_emb is None:
        return {
            "identity_score": None,
            "source": str(source_path),
            "target": str(target_path),
            "embedding_model": embedding_model,
            "error": "No face detected in target image",
        }

    score = cosine_similarity(src_emb, tgt_emb)
    return {
        "identity_score": round(score, 4),
        "source": str(source_path),
        "target": str(target_path),
        "embedding_model": embedding_model,
    }


def write_json(data: Any, path: str | Path | None) -> None:
    text = json.dumps(data, indent=2, ensure_ascii=False)
    if path is None:
        print(text)
    else:
        Path(path).write_text(text + "\n", encoding="utf-8")
        logger.info("Wrote results to %s", path)


def collect_images(directory: str | Path) -> list[Path]:
    d = Path(directory)
    if not d.is_dir():
        raise NotADirectoryError(f"Not a directory: {d}")
    return sorted(p for p in d.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS)


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="[%(levelname)s] %(message)s",
        stream=sys.stderr,
    )
