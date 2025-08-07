from typing import Optional
import io

import gradio

from facefusion import logger
from facefusion.uis.core import register_ui_component
from facefusion.uis.types import ComponentOptions

# Optional plotting dependencies
try:
	import matplotlib.pyplot as plt
	import matplotlib.backends.backend_agg as agg
	import numpy as np
	from PIL import Image
	PLOTTING_AVAILABLE = True
except ImportError:
	logger.warn('Matplotlib not available, training plots will be disabled', __name__)
	PLOTTING_AVAILABLE = False

TRAINING_PROGRESS_BAR : Optional[gradio.Progress] = None
TRAINING_LOSS_PLOT : Optional[gradio.Plot] = None
TRAINING_SAMPLES_GALLERY : Optional[gradio.Gallery] = None
TRAINING_METRICS_TEXTBOX : Optional[gradio.Textbox] = None

# Training metrics storage
TRAINING_LOSSES = []
TRAINING_EPOCHS = []


def render() -> None:
	global TRAINING_LOSS_PLOT
	global TRAINING_SAMPLES_GALLERY
	global TRAINING_METRICS_TEXTBOX

	training_loss_plot_options : ComponentOptions =\
	{
		'label': 'Training Loss Progress',
		'show_label': True
	}
	training_samples_gallery_options : ComponentOptions =\
	{
		'label': 'Training Samples',
		'show_label': True,
		'columns': 3,
		'rows': 2,
		'height': 400
	}
	training_metrics_textbox_options : ComponentOptions =\
	{
		'label': 'Training Metrics',
		'interactive': False,
		'lines': 8,
		'value': get_initial_metrics_text()
	}

	with gradio.Group():
		TRAINING_LOSS_PLOT = gradio.Plot(**training_loss_plot_options)
		TRAINING_SAMPLES_GALLERY = gradio.Gallery(**training_samples_gallery_options)
		TRAINING_METRICS_TEXTBOX = gradio.Textbox(**training_metrics_textbox_options)

	register_ui_component('training_loss_plot', TRAINING_LOSS_PLOT)
	register_ui_component('training_samples_gallery', TRAINING_SAMPLES_GALLERY)
	register_ui_component('training_metrics_textbox', TRAINING_METRICS_TEXTBOX)


def listen() -> None:
	# Progress monitoring would be handled by periodic updates
	pass


def update_training_progress(epoch: int, total_epochs: int, loss: float, learning_rate: float) -> tuple:
	"""Update training progress with current metrics"""
	global TRAINING_LOSSES, TRAINING_EPOCHS
	
	# Store training data
	TRAINING_EPOCHS.append(epoch)
	TRAINING_LOSSES.append(loss)
	
	# Create loss plot
	plot_fig = create_loss_plot()
	
	# Update metrics text
	metrics_text = create_metrics_text(epoch, total_epochs, loss, learning_rate)
	
	# Calculate progress percentage
	progress = (epoch / total_epochs) * 100
	
	return plot_fig, metrics_text, progress


def create_loss_plot():
	"""Create matplotlib plot for training loss"""
	if not PLOTTING_AVAILABLE:
		return None
	
	try:
		fig, ax = plt.subplots(figsize=(10, 6))
		
		if TRAINING_EPOCHS and TRAINING_LOSSES:
			ax.plot(TRAINING_EPOCHS, TRAINING_LOSSES, 'b-', linewidth=2, label='Training Loss')
			ax.set_xlabel('Epoch')
			ax.set_ylabel('Loss')
			ax.set_title('Training Loss Over Time')
			ax.legend()
			ax.grid(True, alpha=0.3)
			
			# Add trend line if we have enough data
			if len(TRAINING_EPOCHS) > 5:
				z = np.polyfit(TRAINING_EPOCHS, TRAINING_LOSSES, 1)
				p = np.poly1d(z)
				ax.plot(TRAINING_EPOCHS, p(TRAINING_EPOCHS), "r--", alpha=0.8, label='Trend')
		else:
			ax.text(0.5, 0.5, 'No training data yet', transform=ax.transAxes, 
					ha='center', va='center', fontsize=14)
			ax.set_xlim(0, 100)
			ax.set_ylim(0, 1)
		
		plt.tight_layout()
		return fig
	
	except Exception as error:
		logger.error(f'Error creating loss plot: {error}')
		# Return empty plot on error
		if PLOTTING_AVAILABLE:
			fig, ax = plt.subplots(figsize=(10, 6))
			ax.text(0.5, 0.5, f'Plot error: {error}', transform=ax.transAxes, 
					ha='center', va='center', fontsize=12)
			return fig
		return None


def create_metrics_text(epoch: int, total_epochs: int, loss: float, learning_rate: float) -> str:
	"""Create formatted metrics text"""
	progress_percent = (epoch / total_epochs) * 100
	
	# Calculate average loss
	avg_loss = 'N/A'
	if TRAINING_LOSSES:
		if PLOTTING_AVAILABLE:
			avg_loss = f"{np.mean(TRAINING_LOSSES):.6f}"
		else:
			avg_loss = f"{sum(TRAINING_LOSSES) / len(TRAINING_LOSSES):.6f}"
	
	metrics = f"""Training Progress: {epoch}/{total_epochs} ({progress_percent:.1f}%)

Current Metrics:
• Loss: {loss:.6f}
• Learning Rate: {learning_rate:.6f}
• Epoch: {epoch}

Statistics:
• Total Epochs: {total_epochs}
• Best Loss: {min(TRAINING_LOSSES) if TRAINING_LOSSES else 'N/A'}
• Average Loss: {avg_loss}
• Data Points: {len(TRAINING_LOSSES)}

Status: {'Training...' if epoch < total_epochs else 'Completed'}
"""
	return metrics


def get_initial_metrics_text() -> str:
	"""Get initial metrics text before training starts"""
	return """Training Progress: 0/0 (0.0%)

Current Metrics:
• Loss: N/A
• Learning Rate: N/A
• Epoch: N/A

Statistics:
• Total Epochs: N/A
• Best Loss: N/A
• Average Loss: N/A
• Data Points: 0

Status: Ready to start training
"""


def reset_training_data() -> None:
	"""Reset training data for new training session"""
	global TRAINING_LOSSES, TRAINING_EPOCHS
	TRAINING_LOSSES = []
	TRAINING_EPOCHS = []


def add_training_samples(sample_images: list) -> list:
	"""Add sample images to gallery"""
	try:
		# This would be called during training to show progress samples
		return sample_images
	except Exception as error:
		logger.error(f'Error updating training samples: {error}')
		return []


def export_training_report() -> str:
	"""Export training metrics as a report"""
	try:
		if not TRAINING_EPOCHS:
			return "No training data to export"
		
		report = f"""Training Report
===============

Training Summary:
• Total Epochs: {max(TRAINING_EPOCHS) if TRAINING_EPOCHS else 0}
• Final Loss: {TRAINING_LOSSES[-1] if TRAINING_LOSSES else 'N/A'}
• Best Loss: {min(TRAINING_LOSSES) if TRAINING_LOSSES else 'N/A'}
• Loss Improvement: {TRAINING_LOSSES[0] - TRAINING_LOSSES[-1] if len(TRAINING_LOSSES) > 1 else 'N/A'}

Training completed successfully.
"""
		return report
	except Exception as error:
		return f"Error generating report: {error}"