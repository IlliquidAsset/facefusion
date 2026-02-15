import subprocess

import pytest

from watserface import face_classifier, face_detector, face_landmarker, face_recognizer, state_manager
from watserface.download import conditional_download
from watserface.face_analyser import get_many_faces, get_one_face
from watserface.types import Face
from watserface.vision import read_static_image
from .helper import get_test_example_file, get_test_examples_directory


@pytest.fixture(scope = 'module', autouse = True)
def before_all() -> None:
	conditional_download(get_test_examples_directory(),
	[
		'https://github.com/facefusion/facefusion-assets/releases/download/examples-3.0.0/source.jpg'
	])
	subprocess.run([ 'ffmpeg', '-i', get_test_example_file('source.jpg'), '-vf', 'crop=iw*0.8:ih*0.8', get_test_example_file('source-80crop.jpg') ])
	subprocess.run([ 'ffmpeg', '-i', get_test_example_file('source.jpg'), '-vf', 'crop=iw*0.7:ih*0.7', get_test_example_file('source-70crop.jpg') ])
	subprocess.run([ 'ffmpeg', '-i', get_test_example_file('source.jpg'), '-vf', 'crop=iw*0.6:ih*0.6', get_test_example_file('source-60crop.jpg') ])
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


def test_get_one_face_without_face_classification() -> None:
	source_path = get_test_example_file('source.jpg')
	source_frame = read_static_image(source_path)
	state_manager.set_item('face_selector_gender', None)
	state_manager.set_item('face_selector_race', None)
	state_manager.set_item('face_selector_age_start', None)
	state_manager.set_item('face_selector_age_end', None)
	face_classifier.classify_face = lambda vision_frame, face_landmark_5: (None, None, None)

	many_faces = get_many_faces([ source_frame ])
	face = get_one_face(many_faces)

	assert face.gender is None
	assert face.age is None
	assert face.race is None


def test_get_one_face_with_face_classification() -> None:
	source_path = get_test_example_file('source.jpg')
	source_frame = read_static_image(source_path)
	state_manager.set_item('face_selector_gender', 'female')
	state_manager.set_item('face_selector_race', 'white')
	state_manager.set_item('face_selector_age_start', 0)
	state_manager.set_item('face_selector_age_end', 100)

	many_faces = get_many_faces([ source_frame ])
	face = get_one_face(many_faces)

	assert face.gender is not None
	assert face.age is not None
	assert face.race is not None
