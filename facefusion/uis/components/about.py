from typing import Optional

import gradio

from facefusion import metadata

# Removed the buttons that were taking up space


def render() -> None:
	# Just show the title without buttons
	with gradio.Row():
		gradio.HTML(f"""
		<div style="text-align: center; padding: 10px;">
			<h2 style="margin: 0; color: #1f2937;">{metadata.get('name')} {metadata.get('version')} - Training Edition</h2>
			<p style="margin: 5px 0; color: #6b7280; font-size: 0.9em;">{metadata.get('description')}</p>
		</div>
		""")
