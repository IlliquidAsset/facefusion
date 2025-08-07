from typing import Optional

import gradio

from facefusion import state_manager, wording
from facefusion.uis.core import register_ui_component
from facefusion.uis.types import ComponentOptions

TRAINING_MODEL_DROPDOWN : Optional[gradio.Dropdown] = None
TRAINING_EPOCHS_SLIDER : Optional[gradio.Slider] = None
TRAINING_BATCH_SIZE_SLIDER : Optional[gradio.Slider] = None
TRAINING_LEARNING_RATE_SLIDER : Optional[gradio.Slider] = None
TRAINING_SAVE_INTERVAL_SLIDER : Optional[gradio.Slider] = None


def render() -> None:
	global TRAINING_MODEL_DROPDOWN
	global TRAINING_EPOCHS_SLIDER
	global TRAINING_BATCH_SIZE_SLIDER
	global TRAINING_LEARNING_RATE_SLIDER
	global TRAINING_SAVE_INTERVAL_SLIDER

	# Initialize training state items if not present
	try:
		training_model = state_manager.get_item('training_model')
	except:
		training_model = 'InstantID'
		state_manager.init_item('training_model', training_model)
	
	try:
		training_epochs = state_manager.get_item('training_epochs')
	except:
		training_epochs = 100
		state_manager.init_item('training_epochs', training_epochs)
	
	try:
		training_batch_size = state_manager.get_item('training_batch_size')
	except:
		training_batch_size = 4
		state_manager.init_item('training_batch_size', training_batch_size)
	
	try:
		training_learning_rate = state_manager.get_item('training_learning_rate')
	except:
		training_learning_rate = 0.001
		state_manager.init_item('training_learning_rate', training_learning_rate)
		
	try:
		training_save_interval = state_manager.get_item('training_save_interval')
	except:
		training_save_interval = 20
		state_manager.init_item('training_save_interval', training_save_interval)

	training_model_dropdown_options : ComponentOptions =\
	{
		'label': 'Training Model',
		'choices': [ 'InstantID', 'SimSwap', 'Custom' ],
		'value': training_model
	}
	training_epochs_slider_options : ComponentOptions =\
	{
		'label': 'Training Epochs',
		'minimum': 10,
		'maximum': 1000,
		'step': 10,
		'value': training_epochs
	}
	training_batch_size_slider_options : ComponentOptions =\
	{
		'label': 'Batch Size',
		'minimum': 1,
		'maximum': 32,
		'step': 1,
		'value': training_batch_size
	}
	training_learning_rate_slider_options : ComponentOptions =\
	{
		'label': 'Learning Rate',
		'minimum': 0.0001,
		'maximum': 0.01,
		'step': 0.0001,
		'value': training_learning_rate
	}
	training_save_interval_slider_options : ComponentOptions =\
	{
		'label': 'Save Interval (epochs)',
		'minimum': 5,
		'maximum': 100,
		'step': 5,
		'value': training_save_interval
	}

	with gradio.Group():
		TRAINING_MODEL_DROPDOWN = gradio.Dropdown(**training_model_dropdown_options)
		TRAINING_EPOCHS_SLIDER = gradio.Slider(**training_epochs_slider_options)
		TRAINING_BATCH_SIZE_SLIDER = gradio.Slider(**training_batch_size_slider_options)
		TRAINING_LEARNING_RATE_SLIDER = gradio.Slider(**training_learning_rate_slider_options)
		TRAINING_SAVE_INTERVAL_SLIDER = gradio.Slider(**training_save_interval_slider_options)

	register_ui_component('training_model_dropdown', TRAINING_MODEL_DROPDOWN)
	register_ui_component('training_epochs_slider', TRAINING_EPOCHS_SLIDER)
	register_ui_component('training_batch_size_slider', TRAINING_BATCH_SIZE_SLIDER)
	register_ui_component('training_learning_rate_slider', TRAINING_LEARNING_RATE_SLIDER)
	register_ui_component('training_save_interval_slider', TRAINING_SAVE_INTERVAL_SLIDER)


def listen() -> None:
	TRAINING_MODEL_DROPDOWN.change(update_training_model, inputs = TRAINING_MODEL_DROPDOWN, outputs = None)
	TRAINING_EPOCHS_SLIDER.release(update_training_epochs, inputs = TRAINING_EPOCHS_SLIDER, outputs = None)
	TRAINING_BATCH_SIZE_SLIDER.release(update_training_batch_size, inputs = TRAINING_BATCH_SIZE_SLIDER, outputs = None)
	TRAINING_LEARNING_RATE_SLIDER.release(update_training_learning_rate, inputs = TRAINING_LEARNING_RATE_SLIDER, outputs = None)
	TRAINING_SAVE_INTERVAL_SLIDER.release(update_training_save_interval, inputs = TRAINING_SAVE_INTERVAL_SLIDER, outputs = None)


def update_training_model(training_model : str) -> None:
	state_manager.set_item('training_model', training_model)


def update_training_epochs(training_epochs : int) -> None:
	state_manager.set_item('training_epochs', training_epochs)


def update_training_batch_size(training_batch_size : int) -> None:
	state_manager.set_item('training_batch_size', training_batch_size)


def update_training_learning_rate(training_learning_rate : float) -> None:
	state_manager.set_item('training_learning_rate', training_learning_rate)


def update_training_save_interval(training_save_interval : int) -> None:
	state_manager.set_item('training_save_interval', training_save_interval)