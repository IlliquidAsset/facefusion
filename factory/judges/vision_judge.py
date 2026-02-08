"""Vision-based LLM judge for face-swap quality evaluation."""

import base64
import json
import logging
import os
from dataclasses import dataclass
from typing import Dict, Optional

from factory.judges.prompts import DIMENSIONS, FACE_SWAP_EVALUATION_PROMPT

logger = logging.getLogger(__name__)

MEDIA_TYPE_MAP = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
}


@dataclass
class JudgeResult:
    """Result from a single LLM judge evaluation."""

    scores: Dict[str, int]
    notes: str
    raw_response: str
    skipped: bool = False
    error: Optional[str] = None


def _detect_media_type(path: str) -> str:
    """Detect image media type from file extension."""
    ext = os.path.splitext(path)[1].lower()
    return MEDIA_TYPE_MAP.get(ext, "image/png")


def _encode_image(path: str) -> str:
    """Read an image file and return base64-encoded string."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


class VisionJudge:
    """Uses a vision-capable LLM to evaluate face-swap quality.

    The judge is always advisory — it never crashes or blocks the pipeline.
    When the API key is missing or the anthropic package is unavailable,
    results are returned with ``skipped=True``.
    """

    def __init__(self, model: str = "claude-sonnet-4-20250514") -> None:
        self.model = model

    def evaluate(self, source_path: str, output_path: str) -> JudgeResult:
        """Evaluate a face-swap result against the source identity.

        Args:
            source_path: Path to the source identity image.
            output_path: Path to the face-swapped output image.

        Returns:
            A :class:`JudgeResult` with quality scores or skip/error info.
        """
        # --- Pre-flight checks ---
        if not os.environ.get("ANTHROPIC_API_KEY"):
            logger.debug("ANTHROPIC_API_KEY not set — skipping LLM judge")
            return JudgeResult(
                scores={}, notes="API key not set", raw_response="", skipped=True
            )

        for path in (source_path, output_path):
            if not os.path.isfile(path):
                logger.warning("File not found: %s", path)
                return JudgeResult(
                    scores={},
                    notes="",
                    raw_response="",
                    skipped=True,
                    error=f"File not found: {path}",
                )

        # --- Lazy import ---
        try:
            import anthropic  # type: ignore[import-untyped]
        except ImportError:
            logger.warning("anthropic package not installed — skipping LLM judge")
            return JudgeResult(
                scores={},
                notes="",
                raw_response="",
                skipped=True,
                error="anthropic package not installed",
            )

        # --- Encode images ---
        source_b64 = _encode_image(source_path)
        output_b64 = _encode_image(output_path)
        source_media = _detect_media_type(source_path)
        output_media = _detect_media_type(output_path)

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": FACE_SWAP_EVALUATION_PROMPT},
                    {"type": "text", "text": "SOURCE IMAGE:"},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": source_media,
                            "data": source_b64,
                        },
                    },
                    {"type": "text", "text": "OUTPUT IMAGE:"},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": output_media,
                            "data": output_b64,
                        },
                    },
                ],
            }
        ]

        # --- Call LLM (with one retry on parse failure) ---
        client = anthropic.Anthropic()
        raw_text = ""

        for attempt in range(2):
            try:
                response = client.messages.create(
                    model=self.model,
                    max_tokens=1024,
                    messages=messages,
                )
                raw_text = response.content[0].text
                parsed = json.loads(raw_text)

                scores: Dict[str, int] = {}
                for dim in DIMENSIONS:
                    val = parsed.get(dim)
                    if isinstance(val, (int, float)):
                        scores[dim] = int(val)

                notes = parsed.get("notes", "")
                logger.info("LLM judge evaluation complete (attempt %d)", attempt + 1)
                return JudgeResult(
                    scores=scores,
                    notes=str(notes),
                    raw_response=raw_text,
                )

            except json.JSONDecodeError:
                if attempt == 0:
                    logger.warning(
                        "JSON parse failed on attempt 1 — retrying"
                    )
                    continue
                logger.error("JSON parse failed on retry — returning error")
                return JudgeResult(
                    scores={},
                    notes="",
                    raw_response=raw_text,
                    error="Failed to parse response",
                )
            except Exception as exc:
                logger.error("LLM judge API error: %s", exc)
                return JudgeResult(
                    scores={},
                    notes="",
                    raw_response=raw_text,
                    error=str(exc),
                )

        # Should be unreachable, but defensive:
        return JudgeResult(
            scores={},
            notes="",
            raw_response=raw_text,
            error="Unexpected: exhausted retries",
        )
