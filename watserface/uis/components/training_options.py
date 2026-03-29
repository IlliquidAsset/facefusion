from typing import Optional

import gradio

from watserface import state_manager, wording
from watserface.uis.core import register_ui_component

TRAINING_MODEL_DROPDOWN : Optional[gradio.Dropdown] = None
TRAINING_BASE_MODEL_DROPDOWN : Optional[gradio.Dropdown] = None
TRAINING_EPOCHS_SLIDER : Optional[gradio.Slider] = None
TRAINING_BATCH_SIZE_SLIDER : Optional[gradio.Slider] = None
TRAINING_LEARNING_RATE_NUMBER : Optional[gradio.Number] = None
TRAINING_SAVE_INTERVAL_SLIDER : Optional[gradio.Slider] = None
TRAINING_OUTPUT_MODEL_TEXTBOX : Optional[gradio.Textbox] = None


def render() -> None:
	global TRAINING_MODEL_DROPDOWN
	global TRAINING_BASE_MODEL_DROPDOWN
	global TRAINING_EPOCHS_SLIDER
	global TRAINING_BATCH_SIZE_SLIDER
	global TRAINING_LEARNING_RATE_NUMBER
	global TRAINING_SAVE_INTERVAL_SLIDER
	global TRAINING_OUTPUT_MODEL_TEXTBOX

	with gradio.Group():
		gradio.Markdown("### 🛠️ Training Configuration")
		with gradio.Row():
			TRAINING_MODEL_DROPDOWN = gradio.Dropdown(
				label = wording.get('uis.training_model_dropdown'),
				info = wording.get('help.training_model'),
				choices = [ 'InstantID', 'SimSwap', 'XSeg (Occlusion)', 'Custom' ],
				value = 'InstantID'
			)
			TRAINING_BASE_MODEL_DROPDOWN = gradio.Dropdown(
				label = wording.get('uis.training_base_model_dropdown'),
				info = wording.get('help.training_base_model'),
				choices = [ 'none' ], # To be populated with available models
				value = 'none'
			)
		TRAINING_OUTPUT_MODEL_TEXTBOX = gradio.Textbox(
			label = wording.get('uis.training_output_model_textbox'),
			info = wording.get('help.training_output_model'),
			value = 'my_custom_model',
			placeholder = 'Enter name for the new model'
		)
		with gradio.Row():
			TRAINING_EPOCHS_SLIDER = gradio.Slider(
				label = wording.get('uis.training_epochs_slider'),
				info = wording.get('help.training_epochs'),
				minimum = 1,
				maximum = 1000,
				step = 1,
				value = 100
			)
			TRAINING_BATCH_SIZE_SLIDER = gradio.Slider(
				label = wording.get('uis.training_batch_size_slider'),
				info = wording.get('help.training_batch_size'),
				minimum = 1,
				maximum = 16,
				step = 1,
				value = 2
			)
		with gradio.Row():
			TRAINING_LEARNING_RATE_NUMBER = gradio.Number(
				label = wording.get('uis.training_learning_rate_number'),
				info = wording.get('help.training_learning_rate'),
				value = 0.001,
				step = 0.0001
			)
			TRAINING_SAVE_INTERVAL_SLIDER = gradio.Slider(
				label = wording.get('uis.training_save_interval_slider'),
				info = wording.get('help.training_save_interval'),
				minimum = 1,
				maximum = 100,
				step = 1,
				value = 10
			)

	register_ui_component('training_model_dropdown', TRAINING_MODEL_DROPDOWN)
	register_ui_component('training_base_model_dropdown', TRAINING_BASE_MODEL_DROPDOWN)
	register_ui_component('training_output_model_textbox', TRAINING_OUTPUT_MODEL_TEXTBOX)
	register_ui_component('training_epochs_slider', TRAINING_EPOCHS_SLIDER)
	register_ui_component('training_batch_size_slider', TRAINING_BATCH_SIZE_SLIDER)
	register_ui_component('training_learning_rate_number', TRAINING_LEARNING_RATE_NUMBER)
	register_ui_component('training_save_interval_slider', TRAINING_SAVE_INTERVAL_SLIDER)


def listen() -> None:
	pass
