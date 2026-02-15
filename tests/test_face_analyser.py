import cv2
import pytest

from watserface import face_classifier, face_detector, face_landmarker, face_recognizer, state_manager
from watserface.download import conditional_download
from watserface.face_analyser import get_many_faces, get_one_face
from watserface.types import Face
from watserface.vision import read_static_image
from .helper import get_test_example_file, get_test_examples_directory


def crop_image(input_path : str, output_path : str, scale : float) -> None:
	image = cv2.imread(input_path)
	height, width = image.shape[:2]
	crop_height = int(height * scale)
	crop_width = int(width * scale)
	start_y = (height - crop_height) // 2
	start_x = (width - crop_width) // 2
	image = image[start_y:start_y + crop_height, start_x:start_x + crop_width]
	cv2.imwrite(output_path, image)


@pytest.fixture(scope = 'module', autouse = True)
def before_all() -> None:
	conditional_download(get_test_examples_directory(),
	[
		'https://github.com/facefusion/facefusion-assets/releases/download/examples-3.0.0/source.jpg'
	])
	crop_image(get_test_example_file('source.jpg'), get_test_example_file('source-80crop.jpg'), 0.8)
	crop_image(get_test_example_file('source.jpg'), get_test_example_file('source-70crop.jpg'), 0.7)
	crop_image(get_test_example_file('source.jpg'), get_test_example_file('source-60crop.jpg'), 0.6)
	state_manager.init_item('execution_device_id', '0')
	state_manager.init_item('execution_providers', [ 'cpu' ])
	state_manager.init_item('download_providers', [ 'github' ])
	state_manager.init_item('face_detector_angles', [ 0 ])
	state_manager.init_item('face_detector_model', 'many')
	state_manager.init_item('face_detector_score', 0.5)
	state_manager.init_item('face_landmarker_model', 'many')
	state_manager.init_item('face_landmarker_score', 0.5)
	face_classifier.pre_check()
	face_landmarker.pre_check()
	face_recognizer.pre_check()


@pytest.fixture(autouse = True)
def before_each() -> None:
	face_classifier.clear_inference_pool()
	face_detector.clear_inference_pool()
	face_landmarker.clear_inference_pool()
	face_recognizer.clear_inference_pool()


def test_get_one_face_with_retinaface() -> None:
	state_manager.init_item('face_detector_model', 'retinaface')
	state_manager.init_item('face_detector_size', '320x320')
	face_detector.pre_check()

	source_paths =\
	[
		get_test_example_file('source.jpg'),
		get_test_example_file('source-80crop.jpg'),
		get_test_example_file('source-70crop.jpg'),
		get_test_example_file('source-60crop.jpg')
	]

	for source_path in source_paths:
		source_frame = read_static_image(source_path)
		many_faces = get_many_faces([ source_frame ])
		face = get_one_face(many_faces)

		assert isinstance(face, Face)


def test_get_one_face_with_scrfd() -> None:
	state_manager.init_item('face_detector_model', 'scrfd')
	state_manager.init_item('face_detector_size', '640x640')
	face_detector.pre_check()

	source_paths =\
	[
		get_test_example_file('source.jpg'),
		get_test_example_file('source-80crop.jpg'),
		get_test_example_file('source-70crop.jpg'),
		get_test_example_file('source-60crop.jpg')
	]

	for source_path in source_paths:
		source_frame = read_static_image(source_path)
		many_faces = get_many_faces([ source_frame ])
		face = get_one_face(many_faces)

		assert isinstance(face, Face)


def test_get_one_face_with_yoloface() -> None:
	state_manager.init_item('face_detector_model', 'yoloface')
	state_manager.init_item('face_detector_size', '640x640')
	face_detector.pre_check()

	source_paths =\
	[
		get_test_example_file('source.jpg'),
		get_test_example_file('source-80crop.jpg'),
		get_test_example_file('source-70crop.jpg'),
		get_test_example_file('source-60crop.jpg')
	]

	for source_path in source_paths:
		source_frame = read_static_image(source_path)
		many_faces = get_many_faces([ source_frame ])
		face = get_one_face(many_faces)

		assert isinstance(face, Face)


def test_get_many_faces() -> None:
	source_path = get_test_example_file('source.jpg')
	source_frame = read_static_image(source_path)
	many_faces = get_many_faces([ source_frame, source_frame, source_frame ])

	assert isinstance(many_faces[0], Face)
	assert isinstance(many_faces[1], Face)
	assert isinstance(many_faces[2], Face)
