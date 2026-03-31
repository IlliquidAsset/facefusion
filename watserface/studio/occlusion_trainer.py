"""
Occlusion Trainer - Auto-mask generation and XSeg training management.

Generates occlusion masks using:
1. Convex hull from MediaPipe 478 landmarks (face region)
2. Canny edge detection for boundary refinement
3. Morphological operations for mask cleanup
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple
import json
import os
import time
import uuid

import cv2
import numpy

from watserface import logger
from watserface.filesystem import is_video, resolve_relative_path
from watserface.face_analyser import get_one_face
from watserface.types import Face, FaceLandmark478, VisionFrame


MASK_SET_DIR = resolve_relative_path('../.assets/mask_sets')


@dataclass
class OcclusionMask:
    frame_index: int
    mask: numpy.ndarray
    face_hull: numpy.ndarray
    edge_mask: Optional[numpy.ndarray] = None
    confidence: float = 1.0


@dataclass
class MaskSet:
    id: str
    name: str
    target_path: str
    masks: List[OcclusionMask] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'target_path': self.target_path,
            'created_at': self.created_at,
            'mask_count': len(self.masks)
        }


class OcclusionTrainer:
    
    def __init__(self, mask_set_dir: Optional[str] = None):
        self.mask_set_dir = Path(mask_set_dir or MASK_SET_DIR)
        self.mask_set_dir.mkdir(parents=True, exist_ok=True)
        
        self.frames_per_second = 2
        self.max_masks_per_video = 100
        
        self.canny_low = 50
        self.canny_high = 150
        self.dilation_kernel_size = 5
        self.edge_weight = 0.3
    
    def generate_masks_from_video(
        self,
        name: str,
        video_path: str
    ) -> Generator[Tuple[str, Dict], None, MaskSet]:
        mask_set = MaskSet(
            id=str(uuid.uuid4()),
            name=name,
            target_path=video_path
        )
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            yield f'Failed to open video: {video_path}', {'error': True}
            return mask_set
        
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_interval = max(1, int(fps / self.frames_per_second))
        
        yield f'Processing {total_frames} frames at {fps:.1f} FPS', {
            'total_frames': total_frames,
            'fps': fps
        }
        
        frame_index = 0
        mask_count = 0
        
        while cap.isOpened() and mask_count < self.max_masks_per_video:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_index % frame_interval == 0:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                mask_result = self._generate_mask_for_frame(frame_rgb, frame_index)
                
                if mask_result:
                    mask_set.masks.append(mask_result)
                    mask_count += 1
                    
                    if mask_count % 10 == 0:
                        progress = frame_index / total_frames
                        yield f'Generated {mask_count} masks ({progress:.1%})', {
                            'mask_count': mask_count,
                            'progress': progress
                        }
            
            frame_index += 1
        
        cap.release()
        
        yield f'Mask generation complete: {mask_count} masks', {
            'mask_count': mask_count,
            'mask_set_id': mask_set.id
        }
        
        return mask_set
    
    def generate_mask_for_image(
        self,
        image: VisionFrame,
        frame_index: int = 0
    ) -> Optional[OcclusionMask]:
        return self._generate_mask_for_frame(image, frame_index)
    
    def _generate_mask_for_frame(
        self,
        frame: VisionFrame,
        frame_index: int
    ) -> Optional[OcclusionMask]:
        face = get_one_face([frame])
        if not face:
            return None
        
        landmarks_478 = face.landmark_set.get('478')
        if landmarks_478 is None:
            landmarks_68 = face.landmark_set.get('68')
            if landmarks_68 is None:
                return None
            return self._generate_mask_from_68(frame, face, frame_index)
        
        return self._generate_mask_from_478(frame, face, landmarks_478, frame_index)
    
    def _generate_mask_from_478(
        self,
        frame: VisionFrame,
        face: Face,
        landmarks_478: FaceLandmark478,
        frame_index: int
    ) -> OcclusionMask:
        h, w = frame.shape[:2]
        
        face_oval_indices = [
            10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
            397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
            172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109
        ]
        
        face_oval_pts = landmarks_478[face_oval_indices].astype(numpy.int32)
        
        hull = cv2.convexHull(face_oval_pts)
        
        face_mask = numpy.zeros((h, w), dtype=numpy.uint8)
        cv2.fillConvexPoly(face_mask, hull, 255)
        
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, self.canny_low, self.canny_high)
        
        kernel = numpy.ones((self.dilation_kernel_size, self.dilation_kernel_size), numpy.uint8)
        dilated_edges = cv2.dilate(edges, kernel, iterations=1)
        
        edge_mask_in_face = cv2.bitwise_and(dilated_edges, face_mask)
        
        combined = face_mask.astype(numpy.float32)
        combined -= edge_mask_in_face.astype(numpy.float32) * self.edge_weight
        combined = numpy.clip(combined, 0, 255).astype(numpy.uint8)
        
        kernel_close = numpy.ones((7, 7), numpy.uint8)
        combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel_close)
        
        combined = cv2.GaussianBlur(combined, (5, 5), 0)
        
        return OcclusionMask(
            frame_index=frame_index,
            mask=combined,
            face_hull=hull,
            edge_mask=edge_mask_in_face,
            confidence=1.0
        )
    
    def _generate_mask_from_68(
        self,
        frame: VisionFrame,
        face: Face,
        frame_index: int
    ) -> OcclusionMask:
        h, w = frame.shape[:2]
        
        landmarks_68 = face.landmark_set.get('68', face.landmark_set.get('68/5'))
        if landmarks_68 is None:
            return OcclusionMask(
                frame_index=frame_index,
                mask=numpy.zeros((h, w), dtype=numpy.uint8),
                face_hull=numpy.array([]),
                confidence=0.0
            )
        
        face_contour = landmarks_68[:17]
        eyebrow_left = landmarks_68[17:22]
        eyebrow_right = landmarks_68[22:27]
        
        top_points = numpy.vstack([eyebrow_left, eyebrow_right])
        top_center = numpy.mean(top_points, axis=0)
        forehead_offset = (landmarks_68[27] - top_center) * 0.5
        forehead_point = top_center - forehead_offset
        
        face_outline = numpy.vstack([
            face_contour,
            [forehead_point]
        ]).astype(numpy.int32)
        
        hull = cv2.convexHull(face_outline)
        
        face_mask = numpy.zeros((h, w), dtype=numpy.uint8)
        cv2.fillConvexPoly(face_mask, hull, 255)
        
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, self.canny_low, self.canny_high)
        
        kernel = numpy.ones((self.dilation_kernel_size, self.dilation_kernel_size), numpy.uint8)
        dilated_edges = cv2.dilate(edges, kernel, iterations=1)
        edge_mask_in_face = cv2.bitwise_and(dilated_edges, face_mask)
        
        combined = face_mask.astype(numpy.float32)
        combined -= edge_mask_in_face.astype(numpy.float32) * self.edge_weight
        combined = numpy.clip(combined, 0, 255).astype(numpy.uint8)
        
        kernel_close = numpy.ones((7, 7), numpy.uint8)
        combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel_close)
        combined = cv2.GaussianBlur(combined, (5, 5), 0)
        
        return OcclusionMask(
            frame_index=frame_index,
            mask=combined,
            face_hull=hull,
            edge_mask=edge_mask_in_face,
            confidence=0.8
        )
    
    def save_mask_set(self, mask_set: MaskSet) -> str:
        set_dir = self.mask_set_dir / mask_set.id
        set_dir.mkdir(parents=True, exist_ok=True)
        
        metadata_path = set_dir / 'metadata.json'
        with open(metadata_path, 'w') as f:
            json.dump(mask_set.to_dict(), f, indent=2)
        
        masks_dir = set_dir / 'masks'
        masks_dir.mkdir(exist_ok=True)
        
        for i, mask in enumerate(mask_set.masks):
            mask_path = masks_dir / f'mask_{i:04d}.png'
            cv2.imwrite(str(mask_path), mask.mask)
            
            if mask.edge_mask is not None:
                edge_path = masks_dir / f'edge_{i:04d}.png'
                cv2.imwrite(str(edge_path), mask.edge_mask)
        
        return str(set_dir)
    
    def load_mask_set(self, mask_set_id: str) -> Optional[MaskSet]:
        set_dir = self.mask_set_dir / mask_set_id
        
        if not set_dir.exists():
            return None
        
        metadata_path = set_dir / 'metadata.json'
        if not metadata_path.exists():
            return None
        
        with open(metadata_path, 'r') as f:
            data = json.load(f)
        
        mask_set = MaskSet(
            id=data['id'],
            name=data['name'],
            target_path=data['target_path'],
            created_at=data.get('created_at', time.time())
        )
        
        masks_dir = set_dir / 'masks'
        if masks_dir.exists():
            mask_files = sorted(masks_dir.glob('mask_*.png'))
            
            for i, mask_path in enumerate(mask_files):
                mask_img = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
                if mask_img is None:
                    continue
                
                edge_path = masks_dir / f'edge_{i:04d}.png'
                edge_img = None
                if edge_path.exists():
                    edge_img = cv2.imread(str(edge_path), cv2.IMREAD_GRAYSCALE)
                
                mask_set.masks.append(OcclusionMask(
                    frame_index=i,
                    mask=mask_img,
                    face_hull=numpy.array([]),
                    edge_mask=edge_img,
                    confidence=1.0
                ))
        
        return mask_set
    
    def refine_mask_with_annotation(
        self,
        original_mask: numpy.ndarray,
        annotation_mask: numpy.ndarray,
        mode: str = 'add'
    ) -> numpy.ndarray:
        if mode == 'add':
            return cv2.bitwise_or(original_mask, annotation_mask)
        elif mode == 'subtract':
            return cv2.bitwise_and(original_mask, cv2.bitwise_not(annotation_mask))
        elif mode == 'replace':
            return annotation_mask
        else:
            return original_mask
    
    def get_mask_preview(
        self,
        frame: VisionFrame,
        mask: numpy.ndarray,
        alpha: float = 0.5
    ) -> VisionFrame:
        overlay = frame.copy()
        
        mask_colored = numpy.zeros_like(frame)
        mask_colored[:, :, 0] = mask
        mask_colored[:, :, 2] = 255 - mask
        
        mask_normalized = mask.astype(numpy.float32) / 255.0
        mask_3ch = numpy.stack([mask_normalized] * 3, axis=-1)
        
        blended = (overlay * (1 - alpha * mask_3ch) + mask_colored * alpha * mask_3ch).astype(numpy.uint8)
        
        return blended


def create_occlusion_trainer() -> OcclusionTrainer:
    return OcclusionTrainer()
