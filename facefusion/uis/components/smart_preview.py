import gradio
from typing import Any, Optional, List, Tuple
import tempfile
import os

from facefusion import state_manager, vision
from facefusion.preset_manager import PresetManager, PresetConfig
from facefusion.uis.core import get_ui_component, register_ui_component
from facefusion.uis.types import ComponentName
from facefusion import wording


def render() -> None:
    """Render smart preview component with preset selection"""
    
    # Preview selection radio buttons
    preset_choices = []
    preset_labels = []
    preset_descriptions = []
    
    for preset_name, preset_config in PresetManager.get_all_presets().items():
        preset_choices.append(preset_name)
        preset_labels.append(preset_config.display_name)
        preset_descriptions.append(f"{preset_config.description} ({preset_config.estimated_time})")
    
    # Main preset selector
    with gradio.Row():
        preset_selector = gradio.Radio(
            choices=[(f"{preset_labels[i]} - {preset_descriptions[i]}", preset_choices[i]) 
                    for i in range(len(preset_choices))],
            value="balanced",
            label="🎯 Quality Preset",
            info="Choose your preferred balance of speed vs quality",
            elem_id="smart_preview_selector"
        )
    
    # Preview generation section  
    with gradio.Row():
        generate_previews_button = gradio.Button(
            value="🔍 Generate Preview Options",
            variant="primary",
            size="lg"
        )
    
    # Preview results display
    with gradio.Row(visible=False) as preview_results_row:
        with gradio.Column(scale=1):
            preview_fast = gradio.Image(
                label="🚀 Fast Preview",
                show_label=True,
                interactive=False
            )
            select_fast_button = gradio.Button(
                value="Select Fast",
                variant="secondary",
                size="sm"
            )
        
        with gradio.Column(scale=1):
            preview_balanced = gradio.Image(
                label="⚖️ Balanced Preview", 
                show_label=True,
                interactive=False
            )
            select_balanced_button = gradio.Button(
                value="Select Balanced",
                variant="secondary", 
                size="sm"
            )
        
        with gradio.Column(scale=1):
            preview_quality = gradio.Image(
                label="✨ Quality Preview",
                show_label=True,
                interactive=False
            )
            select_quality_button = gradio.Button(
                value="Select Quality",
                variant="secondary",
                size="sm"
            )
    
    # Processing status
    preview_status = gradio.Textbox(
        label="Preview Status",
        value="Ready to generate previews",
        interactive=False,
        lines=1
    )
    
    # Advanced settings toggle
    with gradio.Row():
        advanced_toggle = gradio.Checkbox(
            label="🔧 Show Advanced Settings",
            value=False,
            info="Toggle technical parameters for power users"
        )
    
    # Advanced settings (initially hidden)
    with gradio.Accordion("⚙️ Advanced Settings", open=False, visible=False) as advanced_settings:
        advanced_info = gradio.Markdown(
            """
            **Advanced users can fine-tune these settings:**
            - Face Detector Model: Controls face detection accuracy
            - Face Enhancer Model: Controls face quality enhancement
            - Processing Resolution: Higher = better quality, slower speed
            - Detection Threshold: Higher = more selective face detection
            """
        )
    
    # Register components for external access
    register_ui_component('smart_preview_selector', preset_selector)
    register_ui_component('smart_preview_generate', generate_previews_button)
    register_ui_component('smart_preview_results', preview_results_row)
    register_ui_component('smart_preview_status', preview_status)
    register_ui_component('smart_preview_advanced_toggle', advanced_toggle)
    register_ui_component('smart_preview_advanced_settings', advanced_settings)
    
    # Store preview buttons for event handling
    register_ui_component('smart_preview_fast', preview_fast)
    register_ui_component('smart_preview_balanced', preview_balanced)
    register_ui_component('smart_preview_quality', preview_quality)
    register_ui_component('smart_preview_select_fast', select_fast_button)
    register_ui_component('smart_preview_select_balanced', select_balanced_button)
    register_ui_component('smart_preview_select_quality', select_quality_button)


def listen() -> None:
    """Set up event listeners for smart preview interactions"""
    
    # Get components
    preset_selector = get_ui_component('smart_preview_selector')
    generate_button = get_ui_component('smart_preview_generate')
    preview_results = get_ui_component('smart_preview_results')
    preview_status = get_ui_component('smart_preview_status')
    advanced_toggle = get_ui_component('smart_preview_advanced_toggle')
    advanced_settings = get_ui_component('smart_preview_advanced_settings')
    
    # Preview selection buttons
    select_fast_button = get_ui_component('smart_preview_select_fast')
    select_balanced_button = get_ui_component('smart_preview_select_balanced')
    select_quality_button = get_ui_component('smart_preview_select_quality')
    
    if not all([preset_selector, generate_button, preview_results, preview_status, 
                advanced_toggle, advanced_settings]):
        return
    
    # Handle preset selection changes
    def on_preset_change(selected_preset: str) -> str:
        """Handle preset selection change"""
        if PresetManager.apply_preset(selected_preset):
            preset_config = PresetManager.get_preset(selected_preset)
            if preset_config:
                return f"Applied {preset_config.display_name} preset - {preset_config.description}"
        return "Error applying preset"
    
    preset_selector.change(
        fn=on_preset_change,
        inputs=[preset_selector],
        outputs=[preview_status]
    )
    
    # Handle preview generation
    def generate_previews() -> Tuple[Any, str]:
        """Generate preview options with different presets"""
        try:
            # Check if source and target are available
            source_component = get_ui_component('source_image')
            target_component = get_ui_component('target_image')
            
            if not (source_component and target_component):
                return gradio.update(visible=False), "Please upload source and target images first"
            
            # TODO: Implement actual preview generation
            # For now, return placeholder status
            return gradio.update(visible=True), "Preview generation started... (Implementation in progress)"
            
        except Exception as e:
            return gradio.update(visible=False), f"Error generating previews: {str(e)}"
    
    generate_button.click(
        fn=generate_previews,
        outputs=[preview_results, preview_status]
    )
    
    # Handle preset selection from preview buttons
    def select_preset_from_preview(preset_name: str) -> str:
        """Apply selected preset and update status"""
        if PresetManager.apply_preset(preset_name):
            preset_config = PresetManager.get_preset(preset_name)
            if preset_config:
                return f"✅ Selected {preset_config.display_name} - Ready to process full image/video"
        return "Error selecting preset"
    
    # Wire up selection buttons
    select_fast_button.click(
        fn=lambda: select_preset_from_preview("fast"),
        outputs=[preview_status]
    )
    
    select_balanced_button.click(
        fn=lambda: select_preset_from_preview("balanced"),
        outputs=[preview_status]
    )
    
    select_quality_button.click(
        fn=lambda: select_preset_from_preview("quality"),
        outputs=[preview_status]
    )
    
    # Handle advanced settings toggle
    def toggle_advanced_settings(show_advanced: bool) -> Any:
        """Show/hide advanced settings"""
        return gradio.update(visible=show_advanced)
    
    advanced_toggle.change(
        fn=toggle_advanced_settings,
        inputs=[advanced_toggle],
        outputs=[advanced_settings]
    )