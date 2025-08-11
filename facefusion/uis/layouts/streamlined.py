import gradio

from facefusion import state_manager
from facefusion.uis.components import about, common_options, execution, face_detector, face_landmarker, face_masker, face_selector, instant_runner, job_manager, job_runner, memory, output, output_options, processors, smart_preview, source, target, terminal, ui_workflow


def pre_check() -> bool:
    return True


def render() -> gradio.Blocks:
    """Render streamlined 4-step workflow layout"""
    with gradio.Blocks() as layout:
        # Header
        about.render()
        
        # Main workflow tabs
        with gradio.Tabs() as main_tabs:
            # Step 1: Upload
            with gradio.Tab("📁 Upload", id="upload_tab"):
                with gradio.Row():
                    with gradio.Column(scale=1):
                        gradio.Markdown(
                            """
                            ## Step 1: Upload Your Media
                            
                            **Source**: The face you want to use (person's photo)
                            **Target**: The video or image where you want to place the face
                            
                            💡 **Tips**: 
                            - Use clear, well-lit photos for best results
                            - Front-facing source images work best
                            - Supported formats: JPG, PNG, MP4, MOV
                            """
                        )
                    with gradio.Column(scale=2):
                        with gradio.Row():
                            with gradio.Column():
                                source.render()
                            with gradio.Column():
                                target.render()
                        
                        next_to_preview_button = gradio.Button(
                            value="➡️ Next: Generate Previews",
                            variant="primary",
                            size="lg"
                        )
            
            # Step 2: Preview Selection  
            with gradio.Tab("🔍 Preview", id="preview_tab"):
                with gradio.Row():
                    with gradio.Column(scale=1):
                        gradio.Markdown(
                            """
                            ## Step 2: Choose Your Quality
                            
                            See 3 preview options and pick the one you like best.
                            Each option balances speed vs quality differently.
                            
                            💡 **Tips**:
                            - Fast: Great for testing and quick results
                            - Balanced: Best overall choice for most users  
                            - Quality: Slower but highest quality output
                            """
                        )
                    with gradio.Column(scale=3):
                        smart_preview.render()
                        
                        next_to_export_button = gradio.Button(
                            value="➡️ Next: Process Full Media",
                            variant="primary",
                            size="lg"
                        )
            
            # Step 3: Export/Processing
            with gradio.Tab("⚡ Process", id="process_tab"):
                with gradio.Row():
                    with gradio.Column(scale=1):
                        gradio.Markdown(
                            """
                            ## Step 3: Process & Download
                            
                            Generate your final result using the settings you selected.
                            Processing time depends on your chosen quality preset.
                            
                            💡 **Tips**:
                            - Processing runs on GPU when available
                            - Larger videos take longer to process
                            - You can monitor progress below
                            """
                        )
                    with gradio.Column(scale=2):
                        # Output settings (simplified)
                        with gradio.Accordion("📤 Output", open=True):
                            output.render()
                        
                        # Execution controls
                        with gradio.Accordion("⚡ Processing", open=True):
                            ui_workflow.render()
                            instant_runner.render()
                            job_runner.render()
                        
                        # Terminal for progress
                        with gradio.Accordion("📊 Progress", open=False):
                            terminal.render()
            
            # Step 4: Advanced/Training (for power users)
            with gradio.Tab("🎓 Advanced", id="advanced_tab"):
                with gradio.Row():
                    with gradio.Column(scale=1):
                        gradio.Markdown(
                            """
                            ## Advanced Settings & Training
                            
                            **Fine-tune settings** or **train custom models** for specialized use cases.
                            
                            ⚠️ **Note**: These are advanced features.
                            Most users should stick to the Preview tab presets.
                            """
                        )
                    
                    with gradio.Column(scale=3):
                        # Advanced processor settings (collapsed by default)
                        with gradio.Accordion("🎛️ Processors", open=False):
                            processors.render()
                        
                        with gradio.Accordion("🔧 Technical Settings", open=False):
                            # Face detection settings
                            with gradio.Row():
                                with gradio.Column():
                                    face_detector.render()
                                with gradio.Column():
                                    face_landmarker.render()
                            
                            # Face processing settings
                            with gradio.Row():
                                with gradio.Column():
                                    face_selector.render()
                                with gradio.Column():
                                    face_masker.render()
                            
                            # System settings
                            execution.render()
                            memory.render()
                            common_options.render()
                            output_options.render()
                        
                        # Job management for advanced workflows
                        with gradio.Accordion("📋 Job Management", open=False):
                            job_manager.render()
                        
                        # Training placeholder (to be implemented)
                        with gradio.Accordion("🎓 Model Training", open=False):
                            gradio.Markdown(
                                """
                                ### Custom Model Training
                                
                                **Coming Soon**: Train custom face models with your own datasets.
                                
                                This feature will allow you to:
                                - Upload training image sets
                                - Configure training parameters
                                - Monitor training progress
                                - Manage trained models
                                
                                *Currently in development as part of Phase 4.*
                                """
                            )
        
        # Register tab navigation components
        from facefusion.uis.core import register_ui_component
        register_ui_component('main_tabs', main_tabs)
        register_ui_component('next_to_preview_button', next_to_preview_button)
        register_ui_component('next_to_export_button', next_to_export_button)
    
    return layout


def listen() -> None:
    """Set up event listeners for streamlined layout"""
    
    # Import components that need listeners
    processors.listen()
    execution.listen()
    memory.listen()
    common_options.listen()
    output_options.listen()
    source.listen()
    target.listen()
    output.listen()
    instant_runner.listen()
    job_runner.listen()
    job_manager.listen()
    terminal.listen()
    face_selector.listen()
    face_masker.listen()
    face_detector.listen()
    face_landmarker.listen()
    smart_preview.listen()
    
    # Get navigation components
    from facefusion.uis.core import get_ui_component
    main_tabs = get_ui_component('main_tabs')
    next_to_preview_button = get_ui_component('next_to_preview_button')
    next_to_export_button = get_ui_component('next_to_export_button')
    
    if main_tabs and next_to_preview_button:
        # Navigate to preview tab when "Next: Generate Previews" is clicked
        next_to_preview_button.click(
            fn=lambda: gradio.update(selected="preview_tab"),
            outputs=[main_tabs]
        )
    
    if main_tabs and next_to_export_button:
        # Navigate to process tab when "Next: Process Full Media" is clicked  
        next_to_export_button.click(
            fn=lambda: gradio.update(selected="process_tab"),
            outputs=[main_tabs]
        )


def run(ui: gradio.Blocks) -> None:
    """Launch the streamlined UI"""
    ui.launch(
        favicon_path='facefusion.ico', 
        inbrowser=state_manager.get_item('open_browser'),
        share=False,
        server_name="0.0.0.0",
        server_port=7860
    )