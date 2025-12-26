from typing import Optional, Tuple
import gradio

from facefusion import state_manager, wording
from facefusion.face_store import clear_reference_faces, clear_static_faces
from facefusion.filesystem import is_image, is_video
from facefusion.uis.core import register_ui_component
from facefusion.uis.types import ComponentOptions, File

TARGET_FILE: Optional[gradio.File] = None
TARGET_IMAGE: Optional[gradio.Image] = None
TARGET_VIDEO: Optional[gradio.Video] = None
TARGET_STATUS: Optional[gradio.Textbox] = None


def render() -> None:
    """Render enhanced target upload with better UX"""
    global TARGET_FILE, TARGET_IMAGE, TARGET_VIDEO, TARGET_STATUS

    is_target_image = is_image(state_manager.get_item('target_path'))
    is_target_video = is_video(state_manager.get_item('target_path'))
    
    with gradio.Column():
        gradio.Markdown(
            """
            ### 🎯 Target Media
            Upload the video or image where you want to place the face.
            
            **💡 Tips for best results:**
            - Videos: MP4, MOV, AVI formats work best
            - Images: JPG, PNG for still image face swaps
            - Clear faces in good lighting get better results
            - Shorter videos process faster (under 30 seconds recommended for testing)
            """
        )
        
        TARGET_FILE = gradio.File(
            label="📁 Drop your target video/image here or click to browse",
            file_types=['.mp4', '.mov', '.avi', '.mkv', '.webm', '.jpg', '.jpeg', '.png', '.bmp', '.webp'],
            value=state_manager.get_item('target_path') if is_target_image or is_target_video else None,
            elem_id="enhanced_target_file",
            height=120
        )
        
        # Status indicator
        TARGET_STATUS = gradio.Textbox(
            label="Status",
            value="👆 Upload a target video or image",
            interactive=False,
            lines=1,
            elem_id="target_status"
        )
        
        # Preview containers
        with gradio.Column(visible=is_target_image or is_target_video) as preview_container:
            gradio.Markdown("### 👁️ Preview")
            
            target_image_options: ComponentOptions = {
                'show_label': False,
                'label': "Target image preview",
                'visible': False,
                'height': 300,
                'elem_id': "target_image_preview"
            }
            target_video_options: ComponentOptions = {
                'show_label': False,
                'label': "Target video preview",
                'visible': False,
                'height': 400,
                'elem_id': "target_video_preview"
            }
            
            if is_target_image:
                target_image_options['value'] = TARGET_FILE.value.get('path')
                target_image_options['visible'] = True
            if is_target_video:
                target_video_options['value'] = TARGET_FILE.value.get('path')
                target_video_options['visible'] = True
                
            TARGET_IMAGE = gradio.Image(**target_image_options)
            TARGET_VIDEO = gradio.Video(**target_video_options)

    # Register components
    register_ui_component('enhanced_target_file', TARGET_FILE)
    register_ui_component('enhanced_target_image', TARGET_IMAGE)
    register_ui_component('enhanced_target_video', TARGET_VIDEO)
    register_ui_component('enhanced_target_status', TARGET_STATUS)
    register_ui_component('enhanced_target_preview_container', preview_container)


def listen() -> None:
    """Set up enhanced event listeners with better feedback"""
    if TARGET_FILE and TARGET_STATUS:
        TARGET_FILE.change(
            update_with_feedback,
            inputs=[TARGET_FILE],
            outputs=[TARGET_IMAGE, TARGET_VIDEO, TARGET_STATUS]
        )


def update_with_feedback(file: File) -> Tuple[gradio.Image, gradio.Video, str]:
    """Update target with enhanced user feedback"""
    if not file:
        state_manager.clear_item('target_path')
        clear_reference_faces()
        clear_static_faces()
        return (
            gradio.Image(show_label=False, label="Target image preview", visible=False),
            gradio.Video(show_label=False, label="Target video preview", visible=False),
            "👆 Upload a target video or image"
        )
    
    file_path = file.name
    is_target_image = is_image(file_path)
    is_target_video = is_video(file_path)
    
    if is_target_image or is_target_video:
        state_manager.set_item('target_path', file_path)
        clear_reference_faces()
        clear_static_faces()
        
        # Enhanced status messaging with media info
        if is_target_image:
            status_msg = "✅ Target image loaded! 📸 Ready for face swapping."
        elif is_target_video:
            status_msg = "✅ Target video loaded! 🎬 Ready for face swapping."
        else:
            status_msg = "✅ Target media loaded successfully!"
        
        return (
            gradio.Image(value=file_path, show_label=False, label="Target image preview", visible=is_target_image, height=300),
            gradio.Video(value=file_path, show_label=False, label="Target video preview", visible=is_target_video, height=400),
            status_msg
        )
    else:
        # Error handling with clear message
        file_extension = file_path.split('.')[-1].lower() if '.' in file_path else 'unknown'
        status_msg = f"❌ Unsupported format: .{file_extension}. Please upload MP4, MOV, JPG, PNG, or other supported media files."
        
        return (
            gradio.Image(show_label=False, label="Target image preview", visible=False),
            gradio.Video(show_label=False, label="Target video preview", visible=False),
            status_msg
        )