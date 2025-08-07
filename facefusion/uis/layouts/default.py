import gradio

from facefusion import state_manager
from facefusion.uis.components import about, age_modifier_options, common_options, deep_swapper_options, download, execution, execution_queue_count, execution_thread_count, expression_restorer_options, face_debugger_options, face_detector, face_editor_options, face_enhancer_options, face_landmarker, face_masker, face_selector, face_swapper_options, frame_colorizer_options, frame_enhancer_options, instant_runner, job_manager, job_runner, lip_syncer_options, memory, output, output_options, preview, processors, source, target, temp_frame, terminal, trim_frame, ui_workflow


def pre_check() -> bool:
	return True


def render() -> gradio.Blocks:
	with gradio.Blocks() as layout:
		# Header
		about.render()
		
		with gradio.Row():
			with gradio.Column(scale = 4):
				with gradio.Accordion("🎛️ Processors", open=True):
					processors.render()
				
				with gradio.Accordion("👤 Age Modifier", open=False):
					age_modifier_options.render()
					
				with gradio.Accordion("🔄 Deep Swapper", open=False):
					deep_swapper_options.render()
					
				with gradio.Accordion("😊 Expression Restorer", open=False):
					expression_restorer_options.render()
					
				with gradio.Accordion("🐛 Face Debugger", open=False):
					face_debugger_options.render()
					
				with gradio.Accordion("✏️ Face Editor", open=False):
					face_editor_options.render()
					
				with gradio.Accordion("✨ Face Enhancer", open=False):
					face_enhancer_options.render()
					
				with gradio.Accordion("🔀 Face Swapper", open=True):
					face_swapper_options.render()
					
				with gradio.Accordion("🎨 Frame Colorizer", open=False):
					frame_colorizer_options.render()
					
				with gradio.Accordion("📈 Frame Enhancer", open=False):
					frame_enhancer_options.render()
					
				with gradio.Accordion("👄 Lip Syncer", open=False):
					lip_syncer_options.render()
					
				with gradio.Accordion("⚡ Execution", open=False):
					execution.render()
					execution_thread_count.render()
					execution_queue_count.render()
					
				with gradio.Accordion("📥 Download", open=False):
					download.render()
					
				with gradio.Accordion("💾 Memory", open=False):
					memory.render()
					
				with gradio.Accordion("🗂️ Temp Frame", open=False):
					temp_frame.render()
					
				with gradio.Accordion("📤 Output Options", open=False):
					output_options.render()
					
			with gradio.Column(scale = 4):
				with gradio.Accordion("📁 Source", open=True):
					source.render()
					
				with gradio.Accordion("🎯 Target", open=True):
					target.render()
					
				with gradio.Accordion("💾 Output", open=True):
					output.render()
					
				with gradio.Accordion("💻 Terminal", open=False):
					terminal.render()
					
				with gradio.Accordion("🔄 Workflow", open=True):
					ui_workflow.render()
					instant_runner.render()
					job_runner.render()
					job_manager.render()
					
			with gradio.Column(scale = 7):
				with gradio.Accordion("👁️ Preview", open=True):
					preview.render()
					
				with gradio.Accordion("✂️ Trim Frame", open=False):
					trim_frame.render()
					
				with gradio.Accordion("👤 Face Selector", open=False):
					face_selector.render()
					
				with gradio.Accordion("🎭 Face Masker", open=False):
					face_masker.render()
					
				with gradio.Accordion("🔍 Face Detector", open=False):
					face_detector.render()
					
				with gradio.Accordion("📍 Face Landmarker", open=False):
					face_landmarker.render()
					
				with gradio.Accordion("⚙️ Common Options", open=False):
					common_options.render()
	return layout


def listen() -> None:
	processors.listen()
	age_modifier_options.listen()
	deep_swapper_options.listen()
	expression_restorer_options.listen()
	face_debugger_options.listen()
	face_editor_options.listen()
	face_enhancer_options.listen()
	face_swapper_options.listen()
	frame_colorizer_options.listen()
	frame_enhancer_options.listen()
	lip_syncer_options.listen()
	execution.listen()
	execution_thread_count.listen()
	execution_queue_count.listen()
	download.listen()
	memory.listen()
	temp_frame.listen()
	output_options.listen()
	source.listen()
	target.listen()
	output.listen()
	instant_runner.listen()
	job_runner.listen()
	job_manager.listen()
	terminal.listen()
	preview.listen()
	trim_frame.listen()
	face_selector.listen()
	face_masker.listen()
	face_detector.listen()
	face_landmarker.listen()
	common_options.listen()


def run(ui : gradio.Blocks) -> None:
	ui.launch(favicon_path = 'facefusion.ico', inbrowser = state_manager.get_item('open_browser'))
