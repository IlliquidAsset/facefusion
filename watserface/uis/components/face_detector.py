from typing import Optional, Sequence, Tuple

import gradio

import watserface.choices
from watserface import face_detector, state_manager, wording
from watserface.common_helper import calc_float_step, get_last
from watserface.types import Angle, FaceDetectorModel, Score
from watserface.uis.core import register_ui_component
from watserface.uis.types import ComponentOptions

FACE_DETECTOR_MODEL_DROPDOWN : Optional[gradio.Dropdown] = None
FACE_DETECTOR_SIZE_DROPDOWN : Optional[gradio.Dropdown] = None
FACE_DETECTOR_ANGLES_CHECKBOX_GROUP : Optional[gradio.CheckboxGroup] = None
FACE_DETECTOR_SCORE_SLIDER : Optional[gradio.Slider] = None


def render() -> None:
	global FACE_DETECTOR_MODEL_DROPDOWN
	global FACE_DETECTOR_SIZE_DROPDOWN
	global FACE_DETECTOR_ANGLES_CHECKBOX_GROUP
	global FACE_DETECTOR_SCORE_SLIDER

	face_detector_size_dropdown_options : ComponentOptions =\
	{
		'label': wording.get('uis.face_detector_size_dropdown'),
		'value': state_manager.get_item('face_detector_size')
	}
	if state_manager.get_item('face_detector_size') in watserface.choices.face_detector_set[state_manager.get_item('face_detector_model')]:
		face_detector_size_dropdown_options['choices'] = watserface.choices.face_detector_set[state_manager.get_item('face_detector_model')]
	with gradio.Row():
		FACE_DETECTOR_MODEL_DROPDOWN = gradio.Dropdown(
			label = wording.get('uis.face_detector_model_dropdown'),
			info = wording.get('help.face_detector_model'),
			choices = watserface.choices.face_detector_models,
			value = state_manager.get_item('face_detector_model')
		)
		FACE_DETECTOR_SIZE_DROPDOWN = gradio.Dropdown(
			info = wording.get('help.face_detector_size'),
			**face_detector_size_dropdown_options
		)
	FACE_DETECTOR_ANGLES_CHECKBOX_GROUP = gradio.CheckboxGroup(
		label = wording.get('uis.face_detector_angles_checkbox_group'),
		info = wording.get('help.face_detector_angles'),
		choices = watserface.choices.face_detector_angles,
		value = state_manager.get_item('face_detector_angles')
	)
	FACE_DETECTOR_SCORE_SLIDER = gradio.Slider(
		label = wording.get('uis.face_detector_score_slider'),
		info = wording.get('help.face_detector_score'),
		value = state_manager.get_item('face_detector_score'),
		step = calc_float_step(watserface.choices.face_detector_score_range),
		minimum = watserface.choices.face_detector_score_range[0],
		maximum = watserface.choices.face_detector_score_range[-1]
	)
	register_ui_component('face_detector_model_dropdown', FACE_DETECTOR_MODEL_DROPDOWN)
	register_ui_component('face_detector_size_dropdown', FACE_DETECTOR_SIZE_DROPDOWN)
	register_ui_component('face_detector_angles_checkbox_group', FACE_DETECTOR_ANGLES_CHECKBOX_GROUP)
	register_ui_component('face_detector_score_slider', FACE_DETECTOR_SCORE_SLIDER)


def listen() -> None:
	FACE_DETECTOR_MODEL_DROPDOWN.change(update_face_detector_model, inputs = FACE_DETECTOR_MODEL_DROPDOWN, outputs = [ FACE_DETECTOR_MODEL_DROPDOWN, FACE_DETECTOR_SIZE_DROPDOWN ])
	FACE_DETECTOR_SIZE_DROPDOWN.change(update_face_detector_size, inputs = FACE_DETECTOR_SIZE_DROPDOWN)
	FACE_DETECTOR_ANGLES_CHECKBOX_GROUP.change(update_face_detector_angles, inputs = FACE_DETECTOR_ANGLES_CHECKBOX_GROUP, outputs = FACE_DETECTOR_ANGLES_CHECKBOX_GROUP)
	FACE_DETECTOR_SCORE_SLIDER.release(update_face_detector_score, inputs = FACE_DETECTOR_SCORE_SLIDER)


def update_face_detector_model(face_detector_model : FaceDetectorModel) -> Tuple[gradio.Dropdown, gradio.Dropdown]:
	face_detector.clear_inference_pool()
	state_manager.set_item('face_detector_model', face_detector_model)

	if face_detector.pre_check():
		face_detector_size_choices = watserface.choices.face_detector_set.get(state_manager.get_item('face_detector_model'))
		state_manager.set_item('face_detector_size', get_last(face_detector_size_choices))
		return gradio.Dropdown(value = state_manager.get_item('face_detector_model')), gradio.Dropdown(value = state_manager.get_item('face_detector_size'), choices = face_detector_size_choices)
	return gradio.Dropdown(), gradio.Dropdown()


def update_face_detector_size(face_detector_size : str) -> None:
	state_manager.set_item('face_detector_size', face_detector_size)


def update_face_detector_angles(face_detector_angles : Sequence[Angle] = None) -> gradio.CheckboxGroup:
	if face_detector_angles is None:
		face_detector_angles = watserface.choices.face_detector_angles
	if not face_detector_angles:
		face_detector_angles = watserface.choices.face_detector_angles
	state_manager.set_item('face_detector_angles', face_detector_angles)
	return gradio.CheckboxGroup(value = state_manager.get_item('face_detector_angles'))


def update_face_detector_score(face_detector_score : Score) -> None:
	state_manager.set_item('face_detector_score', face_detector_score)
