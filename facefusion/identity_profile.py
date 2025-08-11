"""
Quick Identity Profile System for Multi-Source Face Consistency
Implements intelligent source detection and lightweight identity profiling
"""

import os
import json
import time
import hashlib
import numpy as np
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path
import cv2
from datetime import datetime, timedelta
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity

from facefusion import face_detector, face_recognizer, face_analyser, state_manager, logger, vision
from facefusion.filesystem import is_image, is_video
from facefusion.types import VisionFrame, Embedding, Face


@dataclass
class IdentityProfileConfig:
    """Configuration for identity profile creation"""
    min_images: int = 2
    video_sample_fps: int = 1
    video_max_frames: int = 60
    max_images: int = 20
    min_face_px: int = 256
    pose_yaw_max: float = 30.0
    pose_pitch_max: float = 30.0
    blur_var_min: float = 100.0
    outlier_cosine_thresh: float = 0.35
    save_profiles_by_default: bool = False
    retention_days: int = 30


@dataclass
class QualityMetrics:
    """Quality assessment metrics for a source image"""
    face_size: Tuple[int, int]
    blur_variance: float
    pose_yaw: float
    pose_pitch: float
    confidence_score: float
    is_valid: bool
    rejection_reason: Optional[str] = None


@dataclass
class IdentityProfile:
    """Lightweight identity profile for multi-source consistency"""
    id: str
    name: str
    created_at: str
    source_files: List[str]
    embedding_mean: List[float]
    embedding_std: List[float]
    quality_stats: Dict[str, Any]
    thumbnail_path: Optional[str] = None
    is_ephemeral: bool = True
    last_used: Optional[str] = None
    source_count: int = 0
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'IdentityProfile':
        return cls(**data)
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def get_mean_embedding(self) -> np.ndarray:
        return np.array(self.embedding_mean, dtype=np.float32)
    
    def get_embedding_std(self) -> np.ndarray:
        return np.array(self.embedding_std, dtype=np.float32)


class SourceIntelligence:
    """Intelligent source detection and processing"""
    
    def __init__(self, config: Optional[IdentityProfileConfig] = None):
        self.config = config or IdentityProfileConfig()
        self.profiles_dir = Path("models/identities")
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
    
    def detect_source_mode(self, source_paths: List[str]) -> str:
        """
        Detect whether to use Direct Swap or Create Profile mode
        
        Returns:
            'direct_swap': Single image, use direct face swapping
            'create_profile': Multiple images or video, create identity profile first
        """
        if not source_paths:
            return 'direct_swap'
        
        # Count valid images and videos
        image_count = sum(1 for path in source_paths if is_image(path))
        video_count = sum(1 for path in source_paths if is_video(path))
        
        # Single image -> Direct Swap
        if image_count == 1 and video_count == 0:
            logger.info(f"Single image detected: using Direct Swap mode", __name__)
            return 'direct_swap'
        
        # Multiple images or any video -> Create Profile
        if image_count >= self.config.min_images or video_count > 0:
            logger.info(f"Multi-source detected ({image_count} images, {video_count} videos): using Create Profile mode", __name__)
            return 'create_profile'
        
        # Fallback to direct swap
        logger.info(f"Insufficient sources for profile creation: using Direct Swap mode", __name__)
        return 'direct_swap'
    
    def extract_video_frames(self, video_path: str) -> List[VisionFrame]:
        """Extract frames from video for profile creation"""
        frames = []
        
        try:
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Calculate frame sampling interval
            sample_interval = max(1, int(fps / self.config.video_sample_fps))
            
            frame_count = 0
            extracted_count = 0
            
            logger.info(f"Extracting frames from video: {video_path} (fps={fps}, interval={sample_interval})", __name__)
            
            while cap.isOpened() and extracted_count < self.config.video_max_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                
                if frame_count % sample_interval == 0:
                    frames.append(frame)
                    extracted_count += 1
                
                frame_count += 1
            
            cap.release()
            logger.info(f"Extracted {len(frames)} frames from video", __name__)
            
        except Exception as e:
            logger.error(f"Error extracting video frames: {str(e)}", __name__)
        
        return frames
    
    def assess_image_quality(self, vision_frame: VisionFrame, face: Face) -> QualityMetrics:
        """Assess quality of a source image for profile creation"""
        
        try:
            # Get face bounding box
            bounding_box = face.get('bbox', [0, 0, 256, 256])
            face_width = bounding_box[2] - bounding_box[0]
            face_height = bounding_box[3] - bounding_box[1]
            face_size = (face_width, face_height)
            
            # Check minimum face size
            if face_width < self.config.min_face_px or face_height < self.config.min_face_px:
                return QualityMetrics(
                    face_size=face_size,
                    blur_variance=0.0,
                    pose_yaw=0.0,
                    pose_pitch=0.0,
                    confidence_score=0.0,
                    is_valid=False,
                    rejection_reason=f"Face too small: {face_width}x{face_height} < {self.config.min_face_px}"
                )
            
            # Assess blur using Laplacian variance
            face_crop = vision_frame[int(bounding_box[1]):int(bounding_box[3]), 
                                   int(bounding_box[0]):int(bounding_box[2])]
            gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
            blur_variance = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            if blur_variance < self.config.blur_var_min:
                return QualityMetrics(
                    face_size=face_size,
                    blur_variance=blur_variance,
                    pose_yaw=0.0,
                    pose_pitch=0.0,
                    confidence_score=0.0,
                    is_valid=False,
                    rejection_reason=f"Image too blurry: {blur_variance:.1f} < {self.config.blur_var_min}"
                )
            
            # Get pose estimation (if available in face data)
            pose_yaw = abs(face.get('yaw', 0.0))
            pose_pitch = abs(face.get('pitch', 0.0))
            
            if pose_yaw > self.config.pose_yaw_max or pose_pitch > self.config.pose_pitch_max:
                return QualityMetrics(
                    face_size=face_size,
                    blur_variance=blur_variance,
                    pose_yaw=pose_yaw,
                    pose_pitch=pose_pitch,
                    confidence_score=0.0,
                    is_valid=False,
                    rejection_reason=f"Pose too extreme: yaw={pose_yaw:.1f}°, pitch={pose_pitch:.1f}°"
                )
            
            # Get confidence score
            confidence_score = face.get('confidence', face.get('det_score', 0.5))
            
            return QualityMetrics(
                face_size=face_size,
                blur_variance=blur_variance,
                pose_yaw=pose_yaw,
                pose_pitch=pose_pitch,
                confidence_score=confidence_score,
                is_valid=True
            )
            
        except Exception as e:
            logger.error(f"Error assessing image quality: {str(e)}", __name__)
            return QualityMetrics(
                face_size=(0, 0),
                blur_variance=0.0,
                pose_yaw=0.0,
                pose_pitch=0.0,
                confidence_score=0.0,
                is_valid=False,
                rejection_reason=f"Quality assessment failed: {str(e)}"
            )
    
    def extract_embeddings_from_sources(self, source_paths: List[str]) -> Tuple[List[np.ndarray], List[QualityMetrics]]:
        """Extract embeddings from source images/videos with quality filtering"""
        
        all_embeddings = []
        all_quality_metrics = []
        processed_count = 0
        
        for source_path in source_paths:
            try:
                logger.info(f"Processing source: {source_path}", __name__)
                
                if is_video(source_path):
                    # Extract frames from video
                    frames = self.extract_video_frames(source_path)
                    
                    for frame in frames:
                        faces = face_analyser.get_many_faces(frame)
                        if faces:
                            # Use the largest/most confident face
                            best_face = max(faces, key=lambda f: f.get('confidence', f.get('det_score', 0)))
                            
                            # Assess quality
                            quality = self.assess_image_quality(frame, best_face)
                            all_quality_metrics.append(quality)
                            
                            if quality.is_valid:
                                # Extract embedding
                                face_landmark_5 = best_face.get('kps')
                                if face_landmark_5 is not None:
                                    _, normed_embedding = face_recognizer.calc_embedding(frame, face_landmark_5)
                                    all_embeddings.append(normed_embedding)
                                    processed_count += 1
                            
                            # Limit processing to avoid memory issues
                            if processed_count >= self.config.max_images:
                                break
                    
                elif is_image(source_path):
                    # Process single image
                    vision_frame = vision.read_image(source_path)
                    faces = face_analyser.get_many_faces(vision_frame)
                    
                    if faces:
                        # Use the largest/most confident face
                        best_face = max(faces, key=lambda f: f.get('confidence', f.get('det_score', 0)))
                        
                        # Assess quality
                        quality = self.assess_image_quality(vision_frame, best_face)
                        all_quality_metrics.append(quality)
                        
                        if quality.is_valid:
                            # Extract embedding
                            face_landmark_5 = best_face.get('kps')
                            if face_landmark_5 is not None:
                                _, normed_embedding = face_recognizer.calc_embedding(vision_frame, face_landmark_5)
                                all_embeddings.append(normed_embedding)
                                processed_count += 1
                    else:
                        # No face detected
                        all_quality_metrics.append(QualityMetrics(
                            face_size=(0, 0),
                            blur_variance=0.0,
                            pose_yaw=0.0,
                            pose_pitch=0.0,
                            confidence_score=0.0,
                            is_valid=False,
                            rejection_reason="No face detected in image"
                        ))
                
                # Limit total processing
                if processed_count >= self.config.max_images:
                    logger.info(f"Reached maximum image limit ({self.config.max_images}), stopping processing", __name__)
                    break
                    
            except Exception as e:
                logger.error(f"Error processing source {source_path}: {str(e)}", __name__)
                all_quality_metrics.append(QualityMetrics(
                    face_size=(0, 0),
                    blur_variance=0.0,
                    pose_yaw=0.0,
                    pose_pitch=0.0,
                    confidence_score=0.0,
                    is_valid=False,
                    rejection_reason=f"Processing error: {str(e)}"
                ))
        
        logger.info(f"Extracted {len(all_embeddings)} valid embeddings from {len(source_paths)} sources", __name__)
        return all_embeddings, all_quality_metrics
    
    def remove_outliers(self, embeddings: List[np.ndarray]) -> Tuple[List[np.ndarray], List[int]]:
        """Remove outlier embeddings using clustering and cosine similarity"""
        
        if len(embeddings) <= 2:
            # Not enough embeddings for meaningful outlier detection
            return embeddings, list(range(len(embeddings)))
        
        embeddings_array = np.array(embeddings)
        
        # Calculate pairwise cosine similarities
        similarity_matrix = cosine_similarity(embeddings_array)
        
        # Calculate mean similarity for each embedding
        mean_similarities = np.mean(similarity_matrix, axis=1)
        
        # Find centroid (embedding with highest mean similarity)
        centroid_idx = np.argmax(mean_similarities)
        centroid_embedding = embeddings_array[centroid_idx]
        
        # Calculate distances from centroid
        distances = 1 - cosine_similarity([centroid_embedding], embeddings_array)[0]
        
        # Keep embeddings within threshold
        kept_indices = []
        kept_embeddings = []
        
        for i, distance in enumerate(distances):
            if distance <= self.config.outlier_cosine_thresh:
                kept_indices.append(i)
                kept_embeddings.append(embeddings[i])
        
        removed_count = len(embeddings) - len(kept_embeddings)
        logger.info(f"Outlier removal: kept {len(kept_embeddings)}, removed {removed_count} embeddings", __name__)
        
        return kept_embeddings, kept_indices


    def create_identity_profile(
        self, 
        source_paths: List[str], 
        profile_name: Optional[str] = None,
        save_persistent: bool = False
    ) -> IdentityProfile:
        """Create a Quick Identity Profile from source images/videos"""
        
        start_time = time.time()
        
        # Generate unique profile ID
        source_hash = hashlib.md5(str(sorted(source_paths)).encode()).hexdigest()[:8]
        profile_id = f"profile_{source_hash}_{int(time.time())}"
        
        if not profile_name:
            profile_name = f"Identity_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Creating identity profile: {profile_name} ({profile_id})", __name__)
        
        # Extract embeddings with quality filtering
        embeddings, quality_metrics = self.extract_embeddings_from_sources(source_paths)
        
        if not embeddings:
            raise ValueError("No valid embeddings extracted from source files")
        
        # Remove outliers
        cleaned_embeddings, kept_indices = self.remove_outliers(embeddings)
        
        if not cleaned_embeddings:
            raise ValueError("All embeddings were filtered out as outliers")
        
        # Calculate statistics
        embeddings_array = np.array(cleaned_embeddings)
        embedding_mean = np.mean(embeddings_array, axis=0)
        embedding_std = np.std(embeddings_array, axis=0)
        
        # Quality statistics
        valid_metrics = [q for q in quality_metrics if q.is_valid]
        quality_stats = {
            'total_processed': len(quality_metrics),
            'valid_count': len(valid_metrics),
            'outliers_removed': len(embeddings) - len(cleaned_embeddings),
            'final_embedding_count': len(cleaned_embeddings),
            'avg_face_size': np.mean([q.face_size[0] * q.face_size[1] for q in valid_metrics]) if valid_metrics else 0,
            'avg_blur_variance': np.mean([q.blur_variance for q in valid_metrics]) if valid_metrics else 0,
            'avg_confidence': np.mean([q.confidence_score for q in valid_metrics]) if valid_metrics else 0,
            'processing_time': time.time() - start_time
        }
        
        # Create profile
        profile = IdentityProfile(
            id=profile_id,
            name=profile_name,
            created_at=datetime.now().isoformat(),
            source_files=source_paths.copy(),
            embedding_mean=embedding_mean.tolist(),
            embedding_std=embedding_std.tolist(),
            quality_stats=quality_stats,
            is_ephemeral=not save_persistent,
            source_count=len(source_paths)
        )
        
        # Save if persistent
        if save_persistent:
            self.save_profile(profile)
        
        logger.info(f"Identity profile created successfully: {len(cleaned_embeddings)} embeddings, {quality_stats['processing_time']:.2f}s", __name__)
        
        return profile
    
    def save_profile(self, profile: IdentityProfile) -> None:
        """Save identity profile to disk"""
        
        profile_dir = self.profiles_dir / profile.id
        profile_dir.mkdir(parents=True, exist_ok=True)
        
        profile_file = profile_dir / "profile.json"
        
        with open(profile_file, 'w') as f:
            json.dump(profile.to_dict(), f, indent=2)
        
        logger.info(f"Saved identity profile to {profile_file}", __name__)
    
    def load_profile(self, profile_id: str) -> Optional[IdentityProfile]:
        """Load identity profile from disk"""
        
        profile_file = self.profiles_dir / profile_id / "profile.json"
        
        if not profile_file.exists():
            return None
        
        try:
            with open(profile_file, 'r') as f:
                data = json.load(f)
            
            profile = IdentityProfile.from_dict(data)
            
            # Update last used
            profile.last_used = datetime.now().isoformat()
            self.save_profile(profile)
            
            return profile
            
        except Exception as e:
            logger.error(f"Error loading profile {profile_id}: {str(e)}", __name__)
            return None
    
    def list_profiles(self, include_ephemeral: bool = False) -> List[IdentityProfile]:
        """List all available identity profiles"""
        
        profiles = []
        
        for profile_dir in self.profiles_dir.iterdir():
            if profile_dir.is_dir():
                profile = self.load_profile(profile_dir.name)
                if profile and (include_ephemeral or not profile.is_ephemeral):
                    profiles.append(profile)
        
        # Sort by creation date (newest first)
        profiles.sort(key=lambda p: p.created_at, reverse=True)
        
        return profiles
    
    def delete_profile(self, profile_id: str) -> bool:
        """Delete an identity profile"""
        
        profile_dir = self.profiles_dir / profile_id
        
        if not profile_dir.exists():
            return False
        
        try:
            import shutil
            shutil.rmtree(profile_dir)
            logger.info(f"Deleted identity profile: {profile_id}", __name__)
            return True
            
        except Exception as e:
            logger.error(f"Error deleting profile {profile_id}: {str(e)}", __name__)
            return False
    
    def cleanup_expired_profiles(self) -> int:
        """Clean up expired ephemeral profiles"""
        
        cleaned_count = 0
        cutoff_date = datetime.now() - timedelta(days=self.config.retention_days)
        
        for profile in self.list_profiles(include_ephemeral=True):
            if profile.is_ephemeral:
                created_date = datetime.fromisoformat(profile.created_at)
                if created_date < cutoff_date:
                    if self.delete_profile(profile.id):
                        cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} expired ephemeral profiles", __name__)
        
        return cleaned_count


class IdentityProfileManager:
    """High-level manager for identity profiles and source intelligence"""
    
    def __init__(self):
        self.source_intelligence = SourceIntelligence()
        self.current_profile: Optional[IdentityProfile] = None
    
    def process_sources(
        self, 
        source_paths: List[str], 
        force_mode: Optional[str] = None,
        profile_name: Optional[str] = None,
        save_persistent: bool = False
    ) -> Tuple[str, Optional[IdentityProfile]]:
        """
        Process source files and return processing mode and profile
        
        Args:
            source_paths: List of source file paths
            force_mode: Override auto-detection ('direct_swap' or 'create_profile')
            profile_name: Name for the profile (if creating)
            save_persistent: Whether to save profile persistently
            
        Returns:
            Tuple of (processing_mode, identity_profile)
        """
        
        if not source_paths:
            return 'direct_swap', None
        
        # Determine processing mode
        if force_mode:
            processing_mode = force_mode
        else:
            processing_mode = self.source_intelligence.detect_source_mode(source_paths)
        
        # Create profile if needed
        profile = None
        if processing_mode == 'create_profile':
            try:
                profile = self.source_intelligence.create_identity_profile(
                    source_paths, 
                    profile_name, 
                    save_persistent
                )
                self.current_profile = profile
                
            except Exception as e:
                logger.error(f"Failed to create identity profile: {str(e)}, falling back to direct swap", __name__)
                processing_mode = 'direct_swap'
                profile = None
        
        return processing_mode, profile
    
    def get_current_profile(self) -> Optional[IdentityProfile]:
        """Get the currently active identity profile"""
        return self.current_profile
    
    def clear_current_profile(self) -> None:
        """Clear the currently active identity profile"""
        self.current_profile = None
    
    def get_profile_summary(self, profile: IdentityProfile) -> str:
        """Get a human-readable summary of a profile"""
        
        stats = profile.quality_stats
        
        return f"""
Profile: {profile.name}
- Sources: {stats['total_processed']} files → {stats['final_embedding_count']} valid embeddings
- Quality: {stats['avg_confidence']:.2f} avg confidence, {stats['avg_blur_variance']:.1f} blur variance
- Processing: {stats['processing_time']:.1f}s ({stats['outliers_removed']} outliers removed)
- Created: {profile.created_at}
"""


# Global instance
_identity_manager = IdentityProfileManager()


def get_source_intelligence() -> SourceIntelligence:
    """Get singleton source intelligence instance"""
    return SourceIntelligence()


def get_identity_manager() -> IdentityProfileManager:
    """Get singleton identity profile manager"""
    return _identity_manager