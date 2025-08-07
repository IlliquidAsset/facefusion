from typing import Optional, List
import os

import gradio

from facefusion import state_manager, wording, logger
from facefusion.uis.core import register_ui_component
from facefusion.uis.types import ComponentOptions
from facefusion.filesystem import is_directory, create_directory, resolve_relative_path


def get_or_init_state_item(key: str, default_value):
	"""Get state item or initialize with default value if not present"""
	try:
		return state_manager.get_item(key)
	except:
		state_manager.init_item(key, default_value)
		return default_value

DATASET_FOLDER_TEXTBOX : Optional[gradio.Textbox] = None
DATASET_UPLOAD_FILE : Optional[gradio.File] = None
DATASET_GALLERY : Optional[gradio.Gallery] = None
DATASET_STATUS_TEXTBOX : Optional[gradio.Textbox] = None
DATASET_CREATE_BUTTON : Optional[gradio.Button] = None
DATASET_VALIDATE_BUTTON : Optional[gradio.Button] = None


def render() -> None:
	global DATASET_FOLDER_TEXTBOX
	global DATASET_UPLOAD_FILE
	global DATASET_GALLERY
	global DATASET_STATUS_TEXTBOX
	global DATASET_CREATE_BUTTON
	global DATASET_VALIDATE_BUTTON

	dataset_folder_textbox_options : ComponentOptions =\
	{
		'label': 'Dataset Folder Path',
		'placeholder': 'Enter path to dataset folder or create new one',
		'value': get_or_init_state_item('dataset_path', './datasets/training')
	}
	dataset_upload_file_options : ComponentOptions =\
	{
		'label': 'Upload Training Images',
		'file_count': 'multiple',
		'file_types': ['image']
	}
	dataset_gallery_options : ComponentOptions =\
	{
		'label': 'Dataset Preview',
		'show_label': True,
		'columns': 4,
		'rows': 2,
		'height': 400
	}
	dataset_status_textbox_options : ComponentOptions =\
	{
		'label': 'Dataset Status',
		'interactive': False,
		'value': 'Ready to create or load dataset'
	}
	dataset_create_button_options : ComponentOptions =\
	{
		'value': 'Create Dataset Folder',
		'variant': 'primary'
	}
	dataset_validate_button_options : ComponentOptions =\
	{
		'value': 'Validate Dataset',
		'variant': 'secondary'
	}

	with gradio.Group():
		DATASET_FOLDER_TEXTBOX = gradio.Textbox(**dataset_folder_textbox_options)
		with gradio.Row():
			DATASET_CREATE_BUTTON = gradio.Button(**dataset_create_button_options)
			DATASET_VALIDATE_BUTTON = gradio.Button(**dataset_validate_button_options)
		DATASET_UPLOAD_FILE = gradio.File(**dataset_upload_file_options)
		DATASET_STATUS_TEXTBOX = gradio.Textbox(**dataset_status_textbox_options)
		DATASET_GALLERY = gradio.Gallery(**dataset_gallery_options)

	register_ui_component('dataset_folder_textbox', DATASET_FOLDER_TEXTBOX)
	register_ui_component('dataset_upload_file', DATASET_UPLOAD_FILE)
	register_ui_component('dataset_gallery', DATASET_GALLERY)
	register_ui_component('dataset_status_textbox', DATASET_STATUS_TEXTBOX)


def listen() -> None:
	DATASET_FOLDER_TEXTBOX.change(update_dataset_path, inputs = DATASET_FOLDER_TEXTBOX, outputs = [ DATASET_STATUS_TEXTBOX, DATASET_GALLERY ])
	DATASET_CREATE_BUTTON.click(create_dataset_folder, inputs = DATASET_FOLDER_TEXTBOX, outputs = [ DATASET_STATUS_TEXTBOX, DATASET_GALLERY ])
	DATASET_VALIDATE_BUTTON.click(validate_dataset, inputs = DATASET_FOLDER_TEXTBOX, outputs = [ DATASET_STATUS_TEXTBOX, DATASET_GALLERY ])
	DATASET_UPLOAD_FILE.upload(upload_images, inputs = [ DATASET_UPLOAD_FILE, DATASET_FOLDER_TEXTBOX ], outputs = [ DATASET_STATUS_TEXTBOX, DATASET_GALLERY ])


def update_dataset_path(dataset_path : str) -> tuple[str, List]:
	state_manager.set_item('dataset_path', dataset_path)
	
	if not dataset_path:
		return 'Please enter a dataset path', []
	
	if is_directory(dataset_path):
		image_files = get_image_files(dataset_path)
		return f'Found {len(image_files)} images in dataset', image_files[:16]  # Show first 16 images
	else:
		return 'Dataset folder does not exist', []


def create_dataset_folder(dataset_path : str) -> tuple[str, List]:
	if not dataset_path:
		return 'Please enter a dataset path', []
	
	try:
		if not is_directory(dataset_path):
			create_directory(dataset_path)
			logger.info(f'Created dataset directory: {dataset_path}')
			state_manager.set_item('dataset_path', dataset_path)
			return f'Successfully created dataset folder: {dataset_path}', []
		else:
			return f'Dataset folder already exists: {dataset_path}', get_image_files(dataset_path)[:16]
	except Exception as error:
		logger.error(f'Failed to create dataset folder: {error}')
		return f'Error creating dataset folder: {error}', []


def validate_dataset(dataset_path : str) -> tuple[str, List]:
	if not dataset_path or not is_directory(dataset_path):
		return 'Dataset folder does not exist', []
	
	try:
		image_files = get_image_files(dataset_path)
		
		if len(image_files) < 10:
			return f'Warning: Only {len(image_files)} images found. Recommend at least 50-100 images for good results', image_files
		elif len(image_files) < 50:
			return f'Found {len(image_files)} images. This may work but more images (100+) recommended', image_files[:16]
		else:
			return f'Great! Found {len(image_files)} images. Dataset looks good for training', image_files[:16]
	except Exception as error:
		logger.error(f'Error validating dataset: {error}')
		return f'Error validating dataset: {error}', []


def upload_images(files, dataset_path : str) -> tuple[str, List]:
	if not dataset_path:
		return 'Please set dataset folder path first', []
	
	if not is_directory(dataset_path):
		try:
			create_directory(dataset_path)
		except Exception as error:
			return f'Error creating dataset folder: {error}', []
	
	if not files:
		return 'No files uploaded', []
	
	try:
		uploaded_count = 0
		for file in files:
			if file and hasattr(file, 'name'):
				# Copy file to dataset folder
				filename = os.path.basename(file.name)
				destination = os.path.join(dataset_path, filename)
				
				# Simple file copy
				with open(file.name, 'rb') as src, open(destination, 'wb') as dst:
					dst.write(src.read())
				uploaded_count += 1
		
		image_files = get_image_files(dataset_path)
		return f'Successfully uploaded {uploaded_count} images. Total: {len(image_files)} images', image_files[:16]
	
	except Exception as error:
		logger.error(f'Error uploading images: {error}')
		return f'Error uploading images: {error}', []


def get_image_files(directory_path : str) -> List[str]:
	"""Get list of image files in directory"""
	if not is_directory(directory_path):
		return []
	
	image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff'}
	image_files = []
	
	try:
		for filename in os.listdir(directory_path):
			if any(filename.lower().endswith(ext) for ext in image_extensions):
				image_files.append(os.path.join(directory_path, filename))
		return sorted(image_files)
	except Exception as error:
		logger.error(f'Error reading directory {directory_path}: {error}')
		return []