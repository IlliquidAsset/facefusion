from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import time

from facefusion import state_manager


@dataclass
class PresetConfig:
    name: str
    display_name: str
    description: str
    estimated_time: str
    face_detector_model: str
    face_swapper_model: str
    face_enhancer_model: Optional[str]
    output_video_resolution: str
    face_enhancer_blend: int
    execution_providers: List[str]
    face_detector_score_threshold: float


class PresetManager:
    """Manages smart presets for simplified user experience"""
    
    SMART_PRESETS: Dict[str, PresetConfig] = {
        "fast": PresetConfig(
            name="fast",
            display_name="🚀 Fast",
            description="Quick draft quality - Great for testing",
            estimated_time="~15 seconds",
            face_detector_model="yolo_face",
            face_swapper_model="inswapper_128",
            face_enhancer_model=None,
            output_video_resolution="720",
            face_enhancer_blend=80,
            execution_providers=["cuda", "cpu"],
            face_detector_score_threshold=0.5
        ),
        "balanced": PresetConfig(
            name="balanced",
            display_name="⚖️ Balanced",
            description="Good quality with reasonable speed",
            estimated_time="~45 seconds",
            face_detector_model="retinaface",
            face_swapper_model="inswapper_128", 
            face_enhancer_model="gfpgan_1_4",
            output_video_resolution="1080",
            face_enhancer_blend=80,
            execution_providers=["cuda", "cpu"],
            face_detector_score_threshold=0.6
        ),
        "quality": PresetConfig(
            name="quality",
            display_name="✨ Quality",
            description="Best quality - Slower processing",
            estimated_time="~90 seconds",
            face_detector_model="retinaface",
            face_swapper_model="inswapper_128",
            face_enhancer_model="codeformer",
            output_video_resolution="source",
            face_enhancer_blend=90,
            execution_providers=["cuda", "cpu"],
            face_detector_score_threshold=0.7
        )
    }
    
    @classmethod
    def get_preset(cls, preset_name: str) -> Optional[PresetConfig]:
        """Get preset configuration by name"""
        return cls.SMART_PRESETS.get(preset_name)
    
    @classmethod
    def get_all_presets(cls) -> Dict[str, PresetConfig]:
        """Get all available presets"""
        return cls.SMART_PRESETS.copy()
    
    @classmethod
    def apply_preset(cls, preset_name: str) -> bool:
        """Apply preset configuration to state manager"""
        preset = cls.get_preset(preset_name)
        if not preset:
            return False
        
        try:
            # Apply face detector settings
            state_manager.init_item('face_detector_model', preset.face_detector_model)
            state_manager.init_item('face_detector_score_threshold', preset.face_detector_score_threshold)
            
            # Apply face swapper settings  
            state_manager.init_item('face_swapper_model', preset.face_swapper_model)
            
            # Apply face enhancer settings
            if preset.face_enhancer_model:
                state_manager.init_item('face_enhancer_model', preset.face_enhancer_model)
                state_manager.init_item('face_enhancer_blend', preset.face_enhancer_blend)
                # Enable face enhancer in processors
                processors = state_manager.get_item('processors') or []
                if 'face_enhancer' not in processors:
                    processors.append('face_enhancer')
                    state_manager.init_item('processors', processors)
            else:
                # Disable face enhancer if None
                processors = state_manager.get_item('processors') or []
                if 'face_enhancer' in processors:
                    processors.remove('face_enhancer')
                    state_manager.init_item('processors', processors)
            
            # Apply output settings
            if preset.output_video_resolution != "source":
                resolution_map = {
                    "720": (1280, 720),
                    "1080": (1920, 1080)
                }
                if preset.output_video_resolution in resolution_map:
                    width, height = resolution_map[preset.output_video_resolution]
                    state_manager.init_item('output_video_resolution', f"{width}x{height}")
            
            # Apply execution providers
            state_manager.init_item('execution_providers', preset.execution_providers)
            
            return True
            
        except Exception as e:
            print(f"Error applying preset {preset_name}: {e}")
            return False
    
    @classmethod
    def get_current_preset_name(cls) -> Optional[str]:
        """Detect which preset is currently active based on settings"""
        current_face_detector = state_manager.get_item('face_detector_model')
        current_face_enhancer = state_manager.get_item('face_enhancer_model')
        processors = state_manager.get_item('processors') or []
        
        for preset_name, preset in cls.SMART_PRESETS.items():
            if (current_face_detector == preset.face_detector_model and
                ((preset.face_enhancer_model is None and 'face_enhancer' not in processors) or
                 (preset.face_enhancer_model and current_face_enhancer == preset.face_enhancer_model))):
                return preset_name
        
        return None
    
    @classmethod
    def estimate_processing_time(cls, preset_name: str, input_duration: float = 10.0) -> str:
        """Estimate processing time based on preset and input duration"""
        preset = cls.get_preset(preset_name)
        if not preset:
            return "Unknown"
        
        # Base multipliers for different presets (seconds per input second)
        time_multipliers = {
            "fast": 1.5,
            "balanced": 4.5, 
            "quality": 9.0
        }
        
        multiplier = time_multipliers.get(preset_name, 4.5)
        estimated_seconds = input_duration * multiplier
        
        if estimated_seconds < 60:
            return f"~{int(estimated_seconds)} seconds"
        else:
            minutes = int(estimated_seconds / 60)
            return f"~{minutes} minute{'s' if minutes > 1 else ''}"


def get_preset_manager() -> PresetManager:
    """Get singleton preset manager instance"""
    return PresetManager()