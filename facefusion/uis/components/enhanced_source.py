from typing import List, Optional, Tuple
import gradio

from facefusion import state_manager, wording, logger
from facefusion.common_helper import get_first
from facefusion.filesystem import filter_audio_paths, filter_image_paths, has_audio, has_image
from facefusion.uis.core import register_ui_component
from facefusion.uis.types import File
from facefusion.identity_profile import get_identity_manager

SOURCE_FILE: Optional[gradio.File] = None
SOURCE_AUDIO: Optional[gradio.Audio] = None
SOURCE_IMAGE: Optional[gradio.Image] = None
SOURCE_STATUS: Optional[gradio.Textbox] = None
SOURCE_MODE_CHIP: Optional[gradio.HTML] = None
SOURCE_PROFILE_INFO: Optional[gradio.Markdown] = None
FORCE_MODE_TOGGLE: Optional[gradio.Radio] = None


def render() -> None:
    """Render enhanced source upload with intelligent multi-source support"""
    global SOURCE_FILE, SOURCE_AUDIO, SOURCE_IMAGE, SOURCE_STATUS, SOURCE_MODE_CHIP, SOURCE_PROFILE_INFO, FORCE_MODE_TOGGLE

    has_source_audio = has_audio(state_manager.get_item('source_paths'))
    has_source_image = has_image(state_manager.get_item('source_paths'))
    
    # Enhanced file upload with intelligent multi-source support
    with gradio.Column():
        gradio.Markdown(
            """
            ### 📸 Source Face(s) - Smart Detection
            Upload photos or video of the person whose face you want to use.
            
            **🎯 Smart Modes:**
            - **Single Image** → Direct face swapping
            - **Multiple Images/Video** → Create identity profile for consistency
            
            **💡 Tips for best results:**
            - Use front-facing, well-lit photos
            - 3-10 images recommended for identity profiles  
            - Higher resolution images work better
            - Avoid sunglasses, masks, or extreme angles
            """
        )
        
        SOURCE_FILE = gradio.File(
            label="📁 Drop source photos/video here or click to browse (supports multiple files)",
            file_count='multiple',
            file_types=['.jpg', '.jpeg', '.png', '.bmp', '.webp', '.mp4', '.mov', '.avi', '.mkv'],
            value=state_manager.get_item('source_paths') if has_source_audio or has_source_image else None,
            elem_id="enhanced_source_file",
            height=120
        )
        
        # Processing mode indicator
        SOURCE_MODE_CHIP = gradio.HTML(
            """
            <div style="display: inline-block; padding: 4px 8px; background: #e3f2fd; border: 1px solid #2196F3; border-radius: 16px; font-size: 12px; color: #1976D2; margin: 8px 0;">
                🎯 Ready for Upload
            </div>
            """,
            elem_id="source_mode_chip"
        )
        
        # Advanced mode override
        with gradio.Accordion("🔧 Advanced: Override Auto-Detection", open=False):
            FORCE_MODE_TOGGLE = gradio.Radio(
                choices=[
                    ("🎯 Auto-Detect (Recommended)", "auto"),
                    ("📷 Force Direct Swap", "direct_swap"), 
                    ("👥 Force Create Profile", "create_profile")
                ],
                value="auto",
                label="Processing Mode",
                info="Override intelligent source detection"
            )
        
        # Status indicator
        SOURCE_STATUS = gradio.Textbox(
            label="Status",
            value="👆 Upload source images or video to get started",
            interactive=False,
            lines=2,
            elem_id="source_status"
        )
        
        # Identity profile information
        SOURCE_PROFILE_INFO = gradio.Markdown(
            "",
            visible=False,
            elem_id="source_profile_info"
        )
        
        # Preview containers
        source_file_names = [source_file_value.get('path') for source_file_value in SOURCE_FILE.value] if SOURCE_FILE.value else None
        source_audio_path = get_first(filter_audio_paths(source_file_names))
        source_image_path = get_first(filter_image_paths(source_file_names))
        
        with gradio.Column(visible=has_source_image or has_source_audio) as preview_container:
            gradio.Markdown("### 👁️ Preview")
            
            SOURCE_AUDIO = gradio.Audio(
                value=source_audio_path if has_source_audio else None,
                visible=has_source_audio,
                show_label=False,
                label="Source audio preview",
                elem_id="source_audio_preview"
            )
            
            SOURCE_IMAGE = gradio.Image(
                value=source_image_path if has_source_image else None,
                visible=has_source_image,
                show_label=False,
                label="Source image preview",
                height=300,
                elem_id="source_image_preview"
            )

    # Register components
    register_ui_component('enhanced_source_file', SOURCE_FILE)
    register_ui_component('enhanced_source_audio', SOURCE_AUDIO)
    register_ui_component('enhanced_source_image', SOURCE_IMAGE)
    register_ui_component('enhanced_source_status', SOURCE_STATUS)
    register_ui_component('enhanced_source_preview_container', preview_container)


def listen() -> None:
    """Set up enhanced event listeners with identity profile integration"""
    if SOURCE_FILE and SOURCE_STATUS:
        SOURCE_FILE.change(
            update_with_feedback, 
            inputs=[SOURCE_FILE], 
            outputs=[SOURCE_AUDIO, SOURCE_IMAGE, SOURCE_STATUS]
        )
        
        # Also update mode chip and profile info when files change
        if SOURCE_MODE_CHIP and SOURCE_PROFILE_INFO:
            SOURCE_FILE.change(
                update_mode_indicators,
                inputs=[SOURCE_FILE, FORCE_MODE_TOGGLE],
                outputs=[SOURCE_MODE_CHIP, SOURCE_PROFILE_INFO]
            )
        
        # Listen to force mode toggle changes
        if FORCE_MODE_TOGGLE:
            FORCE_MODE_TOGGLE.change(
                update_mode_indicators,
                inputs=[SOURCE_FILE, FORCE_MODE_TOGGLE], 
                outputs=[SOURCE_MODE_CHIP, SOURCE_PROFILE_INFO]
            )


def update_with_feedback(files: List[File]) -> Tuple[gradio.Audio, gradio.Image, str]:
    """Update source with enhanced user feedback and identity profile processing"""
    if not files:
        state_manager.clear_item('source_paths')
        get_identity_manager().clear_current_profile()
        return (
            gradio.Audio(value=None, visible=False),
            gradio.Image(value=None, visible=False),
            "👆 Upload source images or video to get started"
        )
    
    file_names = [file.name for file in files]
    has_source_audio = has_audio(file_names)
    has_source_image = has_image(file_names)
    
    if has_source_image or has_source_audio:
        source_audio_path = get_first(filter_audio_paths(file_names))
        source_image_path = get_first(filter_image_paths(file_names))
        state_manager.set_item('source_paths', file_names)
        
        # Process with identity profile system
        try:
            identity_manager = get_identity_manager()
            
            # Get force mode from UI (if available)
            force_mode = None  # Will be updated when we integrate with FORCE_MODE_TOGGLE
            
            # Process sources through identity intelligence
            processing_mode, profile = identity_manager.process_sources(
                file_names, 
                force_mode=force_mode,
                save_persistent=False  # Default to ephemeral
            )
            
            # Enhanced status messaging with processing mode info
            file_count = len(file_names)
            if processing_mode == 'direct_swap':
                status_msg = f"✅ Single source loaded → 🎯 Direct Swap mode ready"
            else:
                if profile:
                    embeddings_count = profile.quality_stats.get('final_embedding_count', 0)
                    processing_time = profile.quality_stats.get('processing_time', 0)
                    status_msg = f"✅ Identity profile created from {file_count} sources → 👥 Profile mode ready\n"
                    status_msg += f"📊 {embeddings_count} embeddings processed in {processing_time:.1f}s"
                else:
                    status_msg = f"⚠️ Profile creation failed → 🎯 Fallback to Direct Swap mode"
            
            if has_source_audio:
                status_msg += f"\n🎵 Audio track detected"
            
        except Exception as e:
            logger.error(f"Identity profile processing failed: {str(e)}", __name__)
            status_msg = f"✅ Sources loaded → 🎯 Direct Swap mode (profile processing unavailable)"
        
        return (
            gradio.Audio(value=source_audio_path, visible=has_source_audio),
            gradio.Image(value=source_image_path, visible=has_source_image),
            status_msg
        )
    else:
        # Error handling with clear message
        unsupported_files = [file.name.split('.')[-1] for file in files]
        status_msg = f"❌ Unsupported file format: {', '.join(unsupported_files)}. Please upload JPG, PNG, MP4, or other supported files."
        
        return (
            gradio.Audio(value=None, visible=False),
            gradio.Image(value=None, visible=False),
            status_msg
        )


def update_mode_indicators(files: List[File], force_mode: str) -> Tuple[str, str]:
    """Update mode chip and profile information display"""
    if not files:
        mode_chip_html = """
        <div style="display: inline-block; padding: 4px 8px; background: #e3f2fd; border: 1px solid #2196F3; border-radius: 16px; font-size: 12px; color: #1976D2; margin: 8px 0;">
            🎯 Ready for Upload
        </div>
        """
        return mode_chip_html, ""
    
    try:
        file_names = [file.name for file in files]
        identity_manager = get_identity_manager()
        
        # Determine processing mode
        if force_mode and force_mode != "auto":
            processing_mode = force_mode
            mode_source = "Manual Override"
        else:
            processing_mode = identity_manager.source_intelligence.detect_source_mode(file_names)
            mode_source = "Auto-Detected"
        
        # Create mode chip based on processing mode
        if processing_mode == 'direct_swap':
            mode_chip_html = """
            <div style="display: inline-block; padding: 4px 8px; background: #e8f5e8; border: 1px solid #4caf50; border-radius: 16px; font-size: 12px; color: #2e7d32; margin: 8px 0;">
                🎯 Direct Swap Mode
            </div>
            """
        else:
            mode_chip_html = """
            <div style="display: inline-block; padding: 4px 8px; background: #fff3e0; border: 1px solid #ff9800; border-radius: 16px; font-size: 12px; color: #f57c00; margin: 8px 0;">
                👥 Identity Profile Mode
            </div>
            """
        
        # Get current profile info if available
        profile_info = ""
        current_profile = identity_manager.get_current_profile()
        if current_profile:
            profile_summary = identity_manager.get_profile_summary(current_profile)
            profile_info = f"### 🆔 Active Profile\n\n```\n{profile_summary}\n```"
        elif processing_mode == 'create_profile' and len(file_names) > 1:
            profile_info = f"### 📋 Profile Creation Pending\n\n- **Sources**: {len(file_names)} files ready for processing\n- **Mode**: {mode_source}\n- Profile will be created when processing starts"
        
        return mode_chip_html, profile_info
        
    except Exception as e:
        logger.error(f"Error updating mode indicators: {str(e)}", __name__)
        mode_chip_html = """
        <div style="display: inline-block; padding: 4px 8px; background: #ffebee; border: 1px solid #f44336; border-radius: 16px; font-size: 12px; color: #c62828; margin: 8px 0;">
            ⚠️ Mode Detection Error
        </div>
        """
        return mode_chip_html, ""