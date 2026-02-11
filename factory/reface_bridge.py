from __future__ import annotations

import atexit
import base64
import importlib
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Iterable
from urllib import request

cv2 = importlib.import_module("cv2")
np = importlib.import_module("numpy")
PILImage = importlib.import_module("PIL.Image")
NDArray = Any


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


class REFaceBridge:
    def __init__(
        self,
        config_path: str | Path | None = None,
        checkpoint_path: str | Path | None = None,
        device: str = "cuda",
        ddim_steps: int = 50,
        scale: float = 3.5,
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
            str(self._config_path),
            "--ckpt",
            str(self._checkpoint_path),
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

        self._server_process = subprocess.Popen(
            cmd,
            cwd=self._reface_dir,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
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

    def _swap_via_server(self, source_png: bytes, target_png: bytes) -> NDArray:
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

        output_image_url = payload.get("output_image_url", "")
        if "," not in output_image_url:
            raise RuntimeError("REFace response missing output image")

        _, encoded = output_image_url.split(",", 1)
        image_bytes = base64.b64decode(encoded)
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            raise RuntimeError("Failed to decode REFace output image")
        return img

    def swap(self, source_image: NDArray, target_image: NDArray) -> NDArray:
        if source_image is None or target_image is None:
            raise ValueError("source_image and target_image must be non-empty arrays")

        source_png = self._bgr_to_rgb_bytes(source_image)
        target_png = self._bgr_to_rgb_bytes(target_image)

        with tempfile.TemporaryDirectory(prefix="reface_bridge_") as temp_dir:
            base = Path(temp_dir)
            src_dir = base / "source"
            tgt_dir = base / "target"
            out_dir = base / "output"
            src_dir.mkdir(parents=True, exist_ok=True)
            tgt_dir.mkdir(parents=True, exist_ok=True)
            out_dir.mkdir(parents=True, exist_ok=True)
            (src_dir / "source.png").write_bytes(source_png)
            (tgt_dir / "target.png").write_bytes(target_png)

            with self._lock:
                self._ensure_server()
                swapped = self._swap_via_server(source_png, target_png)

            output_path = out_dir / "result.png"
            cv2.imwrite(str(output_path), swapped)
            result = cv2.imread(str(output_path), cv2.IMREAD_COLOR)
            if result is None:
                raise RuntimeError("Failed to read bridge output image")
            return result

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
