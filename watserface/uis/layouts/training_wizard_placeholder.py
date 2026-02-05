from typing import Optional, Any, Tuple, List
import os
import gradio
import pandas as pd
import time

from watserface import state_manager
from watserface.filesystem import resolve_relative_path
from watserface.uis.components import about, footer, training_source, identity_loader, terminal
from watserface.training import core as training_core

# --- Wizard State & Navigation ---
WIZARD_STEP : Optional[gradio.State] = None
STEP_INDICATOR : Optional[gradio.HTML] = None

# --- Step Containers ---
STEP_1_CONTAINER : Optional[gradio.Group] = None
STEP_2_CONTAINER : Optional[gradio.Group] = None
STEP_3_CONTAINER : Optional[gradio.Group] = None

# --- Step 2 Specifics ---
MODEL_NAME : Optional[gradio.Textbox] = None
EPOCHS : Optional[gradio.Slider] = None

# --- Step 3 Specifics ---
REVIEW_MARKDOWN : Optional[gradio.Markdown] = None
START_BUTTON : Optional[gradio.Button] = None
STOP_BUTTON : Optional[gradio.Button] = None
STATUS_TEXT : Optional[gradio.Textbox] = None
TELEMETRY_GROUP : Optional[gradio.Group] = None
OVERALL_PROGRESS : Optional[gradio.HTML] = None
EPOCH_PROGRESS : Optional[gradio.HTML] = None
BATCH_PROGRESS : Optional[gradio.HTML] = None
METRICS_HTML : Optional[gradio.HTML] = None
LOSS_PLOT : Optional[gradio.LinePlot] = None

# --- Navigation Controls ---
NAV_ROW : Optional[gradio.Row] = None
BACK_BUTTON : Optional[gradio.Button] = None
NEXT_BUTTON : Optional[gradio.Button] = None
ERROR_BOX : Optional[gradio.Textbox] = None


def generate_step_html(current_step: int) -> str:
    """Generate the HTML for the wizard step indicator."""
    steps = [
        {"num": 1, "label": "Data Source"},
        {"num": 2, "label": "Configuration"},
        {"num": 3, "label": "Train"}
    ]

    html = '<div style="display: flex; justify-content: center; margin-bottom: 20px; align-items: center;">'

    for i, step in enumerate(steps):
        is_active = step["num"] == current_step
        is_completed = step["num"] < current_step

        color = "#ff9900" if is_active or is_completed else "#555"
        weight = "bold" if is_active else "normal"
        opacity = "1.0" if is_active or is_completed else "0.5"

        # Circle
        html += f'''
        <div style="display: flex; flex-direction: column; align-items: center; width: 100px;">
            <div style="width: 30px; height: 30px; border-radius: 50%; background-color: {color}; color: white; display: flex; align-items: center; justify-content: center; font-weight: bold; margin-bottom: 5px;">
                {step["num"]}
            </div>
            <div style="font-size: 0.9em; font-weight: {weight}; opacity: {opacity}; text-align: center;">
                {step["label"]}
            </div>
        </div>
        '''

        # Line
        if i < len(steps) - 1:
            line_color = "#ff9900" if is_completed else "#555"
            html += f'<div style="height: 2px; width: 60px; background-color: {line_color}; margin-top: -20px;"></div>'

    html += '</div>'
    return html


def generate_progress_html(label: str, percentage: float, detail_text: str) -> str:
    """Generate HTML for a progress bar using the template"""
    template_path = resolve_relative_path("uis/assets/training_progress.html")
    if not os.path.exists(template_path):
        return f"<div>{label}: {percentage:.1f}% - {detail_text}</div>"

    with open(template_path, 'r') as f:
        template = f.read()

    return template.format(
        label=label,
        percentage=min(max(percentage, 0), 100),
        detail_text=detail_text
    )


def generate_metrics_html(telemetry: dict) -> str:
    """Generate HTML for the metrics panel"""
    epoch_time = telemetry.get('epoch_time', 'N/A')
    eta = telemetry.get('eta', 'N/A')
    device = telemetry.get('device', 'N/A')
    loss = telemetry.get('loss', 'N/A')

    return f"""
    <div class="glass-metrics-panel">
        <div class="metric-row">
            <span class="metric-label">Device</span>
            <span class="metric-value">{device}</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Epoch Time</span>
            <span class="metric-value">{epoch_time}</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">ETA</span>
            <span class="metric-value">{eta}</span>
        </div>
        <div class="metric-row">
            <span class="metric-label">Current Loss</span>
            <span class="metric-value">{loss}</span>
        </div>
    </div>
    """


def wrapped_start_identity_training(
    model_name: str,
    epochs: int,
    identity_mode: str,
    existing_identity_id: Optional[str] = None,
    source_type: str = "Upload Files",
    face_set_id: Optional[str] = None,
    source_files: Any = None,
    save_as_face_set: bool = False,
    face_set_name: Optional[str] = None,
    face_set_description: Optional[str] = None
):
    """Wrapper to format identity training output with throttling and telemetry"""
    last_update = 0
    loss_history = []
    historical_loaded = False

    # Handle "Load Existing" mode - use existing identity ID as model name
    if identity_mode == "Load Existing":
        if not existing_identity_id:
            yield "❌ Error: Please select an existing identity to enrich", None, generate_progress_html("Overall Progress", 0, "Error"), generate_progress_html("Epoch Progress", 0, "Error"), generate_progress_html("Batch Progress", 0, "Error"), generate_metrics_html({}), gradio.update(visible=True)
            return
        model_name = existing_identity_id  # Use existing identity ID

    # Determine parameters based on source type
    if source_type == "Face Set":
        training_kwargs = {
            'model_name': model_name,
            'epochs': epochs,
            'face_set_id': face_set_id
        }
    else:  # "Upload Files"
        training_kwargs = {
            'model_name': model_name,
            'epochs': epochs,
            'source_files': source_files,
            'save_as_face_set': save_as_face_set,
            'new_face_set_name': face_set_name if save_as_face_set else None
        }

    # Show the telemetry group immediately
    yield "Initializing...", None, generate_progress_html("Overall Progress", 0, "Starting..."), generate_progress_html("Epoch Progress", 0, "Starting..."), generate_progress_html("Batch Progress", 0, "Starting..."), generate_metrics_html({}), gradio.update(visible=True)

    for status_data in training_core.start_identity_training(**training_kwargs):
        current_time = time.time()

        # Parse status data
        message = status_data[0] if isinstance(status_data, list) else str(status_data)
        telemetry = status_data[1] if isinstance(status_data, list) and len(status_data) > 1 else {}

        # Prepare updates
        plot_update = None
        overall_html = generate_progress_html("Overall Progress", 0, "Initializing...")
        epoch_html = generate_progress_html("Epoch Progress", 0, "Waiting...")
        batch_html = generate_progress_html("Batch Progress", 0, "Waiting...")
        metrics_html = generate_metrics_html({})

        if telemetry:
            # Load historical data if available
            if not historical_loaded and 'historical_loss' in telemetry:
                historical_data = telemetry['historical_loss']
                for entry in historical_data:
                    loss_history.append({
                        'epoch': float(entry['epoch']),
                        'loss': float(entry['loss'])
                    })
                historical_loaded = True
                plot_update = pd.DataFrame(loss_history)

            # Update history and plot
            loss_val = telemetry.get('loss') or telemetry.get('current_loss')
            if loss_val is not None:
                try:
                    epoch_val = int(telemetry.get('epoch', 0))
                    if 'batch' in telemetry and 'total_batches' in telemetry:
                        batch_fraction = int(telemetry['batch']) / int(telemetry['total_batches'])
                        epoch_val = (epoch_val - 1) + batch_fraction

                    loss_history.append({
                        'epoch': float(epoch_val),
                        'loss': float(loss_val)
                    })
                    plot_update = pd.DataFrame(loss_history)
                except (ValueError, TypeError):
                    pass

            # Extract progress values
            def parse_pct(val):
                if isinstance(val, str) and '%' in val:
                    return float(val.strip('%'))
                if isinstance(val, (int, float)) and val <= 1.0:
                    return val * 100
                return float(val)

            overall_pct = parse_pct(telemetry.get('overall_progress', 0))
            epoch_pct = parse_pct(telemetry.get('epoch_progress', 0))
            batch_pct = parse_pct(telemetry.get('batch_progress', 0))

            if 'batch' in telemetry and 'total_batches' in telemetry:
                batch_pct = (int(telemetry['batch']) / int(telemetry['total_batches'])) * 100

            # Generate HTML
            overall_html = generate_progress_html("Overall Progress", overall_pct, f"Epoch {telemetry.get('epoch', 0)}/{telemetry.get('total_epochs', '?')}")
            epoch_html = generate_progress_html("Epoch Progress", epoch_pct, f"Loss: {telemetry.get('loss', 'N/A')}")
            batch_html = generate_progress_html("Batch Progress", batch_pct, f"Batch {telemetry.get('batch', 0)}/{telemetry.get('total_batches', '?')}")
            metrics_html = generate_metrics_html(telemetry)

        # Only update UI every 0.5 seconds to avoid flickering
        if current_time - last_update >= 0.5:
            last_update = current_time
            yield message, plot_update, overall_html, epoch_html, batch_html, metrics_html, gradio.update(visible=True)

    # Always yield the final status
    yield "Training Complete", pd.DataFrame(loss_history) if loss_history else None, generate_progress_html("Overall", 100, "Done"), generate_progress_html("Epoch", 100, "Done"), generate_progress_html("Batch", 100, "Done"), metrics_html, gradio.update(visible=True)


def wrapped_stop_training():
    return training_core.stop_training()


def pre_check() -> bool:
    return True


def render() -> gradio.Blocks:
    global WIZARD_STEP, STEP_INDICATOR
    global STEP_1_CONTAINER, STEP_2_CONTAINER, STEP_3_CONTAINER
    global MODEL_NAME, EPOCHS
    global REVIEW_MARKDOWN, START_BUTTON, STOP_BUTTON, STATUS_TEXT
    global TELEMETRY_GROUP, OVERALL_PROGRESS, EPOCH_PROGRESS, BATCH_PROGRESS, METRICS_HTML, LOSS_PLOT
    global NAV_ROW, BACK_BUTTON, NEXT_BUTTON, ERROR_BOX

    with gradio.Blocks() as layout:
        about.render()

        # Wizard State
        WIZARD_STEP = gradio.State(1)

        # Header / Stepper
        STEP_INDICATOR = gradio.HTML(value=generate_step_html(1))

        # === STEP 1: Data Source ===
        with gradio.Group(visible=True) as STEP_1_CONTAINER:
            gradio.Markdown("### 📂 Step 1: Select Training Data")
            training_source.render()

        # === STEP 2: Configuration ===
        with gradio.Group(visible=False) as STEP_2_CONTAINER:
            gradio.Markdown("### ⚙️ Step 2: Configure Model")
            with gradio.Row():
                with gradio.Column():
                    identity_loader.render()
                    MODEL_NAME = gradio.Textbox(label="Identity Model Name", placeholder="e.g. my_actor_v1", info="The name required to use this model later.")
                    EPOCHS = gradio.Slider(label="Epochs", minimum=1, maximum=1000, value=100, step=1, info="More epochs = longer training, potentially better results.")

        # === STEP 3: Review & Train ===
        with gradio.Group(visible=False) as STEP_3_CONTAINER:
            gradio.Markdown("### 🚀 Step 3: Review & Train")
            REVIEW_MARKDOWN = gradio.Markdown("Please review your settings before starting.")

            with gradio.Row():
                START_BUTTON = gradio.Button("▶ Start Training", variant="primary", elem_classes=["primary-btn"])
                STOP_BUTTON = gradio.Button("⏹ Stop", variant="stop", elem_classes=["stop-btn"])

            STATUS_TEXT = gradio.Textbox(label="Current Status", value="Ready", interactive=False, lines=2)

            with gradio.Group(visible=False) as TELEMETRY_GROUP:
                gradio.Markdown("### 📊 Live Telemetry")
                with gradio.Row():
                    with gradio.Column(scale=1):
                        OVERALL_PROGRESS = gradio.HTML(value=generate_progress_html("Overall Progress", 0, "Idle"))
                        EPOCH_PROGRESS = gradio.HTML(value=generate_progress_html("Epoch Progress", 0, "Idle"))
                        BATCH_PROGRESS = gradio.HTML(value=generate_progress_html("Batch Progress", 0, "Idle"))

                    with gradio.Column(scale=1):
                        LOSS_PLOT = gradio.LinePlot(
                            label="Training Loss",
                            x="epoch", y="loss",
                            title="Loss over Time",
                            width=400, height=200,
                            tooltip=["epoch", "loss"],
                            overlay_point=True
                        )
                        METRICS_HTML = gradio.HTML(value=generate_metrics_html({}))

        # Navigation & Errors
        with gradio.Row() as NAV_ROW:
            BACK_BUTTON = gradio.Button("⬅ Back", variant="secondary", visible=False)
            NEXT_BUTTON = gradio.Button("Next ➡", variant="primary")

        ERROR_BOX = gradio.Textbox(label="Notice", visible=False, interactive=False)

        # Terminal and Footer
        terminal.render()
        footer.render()

    return layout


def validate_and_next(
    current_step: int,
    source_type: str,
    source_files: Any,
    face_set_id: Optional[str],
    identity_mode: str,
    existing_id: Optional[str],
    model_name: str,
    epochs: int
):
    """Validate current step and move to next if valid"""
    error = ""
    next_step = current_step

    # Validation Logic
    if current_step == 1:
        if source_type == "Upload Files":
            if not source_files:
                error = "❌ Please upload at least one image or video file."
            else:
                next_step = 2
        elif source_type == "Face Set":
            if not face_set_id:
                error = "❌ Please select a Face Set."
            else:
                next_step = 2

    elif current_step == 2:
        if identity_mode == "New Identity":
            if not model_name or not model_name.strip():
                error = "❌ Please enter a name for the new identity model."
            else:
                next_step = 3
        elif identity_mode == "Load Existing":
            if not existing_id:
                error = "❌ Please select an existing identity to enrich."
            else:
                next_step = 3

    # Update UI based on results
    step_indicator = generate_step_html(next_step)

    # Visibility updates
    show_s1 = (next_step == 1)
    show_s2 = (next_step == 2)
    show_s3 = (next_step == 3)

    # Generate review text if moving to step 3
    review_text = ""
    if next_step == 3:
        if identity_mode == "Load Existing":
            name_display = existing_id
            mode_display = "Enrich Existing Identity"
        else:
            name_display = model_name
            mode_display = "New Identity"

        source_display = source_type
        if source_type == "Face Set":
            source_display += f" (ID: {face_set_id})"

        review_text = f"""
        **Training Configuration Summary:**
        *   **Mode:** {mode_display}
        *   **Model Name:** {name_display}
        *   **Source:** {source_display}
        *   **Epochs:** {epochs}
        """

    # Button Visibility
    # Back button: visible if step > 1
    show_back = (next_step > 1)
    # Next button: visible if step < 3
    show_next = (next_step < 3)

    return (
        next_step,              # WIZARD_STEP
        step_indicator,         # STEP_INDICATOR
        gradio.Group(visible=show_s1), # STEP_1_CONTAINER
        gradio.Group(visible=show_s2), # STEP_2_CONTAINER
        gradio.Group(visible=show_s3), # STEP_3_CONTAINER
        gradio.Button(visible=show_back), # BACK_BUTTON
        gradio.Button(visible=show_next), # NEXT_BUTTON
        gradio.Textbox(value=error, visible=bool(error)), # ERROR_BOX
        gradio.Markdown(value=review_text) # REVIEW_MARKDOWN
    )


def go_back(current_step: int):
    """Move back one step"""
    prev_step = max(1, current_step - 1)
    step_indicator = generate_step_html(prev_step)

    show_s1 = (prev_step == 1)
    show_s2 = (prev_step == 2)
    show_s3 = (prev_step == 3)

    # Button Visibility
    show_back = (prev_step > 1)
    show_next = (prev_step < 3)

    return (
        prev_step,
        step_indicator,
        gradio.Group(visible=show_s1),
        gradio.Group(visible=show_s2),
        gradio.Group(visible=show_s3),
        gradio.Button(visible=show_back), # BACK_BUTTON
        gradio.Button(visible=show_next), # NEXT_BUTTON
        gradio.Textbox(visible=False) # Clear errors
    )


def listen() -> None:
    training_source.listen()
    identity_loader.listen()
    terminal.listen()

    # Navigation
    NEXT_BUTTON.click(
        validate_and_next,
        inputs=[
            WIZARD_STEP,
            training_source.SOURCE_TYPE_RADIO,
            training_source.TRAINING_SOURCE_FILE,
            training_source.FACE_SET_DROPDOWN,
            identity_loader.IDENTITY_MODE_RADIO,
            identity_loader.EXISTING_IDENTITY_DROPDOWN,
            MODEL_NAME,
            EPOCHS
        ],
        outputs=[
            WIZARD_STEP,
            STEP_INDICATOR,
            STEP_1_CONTAINER,
            STEP_2_CONTAINER,
            STEP_3_CONTAINER,
            BACK_BUTTON,
            NEXT_BUTTON,
            ERROR_BOX,
            REVIEW_MARKDOWN
        ]
    )

    BACK_BUTTON.click(
        go_back,
        inputs=[WIZARD_STEP],
        outputs=[
            WIZARD_STEP,
            STEP_INDICATOR,
            STEP_1_CONTAINER,
            STEP_2_CONTAINER,
            STEP_3_CONTAINER,
            BACK_BUTTON,
            NEXT_BUTTON,
            ERROR_BOX
        ]
    )

    # Training Actions
    START_BUTTON.click(
        wrapped_start_identity_training,
        inputs=[
            MODEL_NAME,
            EPOCHS,
            identity_loader.IDENTITY_MODE_RADIO,
            identity_loader.EXISTING_IDENTITY_DROPDOWN,
            training_source.SOURCE_TYPE_RADIO,
            training_source.FACE_SET_DROPDOWN,
            training_source.TRAINING_SOURCE_FILE,
            training_source.SAVE_AS_FACE_SET_CHECKBOX,
            training_source.FACE_SET_NAME,
            training_source.FACE_SET_DESCRIPTION
        ],
        outputs=[
            STATUS_TEXT,
            LOSS_PLOT,
            OVERALL_PROGRESS,
            EPOCH_PROGRESS,
            BATCH_PROGRESS,
            METRICS_HTML,
            TELEMETRY_GROUP
        ]
    )

    STOP_BUTTON.click(wrapped_stop_training, outputs=[STATUS_TEXT])


def run(ui : gradio.Blocks) -> None:
    ui.launch(inbrowser = state_manager.get_item('open_browser'), server_name = state_manager.get_item('server_name'), server_port = state_manager.get_item('server_port'), show_error = True)
