"""Headless face-swap orchestrator for the factory module.

Provides ``SwapResult`` and ``run_swap()`` — a self-contained function that
loads images, runs a face swap via the watserface pipeline, extracts ArcFace
embeddings from source and result, and returns timing / VRAM metrics.

v0.1 — swap wiring is a stub (passthrough) with a clear TODO.
Embedding extraction and VRAM tracking are fully functional.
"""

from __future__ import annotations

import logging
import importlib
import time
from dataclasses import dataclass
from typing import Any, Optional

cv2 = importlib.import_module("cv2")
np = importlib.import_module("numpy")
NDArray = Any

from factory.identity import compute_identity_similarity
from factory.reface_bridge import REFaceBridge
from factory.state_isolator import StateIsolator

logger = logging.getLogger("factory.orchestrator")


# ---------------------------------------------------------------------------
# Embedding helpers — reuse the eval/utils.py InsightFace pattern
# ---------------------------------------------------------------------------

_face_app = None
_reface_bridge: REFaceBridge | None = None


def _get_reface_bridge() -> REFaceBridge:
    global _reface_bridge
    if _reface_bridge is None:
        _reface_bridge = REFaceBridge(device="auto")
    return _reface_bridge


def _get_face_app():
    """Lazily initialise the InsightFace buffalo_l analysis app."""
    global _face_app
    if _face_app is not None:
        return _face_app

    insightface = importlib.import_module("insightface")

    app = insightface.app.FaceAnalysis(
        name="buffalo_l",
        providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
    )
    app.prepare(ctx_id=0, det_size=(640, 640))
    _face_app = app
    return _face_app


def _extract_embedding(img: NDArray) -> Optional[NDArray]:
    """Extract the L2-normalised ArcFace embedding of the largest face in *img*."""
    app = _get_face_app()
    faces = app.get(img)
    if not faces:
        return None

    def _area(f):
        bbox = f.bbox
        return (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])

    best = max(faces, key=_area)
    emb = best.normed_embedding
    return emb.astype(np.float32)


# ---------------------------------------------------------------------------
# VRAM helpers
# ---------------------------------------------------------------------------

def _reset_vram_stats() -> None:
    """Reset CUDA peak memory stats if a GPU is available."""
    try:
        torch = importlib.import_module("torch")

        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
    except Exception:
        pass


def _peak_vram_mb() -> float:
    """Return peak VRAM usage in MB since the last reset, or 0.0 on CPU."""
    try:
        torch = importlib.import_module("torch")

        if torch.cuda.is_available():
            return torch.cuda.max_memory_allocated() / (1024 * 1024)
    except Exception:
        pass
    return 0.0


# ---------------------------------------------------------------------------
# SwapResult dataclass
# ---------------------------------------------------------------------------

@dataclass
class SwapResult:
    """Container for the outputs of a single ``run_swap`` invocation."""

    source_frame: NDArray
    """The loaded source image (BGR, HWC)."""

    target_frame: NDArray
    """The loaded target image (BGR, HWC)."""

    result_frame: NDArray
    """The face-swapped output (BGR, HWC)."""

    source_embedding: Optional[NDArray]
    """ArcFace embedding of the source face (512-d, L2-normalised)."""

    result_embedding: Optional[NDArray]
    """ArcFace embedding of the result face (512-d, L2-normalised)."""

    elapsed_seconds: float
    """Wall-clock time for the entire run_swap call."""

    peak_vram_mb: float
    """Peak VRAM usage during the swap (0.0 on CPU)."""


# ---------------------------------------------------------------------------
# Preset application helper
# ---------------------------------------------------------------------------

def _apply_preset(preset: str) -> None:
    """Apply a named preset to the watserface state.

    TODO: Wire up to PresetManager or a factory-specific preset registry.
    For now this is a no-op placeholder; StateIsolator already ensures
    any state changes are rolled back after the swap.
    """
    logger.debug("apply_preset: '%s' (not yet wired)", preset)


# ---------------------------------------------------------------------------
# run_swap — the main entry point
# ---------------------------------------------------------------------------

def run_swap(
    source_path: str,
    target_path: str,
    preset: Optional[str] = None,
) -> SwapResult:
    """Execute a headless face swap and return rich results.

    Parameters
    ----------
    source_path:
        Path to the source face image.
    target_path:
        Path to the target image onto which the source face is swapped.
    preset:
        Optional preset name.  When given the swap runs inside a
        ``StateIsolator`` so global state is restored afterwards.

    Returns
    -------
    SwapResult with frames, embeddings, timing, and VRAM metrics.
    """
    t0 = time.perf_counter()
    _reset_vram_stats()

    # --- load images ---
    source_frame = cv2.imread(source_path)
    if source_frame is None:
        raise FileNotFoundError(f"Cannot read source image: {source_path}")

    target_frame = cv2.imread(target_path)
    if target_frame is None:
        raise FileNotFoundError(f"Cannot read target image: {target_path}")

    # --- extract source embedding ---
    source_embedding = _extract_embedding(source_frame)

    # --- run the swap ---
    if preset is not None:
        with StateIsolator():
            _apply_preset(preset)
            result_frame = _execute_swap(source_frame, target_frame)
    else:
        result_frame = _execute_swap(source_frame, target_frame)

    # --- extract result embedding ---
    result_embedding = _extract_embedding(result_frame)

    # --- metrics ---
    elapsed = time.perf_counter() - t0
    vram = _peak_vram_mb()

    # --- identity similarity (for logging) ---
    if source_embedding is not None and result_embedding is not None:
        sim = compute_identity_similarity(source_embedding, result_embedding)
        logger.info("identity similarity: %.4f", sim)

    return SwapResult(
        source_frame=source_frame,
        target_frame=target_frame,
        result_frame=result_frame,
        source_embedding=source_embedding,
        result_embedding=result_embedding,
        elapsed_seconds=elapsed,
        peak_vram_mb=vram,
    )


def _execute_swap(source_frame: NDArray, target_frame: NDArray) -> NDArray:
    bridge = _get_reface_bridge()
    return bridge.swap(source_frame, target_frame)
