from __future__ import annotations

import atexit
import base64
import importlib
import io
import json
import logging
import os
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional
from urllib import request

cv2 = importlib.import_module("cv2")
np = importlib.import_module("numpy")
PILImage = importlib.import_module("PIL.Image")
NDArray = Any

logger = logging.getLogger("factory.reface_bridge")


# ---------------------------------------------------------------------------
# Swap response with optional raw crop + alignment for hybrid compositing
# ---------------------------------------------------------------------------

@dataclass
class _SwapResponse:
    """Internal result from REFace server."""
    composite: NDArray  # REFace's own paste-back (fallback)
    raw_crop: Optional[NDArray]  # 1024x1024 raw face crop (if patched server)
    alignment: Optional[dict]  # inv_transform_coeffs + orig_size (if patched)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _auto_device() -> str:
    try:
        torch = importlib.import_module("torch")

        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    except Exception:
        pass
    return "cpu"


# ---------------------------------------------------------------------------
# Hybrid compositing — ported from watserface/face_helper.py
# ---------------------------------------------------------------------------

def _pil_perspective_to_cv2_matrix(coeffs: list[float]) -> NDArray:
    """Convert PIL Image.PERSPECTIVE 8-element coefficients to a 3x3 matrix.

    PIL's perspective transform maps destination→source:
        x' = (a*x + b*y + c) / (g*x + h*y + 1)
        y' = (d*x + e*y + f) / (g*x + h*y + 1)
    where coeffs = [a, b, c, d, e, f, g, h].

    We need the INVERSE (source→destination) for cv2.warpPerspective.
    """
    a, b, c, d, e, f, g, h = coeffs
    # PIL transform matrix (maps dest coords to source coords)
    M_pil = np.array([
        [a, b, c],
        [d, e, f],
        [g, h, 1.0],
    ], dtype=np.float64)
    # Invert: we want source→dest for cv2.warpPerspective
    M_cv2 = np.linalg.inv(M_pil)
    return M_cv2


def _create_elliptical_mask(height: int, width: int, shrink: float = 0.85, blur_ksize: int = 0) -> NDArray:
    """Create a soft elliptical mask for face blending.

    The ellipse is centered in the image and covers ``shrink`` fraction
    of width/height, with Gaussian blur for feathering.
    """
    mask = np.zeros((height, width), dtype=np.float32)
    center = (width // 2, height // 2)
    axes = (int(width * shrink / 2), int(height * shrink / 2))
    cv2.ellipse(mask, center, axes, 0, 0, 360, 1.0, -1)

    if blur_ksize <= 0:
        blur_ksize = max(height, width) // 4
        blur_ksize = blur_ksize + 1 if blur_ksize % 2 == 0 else blur_ksize
    mask = cv2.GaussianBlur(mask, (blur_ksize, blur_ksize), 0)
    return mask


def _create_box_mask(height: int, width: int, padding_pct: float = 0.05, blur_frac: float = 0.12) -> NDArray:
    """Create a box mask with Gaussian feathering on all edges.

    Ported from watserface/face_masker.py::create_box_mask.
    """
    blur_amount = int(width * 0.5 * blur_frac)
    blur_area = max(blur_amount // 2, 1)
    pad = max(blur_area, int(height * padding_pct))

    mask = np.ones((height, width), dtype=np.float32)
    mask[:pad, :] = 0
    mask[-pad:, :] = 0
    mask[:, :pad] = 0
    mask[:, -pad:] = 0

    if blur_amount > 0:
        mask = cv2.GaussianBlur(mask, (0, 0), blur_amount * 0.25)
    return mask


def _hybrid_paste_back(
    target_frame: NDArray,
    raw_crop: NDArray,
    alignment: dict,
    use_poisson: bool = True,
    mask_type: str = "elliptical",
) -> NDArray:
    """Paste the raw REFace face crop onto the target using watserface-style compositing.

    Parameters
    ----------
    target_frame : NDArray
        Original target image (BGR, HWC).
    raw_crop : NDArray
        1024x1024 raw diffusion face output (BGR, HWC).
    alignment : dict
        Must contain 'inv_transform_coeffs' (8 floats) and 'orig_size' ([w, h]).
    use_poisson : bool
        If True, use cv2.seamlessClone for Poisson blending; falls back to
        alpha blending on failure.
    mask_type : str
        "elliptical" or "box" — determines feathering shape.

    Returns
    -------
    NDArray — the composited result, same size as target_frame.
    """
    coeffs = alignment["inv_transform_coeffs"]
    orig_w, orig_h = alignment["orig_size"]
    crop_h, crop_w = raw_crop.shape[:2]

    # Build the perspective matrix (crop-space → target-space)
    M = _pil_perspective_to_cv2_matrix(coeffs)

    # Create soft mask in crop space
    if mask_type == "box":
        crop_mask = _create_box_mask(crop_h, crop_w)
    else:
        crop_mask = _create_elliptical_mask(crop_h, crop_w, shrink=0.88)

    # Warp both face and mask into target space
    warped_face = cv2.warpPerspective(
        raw_crop, M, (orig_w, orig_h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )
    warped_mask = cv2.warpPerspective(
        crop_mask, M, (orig_w, orig_h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )

    # Ensure target_frame matches orig_size
    t_h, t_w = target_frame.shape[:2]
    if t_h != orig_h or t_w != orig_w:
        logger.warning(
            "Target frame size (%d,%d) != alignment orig_size (%d,%d), resizing",
            t_w, t_h, orig_w, orig_h,
        )

    if use_poisson:
        try:
            result = _poisson_blend(target_frame, warped_face, warped_mask)
            logger.info("Hybrid compositing: Poisson blending succeeded")
            return result
        except cv2.error as e:
            logger.warning("Poisson blending failed (%s), falling back to alpha blend", e)

    result = _alpha_blend(target_frame, warped_face, warped_mask)
    logger.info("Hybrid compositing: alpha blending")
    return result


def _alpha_blend(target: NDArray, warped_face: NDArray, warped_mask: NDArray) -> NDArray:
    """Standard alpha blending with the warped mask."""
    mask_3ch = np.expand_dims(warped_mask, axis=-1)
    result = target.copy().astype(np.float32)
    result = result * (1.0 - mask_3ch) + warped_face.astype(np.float32) * mask_3ch
    return result.clip(0, 255).astype(np.uint8)


def _poisson_blend(target: NDArray, warped_face: NDArray, warped_mask: NDArray) -> NDArray:
    """Poisson blending (cv2.seamlessClone) ported from watserface."""
    mask_uint8 = (warped_mask * 255).astype(np.uint8)

    # Find contours to get tight bounding box for center
    contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return _alpha_blend(target, warped_face, warped_mask)

    all_points = np.concatenate(contours)
    x, y, w, h = cv2.boundingRect(all_points)
    center = (x + w // 2, y + h // 2)

    # Ensure center is within bounds
    t_h, t_w = target.shape[:2]
    center = (max(1, min(center[0], t_w - 2)), max(1, min(center[1], t_h - 2)))

    result = cv2.seamlessClone(warped_face, target, mask_uint8, center, cv2.MIXED_CLONE)
    return result


# ---------------------------------------------------------------------------
# REFaceBridge
# ---------------------------------------------------------------------------

class REFaceBridge:
    def __init__(
        self,
        config_path: str | Path | None = None,
        checkpoint_path: str | Path | None = None,
        device: str = "cuda",
        ddim_steps: int = 50,
        scale: float = 3.5,
        use_hybrid_compositing: bool = True,
        use_poisson: bool = False,
        mask_type: str = "elliptical",
    ) -> None:
        root = _project_root()
        self._reface_dir = root / "vendors" / "REFace"
        self._script_path = self._reface_dir / "scripts" / "one_inference.py"
        self._config_path = Path(config_path) if config_path else self._reface_dir / "configs" / "train.yaml"
        self._checkpoint_path = (
            Path(checkpoint_path)
            if checkpoint_path
            else self._reface_dir / "models" / "REFace" / "checkpoints" / "saved.ckpt"
        )

        self._device = _auto_device() if device == "auto" else device.lower()
        self._ddim_steps = int(ddim_steps)
        self._scale = float(scale)

        # Hybrid compositing settings
        self._use_hybrid = use_hybrid_compositing
        self._use_poisson = use_poisson
        self._mask_type = mask_type

        self._server_url = "http://127.0.0.1:5000/process_images"
        self._health_url = "http://127.0.0.1:5000/"
        self._server_process: subprocess.Popen[bytes] | None = None
        self._lock = threading.Lock()

        self._validate_paths()
        atexit.register(self.close)

    def _validate_paths(self) -> None:
        for p in (self._reface_dir, self._script_path, self._config_path, self._checkpoint_path):
            if not p.exists():
                raise FileNotFoundError(f"REFace path missing: {p}")

    def _server_running(self) -> bool:
        proc = self._server_process
        return proc is not None and proc.poll() is None

    def _is_healthy(self) -> bool:
        try:
            with request.urlopen(self._health_url, timeout=1.0) as resp:
                return resp.status in (200, 302, 404)
        except Exception:
            return False

    def _ensure_server(self) -> None:
        if self._server_running() and self._is_healthy():
            return

        if self._server_running() and not self._is_healthy():
            self.close()

        # Paths must be relative to _reface_dir since cwd is set there
        try:
            config_rel = self._config_path.relative_to(self._reface_dir)
        except ValueError:
            config_rel = self._config_path
        try:
            ckpt_rel = self._checkpoint_path.relative_to(self._reface_dir)
        except ValueError:
            ckpt_rel = self._checkpoint_path

        cmd = [
            sys.executable,
            "scripts/one_inference.py",
            "--outdir",
            "examples/FaceSwap/One_output/results",
            "--target_folder",
            "examples/FaceSwap/One_target",
            "--src_folder",
            "examples/FaceSwap/One_source",
            "--config",
            str(config_rel),
            "--ckpt",
            str(ckpt_rel),
            "--Base_dir",
            "examples/FaceSwap/One_output/Outs",
            "--n_samples",
            "1",
            "--scale",
            str(self._scale),
            "--ddim_steps",
            str(self._ddim_steps),
        ]

        env = os.environ.copy()
        current_pythonpath = env.get("PYTHONPATH", "")
        if current_pythonpath:
            env["PYTHONPATH"] = f"{self._reface_dir}:{current_pythonpath}"
        else:
            env["PYTHONPATH"] = str(self._reface_dir)
        if self._device == "cpu" or self._device == "mps":
            env["CUDA_VISIBLE_DEVICES"] = ""

        log_path = self._reface_dir / "reface_server.log"
        self._server_log = open(log_path, "w")
        self._server_process = subprocess.Popen(
            cmd,
            cwd=self._reface_dir,
            env=env,
            stdout=self._server_log,
            stderr=subprocess.STDOUT,
        )

        timeout_seconds = 300.0
        start = time.perf_counter()
        while time.perf_counter() - start < timeout_seconds:
            if self._server_process.poll() is not None:
                raise RuntimeError(
                    f"REFace server exited during startup with code {self._server_process.returncode}"
                )
            if self._is_healthy():
                return
            time.sleep(1.0)
        raise TimeoutError("Timed out waiting for REFace server to become ready")

    @staticmethod
    def _bgr_to_rgb_bytes(frame: NDArray) -> bytes:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        buff = io.BytesIO()
        PILImage.fromarray(rgb).save(buff, format="PNG")
        return buff.getvalue()

    @staticmethod
    def _build_multipart_form(fields: dict[str, str], files: dict[str, tuple[str, bytes, str]]) -> tuple[bytes, str]:
        boundary = f"----watserface-{uuid.uuid4().hex}"
        body = bytearray()

        for name, value in fields.items():
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
            body.extend(str(value).encode("utf-8"))
            body.extend(b"\r\n")

        for name, (filename, data, content_type) in files.items():
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(
                (
                    f'Content-Disposition: form-data; name="{name}"; '
                    f'filename="{filename}"\r\n'
                ).encode("utf-8")
            )
            body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
            body.extend(data)
            body.extend(b"\r\n")

        body.extend(f"--{boundary}--\r\n".encode("utf-8"))
        return bytes(body), boundary

    @staticmethod
    def _decode_b64_image(data_uri: str) -> NDArray:
        """Decode a data URI (data:image/...;base64,...) to BGR NDArray."""
        if "," not in data_uri:
            raise RuntimeError("Invalid data URI — no comma separator")
        _, encoded = data_uri.split(",", 1)
        image_bytes = base64.b64decode(encoded)
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise RuntimeError("Failed to decode base64 image")
        return img

    def _swap_via_server(self, source_png: bytes, target_png: bytes) -> _SwapResponse:
        """Send images to REFace Flask server, return composite + optional raw crop."""
        fields = {"steps": str(self._ddim_steps), "scale": str(self._scale)}
        files = {
            "image1": ("source.png", source_png, "image/png"),
            "image2": ("target.png", target_png, "image/png"),
        }
        data, boundary = self._build_multipart_form(fields, files)
        req = request.Request(
            self._server_url,
            data=data,
            method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )

        with request.urlopen(req, timeout=1800.0) as resp:
            payload = json.loads(resp.read().decode("utf-8"))

        # Decode the composite (always present)
        output_image_url = payload.get("output_image_url", "")
        if "," not in output_image_url:
            raise RuntimeError("REFace response missing output image")
        composite = self._decode_b64_image(output_image_url)

        # Decode raw face crop (if patched server provides it)
        raw_crop = None
        raw_crop_uri = payload.get("raw_face_crop")
        if raw_crop_uri and "," in raw_crop_uri:
            try:
                raw_crop = self._decode_b64_image(raw_crop_uri)
                logger.info("Received raw face crop: %s", raw_crop.shape)
            except Exception as e:
                logger.warning("Failed to decode raw face crop: %s", e)

        # Alignment data (if patched server provides it)
        alignment = payload.get("alignment")
        if alignment:
            logger.info("Received alignment data: orig_size=%s", alignment.get("orig_size"))

        return _SwapResponse(composite=composite, raw_crop=raw_crop, alignment=alignment)

    def swap(self, source_image: NDArray, target_image: NDArray) -> NDArray:
        if source_image is None or target_image is None:
            raise ValueError("source_image and target_image must be non-empty arrays")

        source_png = self._bgr_to_rgb_bytes(source_image)
        target_png = self._bgr_to_rgb_bytes(target_image)

        with self._lock:
            self._ensure_server()
            response = self._swap_via_server(source_png, target_png)

        # Hybrid compositing: use raw crop + our own paste-back
        if self._use_hybrid and response.raw_crop is not None and response.alignment is not None:
            try:
                result = _hybrid_paste_back(
                    target_image,
                    response.raw_crop,
                    response.alignment,
                    use_poisson=self._use_poisson,
                    mask_type=self._mask_type,
                )
                logger.info("Hybrid compositing produced %s result", result.shape)
                return result
            except Exception as e:
                logger.warning("Hybrid compositing failed (%s), using REFace composite", e)

        # Fallback: use REFace's own composite
        logger.info("Using REFace composite (no hybrid)")
        return response.composite

    def swap_batch(self, sources: Iterable[NDArray], targets: Iterable[NDArray]) -> list[NDArray]:
        return [self.swap(src, tgt) for src, tgt in zip(sources, targets)]

    def close(self) -> None:
        proc = self._server_process
        if proc is None:
            return
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
        self._server_process = None
        log = getattr(self, "_server_log", None)
        if log is not None and not log.closed:
            log.close()
            self._server_log = None
