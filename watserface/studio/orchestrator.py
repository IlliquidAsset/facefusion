from typing import Any, Dict, Generator, List, Optional, Tuple
import os
import time

from watserface import state_manager, logger
from watserface.filesystem import is_video, is_image, has_audio
from watserface.studio.state import StudioState, StudioPhase, IdentityProfile, OcclusionProfile, FaceMapping
from watserface.studio.identity_builder import IdentityBuilder, create_identity_builder
from watserface.training import core as training_core


class StudioOrchestrator:
    
    def __init__(self):
        self.state = StudioState()
        self.identity_builder = create_identity_builder()
        self._scan_workspace()

    def _scan_workspace(self):
        """Scan workspace for existing face sets and identities."""
        try:
            face_sets = self.identity_builder.list_face_sets()
            for fs_data in face_sets:
                name = fs_data.get('name', 'Unknown')
                fs_id = fs_data.get('id')

                if name not in self.state.identities:
                    identity = self.state.add_identity(name)
                    identity.face_set_id = fs_id

                    # Check for existing trained model
                    set_dir = self.identity_builder.face_set_dir / fs_id
                    if set_dir.exists():
                        # Look for model files
                        controlnets = []
                        pths = []
                        safetensors = []

                        try:
                            with os.scandir(set_dir) as it:
                                for entry in it:
                                    name = entry.name
                                    if name.endswith('_controlnet'):
                                        controlnets.append(entry)
                                    elif name.endswith('.pth'):
                                        pths.append(entry)
                                    elif name.endswith('.safetensors'):
                                        safetensors.append(entry)
                        except OSError:
                            pass

                        potential_models = controlnets + pths + safetensors

                        for entry in potential_models:
                            if entry.is_dir() or entry.is_file():
                                identity.model_path = entry.path
                                identity.epochs_trained = 100  # Assume trained
                                break

                    self.state.log(f"Recovered identity '{name}' from workspace")
        except Exception as e:
            logger.warn(f"Workspace scan failed: {e}", __name__)

    def add_identity_media(self, name: str, files: List[Any]) -> Generator[Tuple[str, Dict], None, None]:
        paths = self._normalize_paths(files)
        if not paths:
            yield self.state.log('No valid files provided'), {}
            return
        
        identity = self.state.add_identity(name, paths)
        yield self.state.log(f'Added {len(paths)} files to identity "{name}"'), {'identity': name, 'count': len(identity.source_paths)}
    
    def extract_faces(self, name: str) -> Generator[Tuple[str, Dict], None, None]:
        identity = self.state.get_identity(name)
        if not identity:
            yield self.state.log(f'Identity "{name}" not found'), {}
            return
        
        if not identity.source_paths:
            yield self.state.log(f'Identity "{name}" has no source media'), {}
            return
        
        self.state.phase = StudioPhase.IDENTITY_BUILDING
        yield self.state.log(f'Extracting faces for identity "{name}"...'), {}
        
        face_set_id = None
        
        for msg, data in self.identity_builder.extract_from_sources(name, identity.source_paths):
            yield self.state.log(msg), data
            if data.get('face_set_id'):
                face_set_id = data['face_set_id']
        
        if face_set_id:
            identity.face_set_id = face_set_id
            yield self.state.log(f'Face set created: {face_set_id}'), {'face_set_id': face_set_id}
        
        self.state.phase = StudioPhase.IDLE
    
    def train_identity(self, name: str, epochs: int = 100, continue_training: bool = False) -> Generator[Tuple[str, Dict], None, None]:
        identity = self.state.get_identity(name)
        if not identity:
            yield self.state.log(f'Identity "{name}" not found'), {}
            return
        
        if not identity.source_paths and not identity.face_set_id:
            yield self.state.log(f'Identity "{name}" has no source media'), {}
            return
        
        self.state.phase = StudioPhase.IDENTITY_BUILDING
        yield self.state.log(f'Starting identity training for "{name}" ({epochs} epochs)'), {}
        
        start_epoch = identity.epochs_trained if continue_training else 0
        
        kwargs = {
            'model_name': name,
            'epochs': epochs,
        }
        
        if identity.face_set_id:
            kwargs['face_set_id'] = identity.face_set_id
        else:
            kwargs['source_files'] = identity.source_paths
            kwargs['save_as_face_set'] = True
        
        telemetry = {}
        for status in training_core.start_identity_training(**kwargs):
            if isinstance(status, list) and len(status) >= 2:
                msg, telemetry = status[0], status[1]
            else:
                msg = str(status)
            yield self.state.log(f'[Identity] {msg}'), telemetry
        
        if telemetry.get('model_path'):
            identity.model_path = telemetry['model_path']
            identity.epochs_trained = start_epoch + epochs
            if telemetry.get('final_loss'):
                identity.last_loss = float(telemetry['final_loss'])
            yield self.state.log(f'Identity "{name}" trained: {identity.model_path}'), telemetry
        
        self.state.phase = StudioPhase.IDLE
    
    def set_target(self, file: Any) -> Generator[Tuple[str, Dict], None, None]:
        paths = self._normalize_paths([file])
        if not paths:
            yield self.state.log('No valid target file'), {}
            return
        
        self.state.target_path = paths[0]
        
        info = {'path': self.state.target_path, 'is_video': False, 'has_audio': False}
        if is_video(self.state.target_path):
            info['is_video'] = True
            info['has_audio'] = has_audio(self.state.target_path)
        
        yield self.state.log(f'Target set: {os.path.basename(self.state.target_path)}'), info
    
    def train_occlusion(self, name: str, epochs: int = 50) -> Generator[Tuple[str, Dict], None, None]:
        if not self.state.target_path:
            yield self.state.log('No target set for occlusion training'), {}
            return
        
        occlusion = self.state.add_occlusion(name, self.state.target_path)
        self.state.phase = StudioPhase.OCCLUSION_TRAINING
        yield self.state.log(f'Starting occlusion training for "{name}" ({epochs} epochs)'), {}
        
        telemetry = {}
        for status in training_core.start_occlusion_training(
            model_name=name,
            epochs=epochs,
            target_file=self.state.target_path
        ):
            if isinstance(status, list) and len(status) >= 2:
                msg, telemetry = status[0], status[1]
            else:
                msg = str(status)
            yield self.state.log(f'[Occlusion] {msg}'), telemetry
        
        if telemetry.get('model_path'):
            occlusion.model_path = telemetry['model_path']
            occlusion.epochs_trained = epochs
            yield self.state.log(f'Occlusion model "{name}" trained: {occlusion.model_path}'), telemetry
        
        self.state.phase = StudioPhase.IDLE
    
    def auto_map_faces(self) -> Generator[Tuple[str, Dict], None, None]:
        if not self.state.target_path:
            yield self.state.log('No target set'), {}
            return
        
        if not self.state.identities:
            yield self.state.log('No identities defined'), {}
            return
        
        self.state.phase = StudioPhase.MAPPING
        yield self.state.log('Analyzing target for face mapping...'), {}
        
        from watserface.face_analyser import get_many_faces
        from watserface.vision import read_static_image, read_static_images
        
        if is_video(self.state.target_path):
            from watserface.ffmpeg import extract_frames
            from watserface.temp_helper import get_temp_directory_path, create_temp_directory, clear_temp_directory

            create_temp_directory(self.state.target_path)
            if not extract_frames(self.state.target_path, '640x480', 30.0, 0, 1):
                yield self.state.log('Could not extract frame from video'), {}
                return

            temp_dir = get_temp_directory_path(self.state.target_path)
            frame_path = os.path.join(temp_dir, '00000001.png')
            if os.path.exists(frame_path):
                frame = read_static_image(frame_path)
                clear_temp_directory(self.state.target_path)
            else:
                yield self.state.log('Could not find extracted frame'), {}
                clear_temp_directory(self.state.target_path)
                return
        else:
            frame = read_static_image(self.state.target_path)
        
        faces = get_many_faces([frame])
        if not faces:
            yield self.state.log('No faces detected in target'), {}
            return
        
        yield self.state.log(f'Detected {len(faces)} face(s) in target'), {'face_count': len(faces)}
        
        self.state.mappings.clear()
        identity_names = list(self.state.identities.keys())
        
        for i, face in enumerate(faces):
            if i < len(identity_names):
                mapping = FaceMapping(
                    source_identity=identity_names[i],
                    target_face_index=i,
                    confidence=float(face.score_set.get('detector', 0.0)) if face.score_set else 0.0
                )
                self.state.mappings.append(mapping)
                yield self.state.log(f'Mapped face {i} -> identity "{identity_names[i]}"'), {}
        
        self.state.phase = StudioPhase.IDLE
    
    def preview(self, frame_number: int = 0) -> Generator[Tuple[str, Any], None, None]:
        if not self.state.target_path or not self.state.mappings:
            yield self.state.log('Cannot preview: missing target or mappings'), None
            return
        
        yield self.state.log('Generating preview frame...'), None
        
        self._configure_processors()
        
        from watserface.vision import read_static_image
        from watserface.core import process_preview_frame
        
        if is_video(self.state.target_path):
            from watserface.ffmpeg import extract_frames
            from watserface.temp_helper import get_temp_directory_path, create_temp_directory, clear_temp_directory

            create_temp_directory(self.state.target_path)
            if not extract_frames(self.state.target_path, '640x480', 30.0, frame_number, frame_number + 1):
                yield self.state.log('Could not extract preview frame'), None
                return

            temp_dir = get_temp_directory_path(self.state.target_path)
            # When extracting a single frame, it's always saved as 00000001.png (first output frame)
            frame_path = os.path.join(temp_dir, '00000001.png')
            if os.path.exists(frame_path):
                frame = read_static_image(frame_path)
                clear_temp_directory(self.state.target_path)
            else:
                yield self.state.log('Could not find extracted preview frame'), None
                clear_temp_directory(self.state.target_path)
                return
        else:
            frame = read_static_image(self.state.target_path)
        
        result = process_preview_frame(frame)
        
        for mapping in self.state.mappings:
            mapping.quality_score = self._estimate_quality(result, mapping)
        
        low_quality = [m for m in self.state.mappings if m.quality_score < self.state.quality_threshold]
        if low_quality and self.state.auto_train_on_low_quality:
            yield self.state.log(f'Quality below threshold for {len(low_quality)} mapping(s). Consider more training.'), result
        else:
            yield self.state.log('Preview generated'), result
    
    def execute(self) -> Generator[Tuple[str, Any], None, None]:
        if not self.state.target_path or not self.state.mappings:
            yield self.state.log('Cannot execute: missing target or mappings'), None
            return
        
        self.state.phase = StudioPhase.EXECUTING
        yield self.state.log('Starting full execution...'), None
        
        self._configure_processors()
        
        output_dir = state_manager.get_item('output_path') or 'output'
        if not os.path.isdir(output_dir):
            output_dir = os.path.dirname(output_dir) or 'output'
        os.makedirs(output_dir, exist_ok=True)
        
        base_name = os.path.basename(self.state.target_path)
        name, ext = os.path.splitext(base_name)
        timestamp = int(time.time())
        self.state.output_path = os.path.join(output_dir, f'{name}_studio_{timestamp}{ext}')
        
        state_manager.set_item('output_path', self.state.output_path)
        
        from watserface.core import process_video, process_image
        
        start_time = time.time()
        
        try:
            if is_video(self.state.target_path):
                error_code = process_video(start_time)
            else:
                error_code = process_image(start_time)
        except Exception as e:
            yield self.state.log(f'Execution failed: {e}'), None
            self.state.phase = StudioPhase.IDLE
            return
        
        if error_code == 0:
            self.state.phase = StudioPhase.REVIEWING
            yield self.state.log(f'Execution complete: {self.state.output_path}'), self.state.output_path
        else:
            yield self.state.log(f'Execution finished with error code {error_code}'), None
            self.state.phase = StudioPhase.IDLE
    
    def _normalize_paths(self, files: List[Any]) -> List[str]:
        paths = []
        for f in files:
            if f is None:
                continue
            if hasattr(f, 'name'):
                paths.append(f.name)
            elif isinstance(f, str) and os.path.exists(f):
                paths.append(f)
        return paths
    
    def _configure_processors(self) -> None:
        processors = ['face_swapper']
        
        has_trained_identity = any(i.model_path for i in self.state.identities.values())
        has_trained_occlusion = any(o.model_path for o in self.state.occlusions.values())
        
        if has_trained_identity:
            identity = next((i for i in self.state.identities.values() if i.model_path), None)
            if identity:
                state_manager.set_item('face_swapper_model', os.path.basename(identity.model_path))
        
        if has_trained_occlusion:
            occlusion = next((o for o in self.state.occlusions.values() if o.model_path), None)
            if occlusion:
                state_manager.set_item('face_occluder_model', os.path.basename(occlusion.model_path))
                mask_types = state_manager.get_item('face_mask_types') or []
                if 'occlusion' not in mask_types:
                    mask_types.append('occlusion')
                    state_manager.set_item('face_mask_types', mask_types)
        
        processors.append('face_enhancer')
        state_manager.set_item('face_enhancer_model', 'codeformer')
        state_manager.set_item('face_enhancer_blend', 100)
        
        if self.state.target_path and is_video(self.state.target_path) and has_audio(self.state.target_path):
            processors.append('lip_syncer')
        
        state_manager.set_item('processors', processors)
        
        for mapping in self.state.mappings:
            identity = self.state.identities.get(mapping.source_identity)
            if identity and identity.source_paths:
                state_manager.set_item('source_paths', identity.source_paths)
                break
        
        state_manager.set_item('target_path', self.state.target_path)
    
    def _estimate_quality(self, frame: Any, mapping: FaceMapping) -> float:
        return 0.85
