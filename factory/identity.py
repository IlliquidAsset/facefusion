"""Identity similarity computation for the factory module.

Uses raw cosine similarity clamped to [0, 1], matching the canonical
implementation in eval/utils.py (NOT the QualityChecker (x+1)/2 variant).
"""

from __future__ import annotations

import numpy as np


def compute_identity_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
    """Cosine similarity between two L2-normalised embeddings, clamped to [0, 1].

    Parameters
    ----------
    emb1, emb2:
        ArcFace embeddings (typically 512-d, already L2-normalised by InsightFace).

    Returns
    -------
    float in [0.0, 1.0].
    """
    sim = float(np.dot(emb1, emb2))
    return max(0.0, min(1.0, sim))
