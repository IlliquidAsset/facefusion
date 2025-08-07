from typing import Optional, Callable, Any

import gradio

def create_collapsible_section(title: str, render_content: Callable[[], Any], default_open: bool = True) -> gradio.Group:
	"""Create a collapsible section with a title and content"""
	
	with gradio.Group() as group:
		# Create accordion which is Gradio's built-in collapsible component
		with gradio.Accordion(title, open=default_open):
			render_content()
	
	return group