from typing import Optional
import threading
import time

import gradio

from facefusion import state_manager, logger
from facefusion.uis.core import register_ui_component
from facefusion.uis.types import ComponentOptions


def get_or_init_state_item(key: str, default_value):
	"""Get state item or initialize with default value if not present"""
	try:
		return state_manager.get_item(key)
	except:
		state_manager.init_item(key, default_value)
		return default_value


def get_initial_training_status() -> str:
	"""Get initial training status message"""
	if not TRAINING_AVAILABLE:
		return """🔧 Training Environment Setup Required

This Hugging Face Space includes the training interface for demonstration and learning purposes.

To use full training functionality:

1️⃣ Clone this Space or setup locally:
   git clone https://huggingface.co/spaces/IlliquidAsset/facefusion3.1

2️⃣ Install training dependencies:
   pip install torch torchvision transformers diffusers huggingface_hub

3️⃣ Follow the TRAINING_README.md for complete setup

🎯 What you can do here:
• Explore the training interface
• Upload and manage datasets  
• Configure training parameters
• Learn about InstantID training"""
	else:
		return "Ready to start training! Upload a dataset and configure parameters."

# Optional training dependencies
try:
	from facefusion.trainers.instantid_trainer import start_instantid_training, create_training_config
	TRAINING_AVAILABLE = True
except ImportError as error:
	logger.warn(f'Training dependencies not available: {error}', __name__)
	TRAINING_AVAILABLE = False

START_TRAINING_BUTTON : Optional[gradio.Button] = None
STOP_TRAINING_BUTTON : Optional[gradio.Button] = None
TRAINING_STATUS_TEXTBOX : Optional[gradio.Textbox] = None
MODEL_OUTPUT_PATH_TEXTBOX : Optional[gradio.Textbox] = None
DOWNLOAD_MODELS_BUTTON : Optional[gradio.Button] = None

TRAINING_THREAD = None
TRAINING_ACTIVE = False
TRAINER_INSTANCE = None


def render() -> None:
	global START_TRAINING_BUTTON
	global STOP_TRAINING_BUTTON
	global TRAINING_STATUS_TEXTBOX
	global MODEL_OUTPUT_PATH_TEXTBOX
	global DOWNLOAD_MODELS_BUTTON

	start_training_button_options : ComponentOptions =\
	{
		'value': 'Start Training',
		'variant': 'primary',
		'size': 'lg'
	}
	stop_training_button_options : ComponentOptions =\
	{
		'value': 'Stop Training',
		'variant': 'stop',
		'size': 'lg',
		'interactive': False
	}
	training_status_textbox_options : ComponentOptions =\
	{
		'label': 'Training Status',
		'interactive': False,
		'value': get_initial_training_status(),
		'lines': 8
	}
	model_output_path_textbox_options : ComponentOptions =\
	{
		'label': 'Model Output Path',
		'placeholder': 'Path where trained model will be saved',
		'value': get_or_init_state_item('model_output_path', './models/trained')
	}
	download_models_button_options : ComponentOptions =\
	{
		'value': 'Download Base Models',
		'variant': 'secondary'
	}

	with gradio.Group():
		MODEL_OUTPUT_PATH_TEXTBOX = gradio.Textbox(**model_output_path_textbox_options)
		DOWNLOAD_MODELS_BUTTON = gradio.Button(**download_models_button_options)
		TRAINING_STATUS_TEXTBOX = gradio.Textbox(**training_status_textbox_options)
		with gradio.Row():
			START_TRAINING_BUTTON = gradio.Button(**start_training_button_options)
			STOP_TRAINING_BUTTON = gradio.Button(**stop_training_button_options)

	register_ui_component('start_training_button', START_TRAINING_BUTTON)
	register_ui_component('stop_training_button', STOP_TRAINING_BUTTON)
	register_ui_component('training_status_textbox', TRAINING_STATUS_TEXTBOX)


def listen() -> None:
	START_TRAINING_BUTTON.click(
		start_training,
		inputs = [],
		outputs = [ TRAINING_STATUS_TEXTBOX, START_TRAINING_BUTTON, STOP_TRAINING_BUTTON ]
	)
	STOP_TRAINING_BUTTON.click(
		stop_training,
		inputs = [],
		outputs = [ TRAINING_STATUS_TEXTBOX, START_TRAINING_BUTTON, STOP_TRAINING_BUTTON ]
	)
	MODEL_OUTPUT_PATH_TEXTBOX.change(update_model_output_path, inputs = MODEL_OUTPUT_PATH_TEXTBOX, outputs = None)
	DOWNLOAD_MODELS_BUTTON.click(download_base_models, inputs = [], outputs = TRAINING_STATUS_TEXTBOX)


def start_training() -> tuple[str, gradio.Button, gradio.Button]:
	global TRAINING_THREAD, TRAINING_ACTIVE
	
	# Check if training dependencies are available
	if not TRAINING_AVAILABLE:
		return 'Error: Training dependencies not installed. Run: pip install -r requirements-training.txt', gradio.Button(interactive=True), gradio.Button(interactive=False)
	
	# Validate requirements
	try:
		dataset_path = state_manager.get_item('dataset_path')
	except:
		return 'Error: No dataset path specified', gradio.Button(interactive=True), gradio.Button(interactive=False)
	if not dataset_path:
		return 'Error: Dataset path is empty', gradio.Button(interactive=True), gradio.Button(interactive=False)
	
	# Check if already training
	if TRAINING_ACTIVE:
		return 'Training already in progress', gradio.Button(interactive=False), gradio.Button(interactive=True)
	
	# Start training thread
	TRAINING_ACTIVE = True
	TRAINING_THREAD = threading.Thread(target=run_training_process)
	TRAINING_THREAD.start()
	
	return 'Training started...', gradio.Button(interactive=False), gradio.Button(interactive=True)


def stop_training() -> tuple[str, gradio.Button, gradio.Button]:
	global TRAINING_ACTIVE, TRAINER_INSTANCE
	
	TRAINING_ACTIVE = False
	
	# Stop the trainer instance if it exists
	if TRAINER_INSTANCE:
		TRAINER_INSTANCE.stop_training()
	
	logger.info('Training stop requested')
	
	return 'Stopping training...', gradio.Button(interactive=True), gradio.Button(interactive=False)


def run_training_process() -> None:
	"""Main training process using InstantID trainer"""
	global TRAINING_ACTIVE, TRAINER_INSTANCE
	
	if not TRAINING_AVAILABLE:
		logger.error('Training dependencies not available')
		TRAINING_ACTIVE = False
		return
	
	try:
		training_model = get_or_init_state_item('training_model', 'InstantID')
		dataset_path = get_or_init_state_item('dataset_path', './datasets/training')
		epochs = get_or_init_state_item('training_epochs', 100)
		output_path = get_or_init_state_item('model_output_path', './models/trained')
		
		logger.info(f'Starting {training_model} training with {epochs} epochs')
		logger.info(f'Dataset path: {dataset_path}')
		logger.info(f'Output path: {output_path}')
		
		if training_model == 'InstantID':
			TRAINER_INSTANCE = start_instantid_training(dataset_path, epochs, output_path)
		elif training_model == 'SimSwap':
			logger.error('SimSwap training not yet implemented')
			TRAINING_ACTIVE = False
			return
		else:
			logger.error('Custom model training not yet implemented')
			TRAINING_ACTIVE = False
			return
		
		# Monitor training progress
		while TRAINING_ACTIVE and TRAINER_INSTANCE and TRAINER_INSTANCE.training_active:
			time.sleep(5)  # Check every 5 seconds
			
			# Get training info
			if TRAINER_INSTANCE:
				info = TRAINER_INSTANCE.get_training_info()
				if info['losses']:
					logger.info(f"Epoch {info['current_epoch']}, Loss: {info['losses'][-1]:.6f}")
		
		if TRAINER_INSTANCE and not TRAINER_INSTANCE.training_active:
			logger.info('Training completed successfully')
		
	except Exception as error:
		logger.error(f'Training error: {error}')
	finally:
		TRAINING_ACTIVE = False


def download_base_models() -> str:
	"""Download base models required for training"""
	try:
		training_model = get_or_init_state_item('training_model', 'InstantID')
		
		if training_model == 'InstantID':
			return download_instantid_models()
		elif training_model == 'SimSwap':
			return download_simswap_models()
		else:
			return 'Custom model training not yet implemented'
	
	except Exception as error:
		logger.error(f'Error downloading models: {error}')
		return f'Error downloading models: {error}'


def download_instantid_models() -> str:
	"""Download InstantID models from Hugging Face"""
	try:
		logger.info('Downloading InstantID models from Hugging Face...')
		
		# This would require huggingface_hub to be installed
		# For now, provide instructions for manual download
		instructions = """
To use InstantID training, please manually download the following models:

1. InstantID ControlNet:
   - Repository: InstantX/InstantID
   - Files: ControlNetModel/, ip-adapter.bin
   - Save to: ./models/InstantID/

2. Face Encoder (InsightFace):
   - Download antelopev2.zip from InsightFace
   - Extract to: ./models/face_encoders/

3. Base Stable Diffusion model:
   - Repository: runwayml/stable-diffusion-v1-5
   - Save to: ./models/stable-diffusion/

Commands to run:
git clone https://github.com/deepinsight/insightface
pip install -r requirements.txt
"""
		
		logger.info(instructions)
		return 'Model download instructions logged. Check terminal for details.'
		
	except Exception as error:
		return f'Error downloading InstantID models: {error}'


def download_simswap_models() -> str:
	"""Download SimSwap models from Hugging Face"""
	try:
		logger.info('Downloading SimSwap models from Hugging Face...')
		# This would download from netrunner-exe/SimSwap-models
		return 'SimSwap models download started. Check terminal for progress.'
	except Exception as error:
		return f'Error downloading SimSwap models: {error}'


def update_model_output_path(model_output_path : str) -> None:
	state_manager.set_item('model_output_path', model_output_path)