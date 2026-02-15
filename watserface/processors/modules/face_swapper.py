from argparse import ArgumentParser
from functools import lru_cache
from typing import List, Tuple

import cv2
import numpy

import watserface.choices
import watserface.jobs.job_store
import watserface.processors.core as processors
from watserface import config, content_analyser, face_classifier, face_detector, face_landmarker, face_masker, face_recognizer, identity_profile, inference_manager, logger, process_manager, state_manager, video_manager, wording
from watserface.uis.components.progress_tracker import update_processing_step
from watserface.common_helper import get_first
from watserface.download import conditional_download_hashes, conditional_download_sources, resolve_download_url
from watserface.execution import has_execution_provider
from watserface.face_analyser import get_average_face, get_many_faces, get_one_face
from watserface.face_helper import paste_back, poisson_paste_back, predict_next_faces, thin_plate_spline_warp, warp_face_by_face_landmark_5
from watserface.face_masker import create_area_mask, create_box_mask, create_occlusion_mask, create_region_mask
from watserface.face_selector import find_similar_faces, sort_and_filter_faces, sort_faces_by_order
from watserface.face_store import clear_previous_faces, get_face_history, get_previous_faces, get_reference_faces, set_previous_faces
from watserface.filesystem import filter_image_paths, get_file_name, has_image, in_directory, is_image, is_video, resolve_file_paths, resolve_relative_path, same_file_extension
from watserface.model_helper import get_static_model_initializer
from watserface.processors import choices as processors_choices
from watserface.processors.pixel_boost import explode_pixel_boost, implode_pixel_boost
from watserface.processors.types import FaceSwapperInputs
from watserface.program_helper import find_argument_group
from watserface.thread_helper import conditional_thread_semaphore
from watserface.types import ApplyStateItem, Args, DownloadScope, Embedding, Face, InferencePool, ModelOptions, ModelSet, ProcessMode, QueuePayload, UpdateProgress, VisionFrame
from watserface.vision import read_image, read_static_image, read_static_images, unpack_resolution, write_image


@lru_cache(maxsize = None)
def create_static_model_set(download_scope : DownloadScope) -> ModelSet:
	return\
	{
		'blendswap_256':
		{
			'hashes':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'blendswap_256.hash'),
					'path': resolve_relative_path('../.assets/models/blendswap_256.hash')
				}
			},
			'sources':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'blendswap_256.onnx'),
					'path': resolve_relative_path('../.assets/models/blendswap_256.onnx')
				}
			},
			'type': 'blendswap',
			'template': 'ffhq_512',
			'size': (256, 256),
			'mean': numpy.array([0.0, 0.0, 0.0], dtype=numpy.float32),
			'standard_deviation': numpy.array([1.0, 1.0, 1.0], dtype=numpy.float32)
		},
		'ghost_1_256':
		{
			'hashes':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'ghost_1_256.hash'),
					'path': resolve_relative_path('../.assets/models/ghost_1_256.hash')
				},
				'embedding_converter':
				{
					'url': resolve_download_url('models-3.0.0', 'arcface_converter_ghost.hash'),
					'path': resolve_relative_path('../.assets/models/arcface_converter_ghost.hash')
				}
			},
			'sources':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'ghost_1_256.onnx'),
					'path': resolve_relative_path('../.assets/models/ghost_1_256.onnx')
				},
				'embedding_converter':
				{
					'url': resolve_download_url('models-3.0.0', 'arcface_converter_ghost.onnx'),
					'path': resolve_relative_path('../.assets/models/arcface_converter_ghost.onnx')
				}
			},
			'type': 'ghost',
			'template': 'arcface_112_v1',
			'size': (256, 256),
			'mean': numpy.array([0.5, 0.5, 0.5], dtype=numpy.float32),
			'standard_deviation': numpy.array([0.5, 0.5, 0.5], dtype=numpy.float32)
		},
		'ghost_2_256':
		{
			'hashes':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'ghost_2_256.hash'),
					'path': resolve_relative_path('../.assets/models/ghost_2_256.hash')
				},
				'embedding_converter':
				{
					'url': resolve_download_url('models-3.0.0', 'arcface_converter_ghost.hash'),
					'path': resolve_relative_path('../.assets/models/arcface_converter_ghost.hash')
				}
			},
			'sources':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'ghost_2_256.onnx'),
					'path': resolve_relative_path('../.assets/models/ghost_2_256.onnx')
				},
				'embedding_converter':
				{
					'url': resolve_download_url('models-3.0.0', 'arcface_converter_ghost.onnx'),
					'path': resolve_relative_path('../.assets/models/arcface_converter_ghost.onnx')
				}
			},
			'type': 'ghost',
			'template': 'arcface_112_v1',
			'size': (256, 256),
			'mean': numpy.array([0.5, 0.5, 0.5], dtype=numpy.float32),
			'standard_deviation': numpy.array([0.5, 0.5, 0.5], dtype=numpy.float32)
		},
		'ghost_3_256':
		{
			'hashes':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'ghost_3_256.hash'),
					'path': resolve_relative_path('../.assets/models/ghost_3_256.hash')
				},
				'embedding_converter':
				{
					'url': resolve_download_url('models-3.0.0', 'arcface_converter_ghost.hash'),
					'path': resolve_relative_path('../.assets/models/arcface_converter_ghost.hash')
				}
			},
			'sources':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'ghost_3_256.onnx'),
					'path': resolve_relative_path('../.assets/models/ghost_3_256.onnx')
				},
				'embedding_converter':
				{
					'url': resolve_download_url('models-3.0.0', 'arcface_converter_ghost.onnx'),
					'path': resolve_relative_path('../.assets/models/arcface_converter_ghost.onnx')
				}
			},
			'type': 'ghost',
			'template': 'arcface_112_v1',
			'size': (256, 256),
			'mean': numpy.array([0.5, 0.5, 0.5], dtype=numpy.float32),
			'standard_deviation': numpy.array([0.5, 0.5, 0.5], dtype=numpy.float32)
		},
		'hififace_unofficial_256':
		{
			'hashes':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.1.0', 'hififace_unofficial_256.hash'),
					'path': resolve_relative_path('../.assets/models/hififace_unofficial_256.hash')
				},
				'embedding_converter':
				{
					'url': resolve_download_url('models-3.1.0', 'arcface_converter_hififace.hash'),
					'path': resolve_relative_path('../.assets/models/arcface_converter_hififace.hash')
				}
			},
			'sources':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.1.0', 'hififace_unofficial_256.onnx'),
					'path': resolve_relative_path('../.assets/models/hififace_unofficial_256.onnx')
				},
				'embedding_converter':
				{
					'url': resolve_download_url('models-3.1.0', 'arcface_converter_hififace.onnx'),
					'path': resolve_relative_path('../.assets/models/arcface_converter_hififace.onnx')
				}
			},
			'type': 'hififace',
			'template': 'mtcnn_512',
			'size': (256, 256),
			'mean': numpy.array([0.5, 0.5, 0.5], dtype=numpy.float32),
			'standard_deviation': numpy.array([0.5, 0.5, 0.5], dtype=numpy.float32)
		},
		'hyperswap_1a_256':
		{
			'hashes':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.3.0', 'hyperswap_1a_256.hash'),
					'path': resolve_relative_path('../.assets/models/hyperswap_1a_256.hash')
				}
			},
			'sources':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.3.0', 'hyperswap_1a_256.onnx'),
					'path': resolve_relative_path('../.assets/models/hyperswap_1a_256.onnx')
				}
			},
			'type': 'hyperswap',
			'template': 'arcface_128',
			'size': (256, 256),
			'mean': numpy.array([0.5, 0.5, 0.5], dtype=numpy.float32),
			'standard_deviation': numpy.array([0.5, 0.5, 0.5], dtype=numpy.float32)
		},
		'hyperswap_1b_256':
		{
			'hashes':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.3.0', 'hyperswap_1b_256.hash'),
					'path': resolve_relative_path('../.assets/models/hyperswap_1b_256.hash')
				}
			},
			'sources':
				{
					'face_swapper':
					{
						'url': resolve_download_url('models-3.3.0', 'hyperswap_1b_256.onnx'),
						'path': resolve_relative_path('../.assets/models/hyperswap_1b_256.onnx')
					}
				},
			'type': 'hyperswap',
			'template': 'arcface_128',
			'size': (256, 256),
			'mean': numpy.array([0.5, 0.5, 0.5], dtype=numpy.float32),
			'standard_deviation': numpy.array([0.5, 0.5, 0.5], dtype=numpy.float32)
		},
		'hyperswap_1c_256':
		{
			'hashes':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.3.0', 'hyperswap_1c_256.hash'),
					'path': resolve_relative_path('../.assets/models/hyperswap_1c_256.hash')
				}
			},
			'sources':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.3.0', 'hyperswap_1c_256.onnx'),
					'path': resolve_relative_path('../.assets/models/hyperswap_1c_256.onnx')
				}
			},
			'type': 'hyperswap',
			'template': 'arcface_128',
			'size': (256, 256),
			'mean': numpy.array([0.5, 0.5, 0.5], dtype=numpy.float32),
			'standard_deviation': numpy.array([0.5, 0.5, 0.5], dtype=numpy.float32)
		},
		'inswapper_128':
		{
			'hashes':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'inswapper_128.hash'),
					'path': resolve_relative_path('../.assets/models/inswapper_128.hash')
				}
			},
			'sources':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'inswapper_128.onnx'),
					'path': resolve_relative_path('../.assets/models/inswapper_128.onnx')
				}
			},
			'type': 'inswapper',
			'template': 'arcface_128',
			'size': (128, 128),
			'mean': numpy.array([0.0, 0.0, 0.0], dtype=numpy.float32),
			'standard_deviation': numpy.array([1.0, 1.0, 1.0], dtype=numpy.float32)
		},
		'inswapper_128_fp16':
		{
			'hashes':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'inswapper_128_fp16.hash'),
					'path': resolve_relative_path('../.assets/models/inswapper_128_fp16.hash')
				}
			},
			'sources':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'inswapper_128_fp16.onnx'),
					'path': resolve_relative_path('../.assets/models/inswapper_128_fp16.onnx')
				}
			},
			'type': 'inswapper',
			'template': 'arcface_128',
			'size': (128, 128),
			'mean': numpy.array([0.0, 0.0, 0.0], dtype=numpy.float32),
			'standard_deviation': numpy.array([1.0, 1.0, 1.0], dtype=numpy.float32)
		},
		'simswap_256':
		{
			'hashes':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'simswap_256.hash'),
					'path': resolve_relative_path('../.assets/models/simswap_256.hash')
				},
				'embedding_converter':
				{
					'url': resolve_download_url('models-3.0.0', 'arcface_converter_simswap.hash'),
					'path': resolve_relative_path('../.assets/models/arcface_converter_simswap.hash')
				}
			},
			'sources':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'simswap_256.onnx'),
					'path': resolve_relative_path('../.assets/models/simswap_256.onnx')
				},
				'embedding_converter':
				{
					'url': resolve_download_url('models-3.0.0', 'arcface_converter_simswap.onnx'),
					'path': resolve_relative_path('../.assets/models/arcface_converter_simswap.onnx')
				}
			},
			'type': 'simswap',
			'template': 'arcface_112_v1',
			'size': (256, 256),
			'mean': numpy.array([0.485, 0.456, 0.406], dtype=numpy.float32),
			'standard_deviation': numpy.array([0.229, 0.224, 0.225], dtype=numpy.float32)
		},
		'simswap_unofficial_512':
		{
			'hashes':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'simswap_unofficial_512.hash'),
					'path': resolve_relative_path('../.assets/models/simswap_unofficial_512.hash')
				},
				'embedding_converter':
				{
					'url': resolve_download_url('models-3.0.0', 'arcface_converter_simswap.hash'),
					'path': resolve_relative_path('../.assets/models/arcface_converter_simswap.hash')
				}
			},
			'sources':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'simswap_unofficial_512.onnx'),
					'path': resolve_relative_path('../.assets/models/simswap_unofficial_512.onnx')
				},
				'embedding_converter':
				{
					'url': resolve_download_url('models-3.0.0', 'arcface_converter_simswap.onnx'),
					'path': resolve_relative_path('../.assets/models/arcface_converter_simswap.onnx')
				}
			},
			'type': 'simswap',
			'template': 'arcface_112_v1',
			'size': (512, 512),
			'mean': numpy.array([0.0, 0.0, 0.0], dtype=numpy.float32),
			'standard_deviation': numpy.array([1.0, 1.0, 1.0], dtype=numpy.float32)
		},
		'uniface_256':
		{
			'hashes':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'uniface_256.hash'),
					'path': resolve_relative_path('../.assets/models/uniface_256.hash')
				}
			},
			'sources':
			{
				'face_swapper':
				{
					'url': resolve_download_url('models-3.0.0', 'uniface_256.onnx'),
					'path': resolve_relative_path('../.assets/models/uniface_256.onnx')
				}
			},
			'type': 'uniface',
			'template': 'ffhq_512',
			'size': (256, 256),
			'mean': numpy.array([0.5, 0.5, 0.5], dtype=numpy.float32),
			'standard_deviation': numpy.array([0.5, 0.5, 0.5], dtype=numpy.float32)
		}
	}

	import os
	trained_model_file_paths = resolve_file_paths(os.path.abspath('.assets/models/trained'))
	logger.info(f"DEBUG: Scanned trained models: {trained_model_file_paths}", __name__)
	if trained_model_file_paths:
		for model_file_path in trained_model_file_paths:
			# Only process ONNX files
			if not model_file_path.endswith('.onnx'):
				continue

			model_name = get_file_name(model_file_path)
			# Only include LoRA models (with _lora suffix), exclude identity models
			if '_lora' in model_name:
				model_set[model_name] = {
					'hashes': {},
					'sources': { 'face_swapper': { 'url': '', 'path': model_file_path } },
					'type': 'inswapper',
					'template': 'arcface_128',
					'size': (128, 128),
					'mean': numpy.array([0.0, 0.0, 0.0], dtype=numpy.float32),
					'standard_deviation': numpy.array([1.0, 1.0, 1.0], dtype=numpy.float32)
				}
	return model_set


def get_inference_pool() -> InferencePool:
	model_names = [ get_model_name() ]
	model_source_set = get_model_options().get('sources')

	return inference_manager.get_inference_pool(__name__, model_names, model_source_set)


def clear_inference_pool() -> None:
	model_names = [ get_model_name() ]
	inference_manager.clear_inference_pool(__name__, model_names)


def get_model_options() -> ModelOptions:
	model_name = get_model_name()

	# Handle LoRA models dynamically
	if model_name and '_lora' in model_name:
		from watserface.filesystem import resolve_relative_path
		import os

		model_path = resolve_relative_path(f'../.assets/models/trained/{model_name}.onnx')
		if os.path.exists(model_path):
			# Create model options for LoRA model
			return {
				'type': 'inswapper',  # LoRA uses inswapper architecture
				'size': (128, 128),
				'template': 'arcface_128',
				'mean': numpy.array([0.0, 0.0, 0.0], dtype=numpy.float32),
				'standard_deviation': numpy.array([1.0, 1.0, 1.0], dtype=numpy.float32),
				'hashes': {
					'face_swapper': {
						'url': None,
						'path': resolve_relative_path(f'../.assets/models/trained/{model_name}.hash')
					}
				},
				'sources': {
					'face_swapper': {
						'url': None,  # Local model
						'path': model_path
					}
				}
			}

	# Standard models from static set
	options = create_static_model_set('full').get(model_name)
	if options is None:
		create_static_model_set.cache_clear()
		options = create_static_model_set('full').get(model_name)
	return options


def get_model_name() -> str:
	model_name = state_manager.get_item('face_swapper_model')

	if has_execution_provider('coreml') and model_name == 'inswapper_128_fp16':
		return 'inswapper_128'
	return model_name


def register_args(program : ArgumentParser) -> None:
	group_processors = find_argument_group(program, 'processors')
	if group_processors:
		group_processors.add_argument('--face-swapper-model', help = wording.get('help.face_swapper_model'), default = config.get_str_value('processors', 'face_swapper_model', 'hyperswap_1a_256'), choices = processors_choices.face_swapper_models)
		known_args, _ = program.parse_known_args()
		face_swapper_pixel_boost_choices = processors_choices.face_swapper_set.get(known_args.face_swapper_model)
		group_processors.add_argument('--face-swapper-pixel-boost', help = wording.get('help.face_swapper_pixel_boost'), default = config.get_str_value('processors', 'face_swapper_pixel_boost', get_first(face_swapper_pixel_boost_choices)), choices = face_swapper_pixel_boost_choices)
		watserface.jobs.job_store.register_step_keys([ 'face_swapper_model', 'face_swapper_pixel_boost' ])


def apply_args(args : Args, apply_state_item : ApplyStateItem) -> None:
	apply_state_item('face_swapper_model', args.get('face_swapper_model'))
	apply_state_item('face_swapper_pixel_boost', args.get('face_swapper_pixel_boost'))


def pre_check() -> bool:
	if get_model_options() is None:
		logger.error(wording.get('model_not_found') or 'Face swapper model not found', __name__)
		return False
	model_hash_set = get_model_options().get('hashes')
	model_source_set = get_model_options().get('sources')

	return conditional_download_hashes(model_hash_set) and conditional_download_sources(model_source_set)


def pre_process(mode : ProcessMode) -> bool:
	model_options = get_model_options()
	if model_options is None:
		# If options are None here, it means pre_check passed (how?) or wasn't called.
		# But pre_check calls get_model_options().
		# If we are here, we might be crashing on None.
		return False

	model_path = model_options.get('sources').get('face_swapper').get('path')
	is_custom_model = 'trained' in model_path
	has_source = has_image(state_manager.get_item('source_paths')) or state_manager.get_item('identity_profile_id')

	if not is_custom_model and not has_source:
		logger.error(wording.get('choose_image_source') + wording.get('exclamation_mark'), __name__)
		return False
	
	if not is_custom_model and not state_manager.get_item('identity_profile_id'):
		source_image_paths = filter_image_paths(state_manager.get_item('source_paths'))
		source_frames = read_static_images(source_image_paths)
		source_faces = get_many_faces(source_frames)
		if not get_one_face(source_faces):
			logger.error(wording.get('no_source_face_detected') + wording.get('exclamation_mark'), __name__)
			return False
	if mode in [ 'output', 'preview' ] and not is_image(state_manager.get_item('target_path')) and not is_video(state_manager.get_item('target_path')):
		logger.error(wording.get('choose_image_or_video_target') + wording.get('exclamation_mark'), __name__)
		return False
	if mode == 'output' and not in_directory(state_manager.get_item('output_path')):
		logger.error(wording.get('specify_image_or_video_output') + wording.get('exclamation_mark'), __name__)
		return False
	if mode == 'output' and not same_file_extension(state_manager.get_item('target_path'), state_manager.get_item('output_path')):
		logger.error(wording.get('match_target_and_output_extension') + wording.get('exclamation_mark'), __name__)
		return False
	return True


def post_process() -> None:
	read_static_image.cache_clear()
	video_manager.clear_video_pool()
	if state_manager.get_item('video_memory_strategy') in [ 'strict', 'moderate' ]:
		get_static_model_initializer.cache_clear()
		clear_inference_pool()
	if state_manager.get_item('video_memory_strategy') == 'strict':
		content_analyser.clear_inference_pool()
		face_classifier.clear_inference_pool()
		face_detector.clear_inference_pool()
		face_landmarker.clear_inference_pool()
		face_masker.clear_inference_pool()
		face_recognizer.clear_inference_pool()


def swap_face(source_face : Face, target_face : Face, temp_vision_frame : VisionFrame) -> VisionFrame:
	from watserface import logger

	model_name = get_model_name()
	model_options = get_model_options()
	model_template = model_options.get('template')
	model_size = model_options.get('size')
	model_type = model_options.get('type')

	logger.info(f'[SWAP_FACE] Using model: {model_name} (type={model_type}, size={model_size})', __name__)

	pixel_boost_size = unpack_resolution(state_manager.get_item('face_swapper_pixel_boost'))
	pixel_boost_total = pixel_boost_size[0] // model_size[0]
	crop_vision_frame, affine_matrix = warp_face_by_face_landmark_5(temp_vision_frame, target_face.landmark_set.get('5/68'), model_template, pixel_boost_size)
	temp_vision_frames = []
	crop_masks = []

	face_mask_types = state_manager.get_item('face_mask_types')
	logger.info(f'[SWAP_FACE] Face mask types: {face_mask_types}', __name__)

	if 'box' in face_mask_types:
		box_mask = create_box_mask(crop_vision_frame, state_manager.get_item('face_mask_blur'), state_manager.get_item('face_mask_padding'))
		crop_masks.append(box_mask)

	if 'occlusion' in face_mask_types:
		occlusion_mask = create_occlusion_mask(crop_vision_frame)
		crop_masks.append(occlusion_mask)

	pixel_boost_vision_frames = implode_pixel_boost(crop_vision_frame, pixel_boost_total, model_size)
	logger.info(f'[SWAP_FACE] Processing {len(pixel_boost_vision_frames)} pixel boost frames...', __name__)

	for pixel_boost_vision_frame in pixel_boost_vision_frames:
		pixel_boost_vision_frame = prepare_crop_frame(pixel_boost_vision_frame)
		pixel_boost_vision_frame = forward_swap_face(source_face, pixel_boost_vision_frame)
		pixel_boost_vision_frame = normalize_crop_frame(pixel_boost_vision_frame)
		temp_vision_frames.append(pixel_boost_vision_frame)
	crop_vision_frame = explode_pixel_boost(temp_vision_frames, pixel_boost_total, model_size, pixel_boost_size)

	if 'area' in face_mask_types:
		face_landmark_68 = cv2.transform(target_face.landmark_set.get('68').reshape(1, -1, 2), affine_matrix).reshape(-1, 2)
		area_mask = create_area_mask(crop_vision_frame, face_landmark_68, state_manager.get_item('face_mask_areas'))
		crop_masks.append(area_mask)

	if 'region' in face_mask_types:
		region_mask = create_region_mask(crop_vision_frame, state_manager.get_item('face_mask_regions'))
		crop_masks.append(region_mask)

	crop_mask = numpy.minimum.reduce(crop_masks).clip(0, 1)
	temp_vision_frame = paste_back(temp_vision_frame, crop_vision_frame, crop_mask, affine_matrix)

	logger.info('[SWAP_FACE] ✓ Face swap complete', __name__)
	return temp_vision_frame


def forward_swap_face(source_face : Face, crop_vision_frame : VisionFrame) -> VisionFrame:
	face_swapper = get_inference_pool().get('face_swapper')
	model_type = get_model_options().get('type')
	face_swapper_inputs = {}

	if has_execution_provider('coreml') and model_type in [ 'ghost', 'uniface' ]:
		face_swapper.set_providers([ watserface.choices.execution_provider_set.get('cpu') ])

	for face_swapper_input in face_swapper.get_inputs():
		if face_swapper_input.name == 'source':
			if model_type in [ 'blendswap', 'uniface' ]:
				face_swapper_inputs[face_swapper_input.name] = prepare_source_frame(source_face)
			else:
				face_swapper_inputs[face_swapper_input.name] = prepare_source_embedding(source_face)
		if face_swapper_input.name == 'target':
			face_swapper_inputs[face_swapper_input.name] = crop_vision_frame

	with conditional_thread_semaphore():
		crop_vision_frame = face_swapper.run(None, face_swapper_inputs)[0][0]

	return crop_vision_frame


def forward_convert_embedding(embedding : Embedding) -> Embedding:
	embedding_converter = get_inference_pool().get('embedding_converter')

	with conditional_thread_semaphore():
		embedding = embedding_converter.run(None,
		{
			'input': embedding
		})[0]

	return embedding


def prepare_source_frame(source_face : Face) -> VisionFrame:
	model_type = get_model_options().get('type')
	source_vision_frame = read_static_image(get_first(state_manager.get_item('source_paths')))

	if model_type == 'blendswap':
		source_vision_frame, _ = warp_face_by_face_landmark_5(source_vision_frame, source_face.landmark_set.get('5/68'), 'arcface_112_v2', (112, 112))
	if model_type == 'uniface':
		source_vision_frame, _ = warp_face_by_face_landmark_5(source_vision_frame, source_face.landmark_set.get('5/68'), 'ffhq_512', (256, 256))
	source_vision_frame = source_vision_frame[:, :, ::-1] / 255.0
	source_vision_frame = source_vision_frame.transpose(2, 0, 1)
	source_vision_frame = numpy.expand_dims(source_vision_frame, axis = 0).astype(numpy.float32)
	return source_vision_frame


def prepare_source_embedding(source_face : Face) -> Embedding:
	model_type = get_model_options().get('type')

	if model_type == 'ghost':
		source_embedding, _ = convert_embedding(source_face)
		source_embedding = source_embedding.reshape(1, -1)
		return source_embedding

	if model_type == 'hyperswap':
		source_embedding = source_face.normed_embedding.reshape((1, -1))
		return source_embedding

	if model_type == 'inswapper':
		model_path = get_model_options().get('sources').get('face_swapper').get('path')
		model_initializer = get_static_model_initializer(model_path)
		source_embedding = source_face.embedding.reshape((1, -1))
		source_embedding = numpy.dot(source_embedding, model_initializer) / numpy.linalg.norm(source_embedding)
		return source_embedding

	_, source_normed_embedding = convert_embedding(source_face)
	source_embedding = source_normed_embedding.reshape(1, -1)
	return source_embedding


def convert_embedding(source_face : Face) -> Tuple[Embedding, Embedding]:
	embedding = source_face.embedding.reshape(-1, 512)
	embedding = forward_convert_embedding(embedding)
	embedding = embedding.ravel()
	normed_embedding = embedding / numpy.linalg.norm(embedding)
	return embedding, normed_embedding


def prepare_crop_frame(crop_vision_frame : VisionFrame) -> VisionFrame:
	model_mean = get_model_options().get('mean')
	model_standard_deviation = get_model_options().get('standard_deviation')

	# Optimization: Convert to float32 and perform in-place normalization
	# to avoid intermediate float64 array allocations (~2x speedup).
	crop_vision_frame = crop_vision_frame[:, :, ::-1].astype(numpy.float32)
	crop_vision_frame /= 255.0
	crop_vision_frame -= model_mean
	crop_vision_frame /= model_standard_deviation
	crop_vision_frame = crop_vision_frame.transpose(2, 0, 1)
	crop_vision_frame = numpy.expand_dims(crop_vision_frame, axis = 0)
	return crop_vision_frame


def normalize_crop_frame(crop_vision_frame : VisionFrame) -> VisionFrame:
	model_type = get_model_options().get('type')
	model_mean = get_model_options().get('mean')
	model_standard_deviation = get_model_options().get('standard_deviation')

	crop_vision_frame = crop_vision_frame.transpose(1, 2, 0)
	if model_type in [ 'ghost', 'hififace', 'hyperswap', 'uniface' ]:
		crop_vision_frame = crop_vision_frame * model_standard_deviation + model_mean
	crop_vision_frame = crop_vision_frame.clip(0, 1)
	crop_vision_frame = crop_vision_frame[:, :, ::-1] * 255
	return crop_vision_frame


def get_reference_frame(source_face : Face, target_face : Face, temp_vision_frame : VisionFrame) -> VisionFrame:
	return swap_face(source_face, target_face, temp_vision_frame)


def get_source_face(source_paths: List[str]) -> Face:
	profile_id = state_manager.get_item('identity_profile_id')
	if profile_id:
		manager = identity_profile.get_identity_manager()
		profile = manager.source_intelligence.load_profile(profile_id)
		if profile:
			embedding_mean = numpy.array(profile.embedding_mean, dtype=numpy.float64)
			return Face(
				bounding_box=None,
				score_set=None,
				landmark_set=None,
				angle=None,
				embedding=embedding_mean,
				normed_embedding=embedding_mean,
				gender=None,
				age=None,
				race=None
			)

	source_frames = read_static_images(source_paths)
	source_faces = []
	for source_frame in source_frames:
		temp_faces = get_many_faces([ source_frame ])
		temp_faces = sort_faces_by_order(temp_faces, 'large-small')
		if temp_faces:
			source_faces.append(get_first(temp_faces))
	return get_average_face(source_faces)


def process_frame(inputs : FaceSwapperInputs, skip_cache : bool = False) -> VisionFrame:
	from watserface import logger

	reference_faces = inputs.get('reference_faces')
	source_face = inputs.get('source_face')
	target_vision_frame = inputs.get('target_vision_frame')

	logger.info(f'[FACE_SWAPPER] process_frame: source_face={source_face is not None}', __name__)

	if not source_face:
		logger.warn('[FACE_SWAPPER] ✗ No source face provided - returning original frame', __name__)
		return target_vision_frame

	many_faces = sort_and_filter_faces(get_many_faces([ target_vision_frame ], skip_cache))
	logger.info(f'[FACE_SWAPPER] Detected {len(many_faces)} faces in target frame', __name__)

	if not many_faces:
		logger.warn('[FACE_SWAPPER] ✗ No faces detected in target - returning original frame', __name__)
		return target_vision_frame

	face_selector_mode = state_manager.get_item('face_selector_mode')
	logger.info(f'[FACE_SWAPPER] Face selector mode: {face_selector_mode}', __name__)

	if face_selector_mode == 'many':
		if many_faces:
			logger.info(f'[FACE_SWAPPER] Swapping {len(many_faces)} faces...', __name__)
			for i, target_face in enumerate(many_faces):
				logger.info(f'[FACE_SWAPPER] Swapping face {i+1}/{len(many_faces)}', __name__)
				target_vision_frame = swap_face(source_face, target_face, target_vision_frame)

	if face_selector_mode == 'one':
		target_face = get_one_face(many_faces)
		if target_face:
			logger.info('[FACE_SWAPPER] Swapping single face...', __name__)
			target_vision_frame = swap_face(source_face, target_face, target_vision_frame)
		else:
			logger.warn('[FACE_SWAPPER] ✗ No suitable face found for "one" mode', __name__)

	if face_selector_mode == 'reference':
		similar_faces = find_similar_faces(many_faces, reference_faces, state_manager.get_item('reference_face_distance'))
		if similar_faces:
			logger.info(f'[FACE_SWAPPER] Swapping {len(similar_faces)} similar faces...', __name__)
			for similar_face in similar_faces:
				target_vision_frame = swap_face(source_face, similar_face, target_vision_frame)
		else:
			logger.warn('[FACE_SWAPPER] ✗ No similar faces found matching reference', __name__)

	logger.info('[FACE_SWAPPER] ✓ Frame processing complete', __name__)
	return target_vision_frame


def process_frames(source_paths : List[str], queue_payloads : List[QueuePayload], update_progress : UpdateProgress) -> None:
	reference_faces = get_reference_faces() if 'reference' in state_manager.get_item('face_selector_mode') else None
	source_face = get_source_face(source_paths)

	for queue_payload in process_manager.manage(queue_payloads):
		target_vision_path = queue_payload['frame_path']
		target_vision_frame = read_image(target_vision_path)
		output_vision_frame = process_frame(
		{
			'reference_faces': reference_faces,
			'source_face': source_face,
			'target_vision_frame': target_vision_frame
		}, skip_cache = True)
		write_image(target_vision_path, output_vision_frame)
		update_progress(1)


def process_image(source_paths : List[str], target_path : str, output_path : str) -> None:
	reference_faces = get_reference_faces() if 'reference' in state_manager.get_item('face_selector_mode') else None
	source_face = get_source_face(source_paths)
	target_vision_frame = read_static_image(target_path)
	output_vision_frame = process_frame(
	{
		'reference_faces': reference_faces,
		'source_face': source_face,
		'target_vision_frame': target_vision_frame
	})
	write_image(output_path, output_vision_frame)


def process_video(source_paths : List[str], temp_frame_paths : List[str]) -> None:
	processors.multi_process_frames(source_paths, temp_frame_paths, process_frames)
