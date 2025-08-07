import gradio

from facefusion import state_manager
from facefusion.uis.components import about, common_options, memory, terminal
from facefusion.uis.components import dataset_manager, model_trainer, training_options, training_progress

def pre_check() -> bool:
	return True

def render() -> gradio.Blocks:
	with gradio.Blocks() as layout:
		with gradio.Row():
			with gradio.Column(scale = 4):
				with gradio.Blocks():
					about.render()
				with gradio.Blocks():
					training_options.render()
				with gradio.Blocks():
					memory.render()
				with gradio.Blocks():
					common_options.render()
			with gradio.Column(scale = 4):
				with gradio.Blocks():
					dataset_manager.render()
				with gradio.Blocks():
					model_trainer.render()
				with gradio.Blocks():
					terminal.render()
			with gradio.Column(scale = 7):
				with gradio.Blocks():
					training_progress.render()
	return layout

def listen() -> None:
	training_options.listen()
	dataset_manager.listen()
	model_trainer.listen()
	training_progress.listen()
	memory.listen()
	common_options.listen()

def run(ui : gradio.Blocks) -> None:
	ui.launch(favicon_path = 'facefusion.ico', inbrowser = state_manager.get_item('open_browser'))