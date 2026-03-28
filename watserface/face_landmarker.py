from functools import lru_cache
from typing import Optional, Tuple

import threading

import cv2
import numpy

from watserface import inference_manager, state_manager
from watserface.download import (
    conditional_download_hashes,
    conditional_download_sources,
    resolve_download_url,
)
from watserface.face_helper import (
    create_rotated_matrix_and_size,
    estimate_matrix_by_face_landmark_5,
    transform_points,
    warp_face_by_translation,
)
from watserface.filesystem import resolve_relative_path
from watserface.thread_helper import conditional_thread_semaphore
from watserface.types import (
    Angle,
    BoundingBox,
    DownloadScope,
    DownloadSet,
    FaceLandmark5,
    FaceLandmark68,
    FaceLandmark478,
    InferencePool,
    ModelSet,
    Prediction,
    Score,
    VisionFrame,
)

MEDIAPIPE_FACE_MESH = None
THREAD_LOCK: threading.Lock = threading.Lock()


@lru_cache(maxsize=None)
def create_static_model_set(download_scope: DownloadScope) -> ModelSet:
    return {
        "2dfan4": {
            "hashes": {
                "2dfan4": {
                    "url": resolve_download_url("models-3.0.0", "2dfan4.hash"),
                    "path": resolve_relative_path("../.assets/models/2dfan4.hash"),
                }
            },
            "sources": {
                "2dfan4": {
                    "url": resolve_download_url("models-3.0.0", "2dfan4.onnx"),
                    "path": resolve_relative_path("../.assets/models/2dfan4.onnx"),
                }
            },
            "size": (256, 256),
        },
        "peppa_wutz": {
            "hashes": {
                "peppa_wutz": {
                    "url": resolve_download_url("models-3.0.0", "peppa_wutz.hash"),
                    "path": resolve_relative_path("../.assets/models/peppa_wutz.hash"),
                }
            },
            "sources": {
                "peppa_wutz": {
                    "url": resolve_download_url("models-3.0.0", "peppa_wutz.onnx"),
                    "path": resolve_relative_path("../.assets/models/peppa_wutz.onnx"),
                }
            },
            "size": (256, 256),
        },
        "fan_68_5": {
            "hashes": {
                "fan_68_5": {
                    "url": resolve_download_url("models-3.0.0", "fan_68_5.hash"),
                    "path": resolve_relative_path("../.assets/models/fan_68_5.hash"),
                }
            },
            "sources": {
                "fan_68_5": {
                    "url": resolve_download_url("models-3.0.0", "fan_68_5.onnx"),
                    "path": resolve_relative_path("../.assets/models/fan_68_5.onnx"),
                }
            },
        },
    }


def get_inference_pool() -> InferencePool:
    model_names = [state_manager.get_item("face_landmarker_model"), "fan_68_5"]
    _, model_source_set = collect_model_downloads()

    return inference_manager.get_inference_pool(__name__, model_names, model_source_set)


def clear_inference_pool() -> None:
    global MEDIAPIPE_FACE_MESH

    model_names = [state_manager.get_item("face_landmarker_model"), "fan_68_5"]
    inference_manager.clear_inference_pool(__name__, model_names)
    if MEDIAPIPE_FACE_MESH:
        MEDIAPIPE_FACE_MESH.close()
        MEDIAPIPE_FACE_MESH = None


def collect_model_downloads() -> Tuple[DownloadSet, DownloadSet]:
    model_set = create_static_model_set("full")
    model_hash_set = {
        "fan_68_5": model_set.get("fan_68_5").get("hashes").get("fan_68_5")
    }
    model_source_set = {
        "fan_68_5": model_set.get("fan_68_5").get("sources").get("fan_68_5")
    }

    for face_landmarker_model in ["2dfan4", "peppa_wutz"]:
        if state_manager.get_item("face_landmarker_model") in [
            "many",
            face_landmarker_model,
        ]:
            model_hash_set[face_landmarker_model] = (
                model_set.get(face_landmarker_model)
                .get("hashes")
                .get(face_landmarker_model)
            )
            model_source_set[face_landmarker_model] = (
                model_set.get(face_landmarker_model)
                .get("sources")
                .get(face_landmarker_model)
            )

    return model_hash_set, model_source_set


def pre_check() -> bool:
    model_hash_set, model_source_set = collect_model_downloads()

    return conditional_download_hashes(model_hash_set) and conditional_download_sources(
        model_source_set
    )


def detect_face_landmark(
    vision_frame: VisionFrame, bounding_box: BoundingBox, face_angle: Angle
) -> Tuple[FaceLandmark68, Optional[FaceLandmark478], Score]:
    face_landmark_2dfan4 = None
    face_landmark_peppa_wutz = None
    face_landmark_score_2dfan4 = 0.0
    face_landmark_score_peppa_wutz = 0.0

    if state_manager.get_item("face_landmarker_model") == "mediapipe":
        return detect_with_mediapipe(vision_frame, bounding_box, face_angle)

    if state_manager.get_item("face_landmarker_model") in ["many", "2dfan4"]:
        face_landmark_2dfan4, face_landmark_score_2dfan4 = detect_with_2dfan4(
            vision_frame, bounding_box, face_angle
        )

    if state_manager.get_item("face_landmarker_model") in ["many", "peppa_wutz"]:
        face_landmark_peppa_wutz, face_landmark_score_peppa_wutz = (
            detect_with_peppa_wutz(vision_frame, bounding_box, face_angle)
        )

    if face_landmark_score_2dfan4 > face_landmark_score_peppa_wutz - 0.2:
        return face_landmark_2dfan4, None, face_landmark_score_2dfan4
    return face_landmark_peppa_wutz, None, face_landmark_score_peppa_wutz


def detect_with_2dfan4(
    temp_vision_frame: VisionFrame, bounding_box: BoundingBox, face_angle: Angle
) -> Tuple[FaceLandmark68, Score]:
    model_size = create_static_model_set("full").get("2dfan4").get("size")
    scale = 195 / numpy.subtract(bounding_box[2:], bounding_box[:2]).max().clip(1, None)
    translation = (
        model_size[0] - numpy.add(bounding_box[2:], bounding_box[:2]) * scale
    ) * 0.5
    rotated_matrix, rotated_size = create_rotated_matrix_and_size(
        face_angle, model_size
    )
    crop_vision_frame, affine_matrix = warp_face_by_translation(
        temp_vision_frame, translation, scale, model_size
    )
    crop_vision_frame = cv2.warpAffine(crop_vision_frame, rotated_matrix, rotated_size)
    crop_vision_frame = conditional_optimize_contrast(crop_vision_frame)
    crop_vision_frame = (
        crop_vision_frame.transpose(2, 0, 1).astype(numpy.float32) / 255.0
    )
    face_landmark_68, face_heatmap = forward_with_2dfan4(crop_vision_frame)
    face_landmark_68 = face_landmark_68[:, :, :2][0] / 64 * 256
    face_landmark_68 = transform_points(
        face_landmark_68, cv2.invertAffineTransform(rotated_matrix)
    )
    face_landmark_68 = transform_points(
        face_landmark_68, cv2.invertAffineTransform(affine_matrix)
    )
    face_landmark_score_68 = numpy.amax(face_heatmap, axis=(2, 3))
    face_landmark_score_68 = numpy.mean(face_landmark_score_68)
    face_landmark_score_68 = numpy.interp(face_landmark_score_68, [0, 0.9], [0, 1])
    return face_landmark_68, face_landmark_score_68


def detect_with_peppa_wutz(
    temp_vision_frame: VisionFrame, bounding_box: BoundingBox, face_angle: Angle
) -> Tuple[FaceLandmark68, Score]:
    model_size = create_static_model_set("full").get("peppa_wutz").get("size")
    scale = 195 / numpy.subtract(bounding_box[2:], bounding_box[:2]).max().clip(1, None)
    translation = (
        model_size[0] - numpy.add(bounding_box[2:], bounding_box[:2]) * scale
    ) * 0.5
    rotated_matrix, rotated_size = create_rotated_matrix_and_size(
        face_angle, model_size
    )
    crop_vision_frame, affine_matrix = warp_face_by_translation(
        temp_vision_frame, translation, scale, model_size
    )
    crop_vision_frame = cv2.warpAffine(crop_vision_frame, rotated_matrix, rotated_size)
    crop_vision_frame = conditional_optimize_contrast(crop_vision_frame)
    crop_vision_frame = (
        crop_vision_frame.transpose(2, 0, 1).astype(numpy.float32) / 255.0
    )
    crop_vision_frame = numpy.expand_dims(crop_vision_frame, axis=0)
    prediction = forward_with_peppa_wutz(crop_vision_frame)
    face_landmark_68 = prediction.reshape(-1, 3)[:, :2] / 64 * model_size[0]
    face_landmark_68 = transform_points(
        face_landmark_68, cv2.invertAffineTransform(rotated_matrix)
    )
    face_landmark_68 = transform_points(
        face_landmark_68, cv2.invertAffineTransform(affine_matrix)
    )
    face_landmark_score_68 = prediction.reshape(-1, 3)[:, 2].mean()
    face_landmark_score_68 = numpy.interp(face_landmark_score_68, [0, 0.95], [0, 1])
    return face_landmark_68, face_landmark_score_68


def detect_with_mediapipe(
    temp_vision_frame: VisionFrame, bounding_box: BoundingBox, face_angle: Angle
) -> Tuple[FaceLandmark68, Optional[FaceLandmark478], Score]:
    global MEDIAPIPE_FACE_MESH

    if MEDIAPIPE_FACE_MESH is None:
        from mediapipe.python.solutions import face_mesh

        MEDIAPIPE_FACE_MESH = face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
        )

    model_size = (256, 256)
    scale = 195 / numpy.subtract(bounding_box[2:], bounding_box[:2]).max().clip(1, None)
    translation = (
        model_size[0] - numpy.add(bounding_box[2:], bounding_box[:2]) * scale
    ) * 0.5
    rotated_matrix, rotated_size = create_rotated_matrix_and_size(
        face_angle, model_size
    )
    crop_vision_frame, affine_matrix = warp_face_by_translation(
        temp_vision_frame, translation, scale, model_size
    )
    crop_vision_frame = cv2.warpAffine(crop_vision_frame, rotated_matrix, rotated_size)

    with THREAD_LOCK:
        results = MEDIAPIPE_FACE_MESH.process(crop_vision_frame)

    if results.multi_face_landmarks:
        face_landmarks = results.multi_face_landmarks[0]
        h, w, _ = crop_vision_frame.shape
        # Capture Z-coordinate (depth relative to face centroid, normalized similarly to x/y)
        # We un-normalize x and y by width/height. Z is usually normalized by image width in MediaPipe.
        landmarks_478 = numpy.array(
            [[lm.x * w, lm.y * h, lm.z * w] for lm in face_landmarks.landmark]
        ).astype(numpy.float32)

        # Map 478 to 68 (Approximate indices)
        # This is a basic mapping, a full mapping is verbose
        indices_68 = [
            162,
            234,
            93,
            58,
            172,
            136,
            149,
            148,
            152,
            377,
            378,
            365,
            397,
            288,
            323,
            454,
            389,
            71,
            63,
            105,
            66,
            107,
            336,
            296,
            334,
            293,
            300,
            168,
            6,
            195,
            4,
            64,
            60,
            279,
            292,
            305,
            7,
            33,
            160,
            158,
            133,
            153,
            144,
            362,
            385,
            387,
            263,
            373,
            380,
            61,
            40,
            37,
            0,
            267,
            270,
            291,
            321,
            314,
            17,
            84,
            181,
            78,
            82,
            13,
            312,
            308,
            317,
            14,
        ]
        if len(indices_68) == 68:
            landmarks_68 = landmarks_478[indices_68]
        else:
            # Fallback if mapping is wrong (safety)
            landmarks_68 = landmarks_478[:68]

        # Strip Z for 68 landmarks to maintain compatibility with 2D-only consumers
        landmarks_68 = landmarks_68[:, :2]

        landmarks_68 = transform_points(
            landmarks_68, cv2.invertAffineTransform(rotated_matrix)
        )
        landmarks_68 = transform_points(
            landmarks_68, cv2.invertAffineTransform(affine_matrix)
        )
        landmarks_478 = transform_points(
            landmarks_478, cv2.invertAffineTransform(rotated_matrix)
        )
        landmarks_478 = transform_points(
            landmarks_478, cv2.invertAffineTransform(affine_matrix)
        )

        return landmarks_68, landmarks_478, 1.0  # High confidence for MP
    return None, None, 0.0


def conditional_optimize_contrast(crop_vision_frame: VisionFrame) -> VisionFrame:
    crop_vision_frame = cv2.cvtColor(crop_vision_frame, cv2.COLOR_RGB2Lab)
    if numpy.mean(crop_vision_frame[:, :, 0]) < 30:  # type: ignore[arg-type]
        crop_vision_frame[:, :, 0] = cv2.createCLAHE(clipLimit=2).apply(
            crop_vision_frame[:, :, 0]
        )
    crop_vision_frame = cv2.cvtColor(crop_vision_frame, cv2.COLOR_Lab2RGB)
    return crop_vision_frame


def estimate_face_landmark_68_5(face_landmark_5: FaceLandmark5) -> FaceLandmark68:
    affine_matrix = estimate_matrix_by_face_landmark_5(
        face_landmark_5, "ffhq_512", (1, 1)
    )
    face_landmark_5 = cv2.transform(
        face_landmark_5.reshape(1, -1, 2), affine_matrix
    ).reshape(-1, 2)
    face_landmark_68_5 = forward_fan_68_5(face_landmark_5)
    face_landmark_68_5 = cv2.transform(
        face_landmark_68_5.reshape(1, -1, 2), cv2.invertAffineTransform(affine_matrix)
    ).reshape(-1, 2)
    return face_landmark_68_5


def forward_with_2dfan4(
    crop_vision_frame: VisionFrame,
) -> Tuple[Prediction, Prediction]:
    face_landmarker = get_inference_pool().get("2dfan4")

    with conditional_thread_semaphore():
        prediction = face_landmarker.run(None, {"input": [crop_vision_frame]})

    return prediction


def forward_with_peppa_wutz(crop_vision_frame: VisionFrame) -> Prediction:
    face_landmarker = get_inference_pool().get("peppa_wutz")

    with conditional_thread_semaphore():
        prediction = face_landmarker.run(None, {"input": crop_vision_frame})[0]

    return prediction


def forward_fan_68_5(face_landmark_5: FaceLandmark5) -> FaceLandmark68:
    face_landmarker = get_inference_pool().get("fan_68_5")

    with conditional_thread_semaphore():
        face_landmark_68_5 = face_landmarker.run(None, {"input": [face_landmark_5]})[0][
            0
        ]

    return face_landmark_68_5
