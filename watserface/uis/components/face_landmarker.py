from typing import Optional

import gradio

import watserface.choices
from watserface import face_landmarker, state_manager, wording
from watserface.common_helper import calc_float_step
from watserface.types import FaceLandmarkerModel, Score
from watserface.uis.core import register_ui_component

FACE_LANDMARKER_MODEL_DROPDOWN : Optional[gradio.Dropdown] = None
FACE_LANDMARKER_SCORE_SLIDER : Optional[gradio.Slider] = None


def render() -> None:
	global FACE_LANDMARKER_MODEL_DROPDOWN
	global FACE_LANDMARKER_SCORE_SLIDER

	FACE_LANDMARKER_MODEL_DROPDOWN = gradio.Dropdown(
		label = wording.get('uis.face_landmarker_model_dropdown'),
		info = wording.get('help.face_landmarker_model'),
		choices = watserface.choices.face_landmarker_models,
		value = state_manager.get_item('face_landmarker_model')
	)
	FACE_LANDMARKER_SCORE_SLIDER = gradio.Slider(
		label = wording.get('uis.face_landmarker_score_slider'),
		info = wording.get('help.face_landmarker_score'),
		value = state_manager.get_item('face_landmarker_score'),
		step = calc_float_step(watserface.choices.face_landmarker_score_range),
		minimum = watserface.choices.face_landmarker_score_range[0],
		maximum = watserface.choices.face_landmarker_score_range[-1]
	)
	register_ui_component('face_landmarker_model_dropdown', FACE_LANDMARKER_MODEL_DROPDOWN)
	register_ui_component('face_landmarker_score_slider', FACE_LANDMARKER_SCORE_SLIDER)


def listen() -> None:
	FACE_LANDMARKER_MODEL_DROPDOWN.change(update_face_landmarker_model, inputs = FACE_LANDMARKER_MODEL_DROPDOWN, outputs = FACE_LANDMARKER_MODEL_DROPDOWN)
	FACE_LANDMARKER_SCORE_SLIDER.release(update_face_landmarker_score, inputs = FACE_LANDMARKER_SCORE_SLIDER)


def update_face_landmarker_model(face_landmarker_model : FaceLandmarkerModel) -> gradio.Dropdown:
	face_landmarker.clear_inference_pool()
	state_manager.set_item('face_landmarker_model', face_landmarker_model)

	if face_landmarker.pre_check():
		gradio.Dropdown(value = state_manager.get_item('face_landmarker_model'))
	return gradio.Dropdown()


def update_face_landmarker_score(face_landmarker_score : Score) -> None:
	state_manager.set_item('face_landmarker_score', face_landmarker_score)
