# FaceFusion Modernization: Streamlined PRD for Claude Code

*Optimized for single-shot implementation*

## Executive Summary

**Mission:** Modernize FaceFusion into a stable, user-friendly face processing platform by fixing critical issues, streamlining the UI, and adding intelligent preview selection - all executable by Claude Code in one session.

**Core Innovation:** Transform the current parameter-heavy interface into an intuitive workflow where users see preview options and click their preferred result, automatically locking in optimal settings.

**Success Criteria:**
- ✅ Zero import errors, stable startup in <5 seconds
- ✅ Working end-to-end: upload → preview → select → export  
- ✅ Preview-driven UX eliminates need for technical parameter adjustment
- ✅ Training tab functional for custom model creation
- ✅ Deployable to HF Spaces with GPU/CPU fallback

## Implementation Strategy (Auto-Execute)

### Claude Code Configuration
```python
# AUTO-ACCEPT MODE - No confirmation prompts
AUTO_ACCEPT_ALL_CHANGES = True
REQUIRE_USER_CONFIRMATION = False
APPLY_FIXES_AUTOMATICALLY = True

# GIT WORKFLOW - Push after every major step
GIT_AUTO_PUSH = True
COMMIT_FREQUENTLY = True  # Changes don't persist without pushes
```

### Critical Git Workflow
```bash
# MANDATORY: Push after each milestone
git add -A && git commit -m "fix: resolve import errors and dependencies" && git push origin main
git add -A && git commit -m "feat: implement preview selection system" && git push origin main  
git add -A && git commit -m "feat: streamlined UI with smart defaults" && git push origin main
git add -A && git commit -m "feat: training tab and model management" && git push origin main
git add -A && git commit -m "feat: production ready deployment" && git push origin main

# Push immediately after ANY significant change!
```

## User Experience Transformation

### Current Problem: Technical Overwhelm
```
User sees: "Face Detector Model", "Landmarker Model", "Mask Type", "Enhancement Strength"
User thinks: "I have no idea what these mean" → abandons workflow
```

### Solution: Preview-Driven Selection
```
User sees: 3 preview options labeled "Fast", "Balanced", "Quality"
User thinks: "I like option 2" → clicks it → gets perfect result
```

### Target Workflow (4 Steps)
```
1. UPLOAD: Drag source photos + target video
2. PREVIEW: See 3 smart preview options (15s, 45s, 90s processing time)
3. SELECT: Click preferred preview 
4. EXPORT: Download final result with those exact settings
```

## Technical Implementation Plan

### Phase 1: Foundation Stabilization
**Priority: Fix blocking issues first**

```python
# 1. Resolve all import errors
# 2. Update gradio compatibility (5.25.2)
# 3. Fix dependency conflicts in requirements.txt
# 4. Ensure basic face swap pipeline works
# 5. Test on both CPU and GPU

CRITICAL_FIXES = [
    "fix_import_errors",           # Blocking everything
    "update_gradio_api",          # Breaking changes
    "resolve_onnxruntime",        # GPU acceleration 
    "fix_opencv_issues",          # ARM compatibility
    "validate_basic_pipeline"     # End-to-end test
]
```

### Phase 2: Smart Preview System
**Core UX Innovation**

```python
# Instead of exposing 20+ technical parameters,
# Generate 3 intelligent preview combinations:

SMART_PRESETS = {
    "fast": {
        "detector": "yolov5n", 
        "enhancer": None,
        "resolution": 512,
        "time_estimate": "~15 seconds",
        "description": "Quick draft quality"
    },
    "balanced": {
        "detector": "retinaface", 
        "enhancer": "gfpgan",
        "resolution": 768, 
        "time_estimate": "~45 seconds",
        "description": "Good quality, reasonable speed"
    },
    "quality": {
        "detector": "retinaface",
        "enhancer": "codeformer", 
        "resolution": 1024,
        "time_estimate": "~90 seconds", 
        "description": "Best quality, slower processing"
    }
}

class PreviewGenerator:
    async def generate_smart_previews(self, source: Image, target: Image) -> List[PreviewResult]:
        """Generate 3 preview options using different quality presets"""
        previews = []
        for preset_name, config in SMART_PRESETS.items():
            preview = await self.process_with_config(source, target, config)
            previews.append(PreviewResult(
                image=preview,
                preset=preset_name, 
                config=config,
                estimated_time=config["time_estimate"]
            ))
        return previews
```

### Phase 3: Streamlined UI Architecture
**Modernize the tab structure**

```python
# Current: 8+ confusing tabs with overlapping settings
# Target: 4 clear tabs with logical flow

NEW_TAB_STRUCTURE = {
    "Upload": "Source photos + target video/image",
    "Preview": "3 smart options to choose from", 
    "Export": "Download settings and final processing",
    "Training": "Custom model creation (advanced users)"
}

# Hide advanced settings by default
ADVANCED_SETTINGS_HIDDEN = True
SHOW_TECHNICAL_PARAMETERS = False  # Only for power users
```

### Phase 4: Training Integration
**Leverage existing training infrastructure**

```python
# Build on existing processors/modules structure
# Add UI for model management and dataset handling

class TrainingManager:
    def create_dataset(self, images: List[Image]) -> Dataset:
        """Validate and prepare training dataset"""
        
    def start_training(self, dataset: Dataset, config: TrainingConfig) -> TrainingJob:
        """Launch training with progress tracking"""
        
    def register_model(self, checkpoint_path: str, metadata: Dict) -> RegisteredModel:
        """Register trained model for use in face swapping"""

# Training Tab UI Components:
# - Dataset uploader with validation
# - Training progress with ETA
# - Model registry with thumbnails
# - One-click model selection for inference
```

## Detailed Implementation Checklist

### ✅ Phase 1: Critical Fixes (Push after completion)
```bash
# Execute these in order, push after each group:

# 1.1 Dependency Resolution
- [ ] Fix requirements.txt version conflicts
- [ ] Update gradio to 5.25.2 API compatibility  
- [ ] Resolve onnxruntime GPU/CPU detection
- [ ] Fix OpenCV import errors on ARM/M1

# 1.2 Core Pipeline Validation  
- [ ] Test basic face detection works
- [ ] Verify face swapping functionality
- [ ] Ensure video processing pipeline
- [ ] Validate output generation

git add -A && git commit -m "fix: resolve critical dependency and pipeline issues" && git push origin main
```

### ✅ Phase 2: Preview System (Push after completion)
```bash
# 2.1 Preview Generator
- [ ] Implement smart preset configurations
- [ ] Create preview generation pipeline
- [ ] Add processing time estimation
- [ ] Build preview comparison UI

# 2.2 Parameter Simplification
- [ ] Hide advanced settings by default
- [ ] Map preset selection to technical parameters
- [ ] Add "Advanced" toggle for power users
- [ ] Validate parameter combinations work

git add -A && git commit -m "feat: implement smart preview selection system" && git push origin main
```

### ✅ Phase 3: UI Modernization (Push after completion)
```bash
# 3.1 Tab Structure
- [ ] Redesign tab layout (Upload/Preview/Export/Training)
- [ ] Implement drag-and-drop file uploads
- [ ] Add progress indicators and status updates
- [ ] Create responsive design for mobile

# 3.2 User Experience Polish
- [ ] Add helpful tooltips and guidance
- [ ] Implement error handling with clear messages
- [ ] Create empty state walkthroughs
- [ ] Add keyboard navigation support

git add -A && git commit -m "feat: modernized UI with streamlined workflow" && git push origin main
```

### ✅ Phase 4: Training Features (Push after completion)
```bash
# 4.1 Dataset Management
- [ ] Build dataset upload and validation
- [ ] Implement face consistency checking
- [ ] Add dataset quality scoring
- [ ] Create dataset preview gallery

# 4.2 Training Pipeline
- [ ] Integrate existing training modules
- [ ] Add progress tracking with WebSocket updates
- [ ] Implement training job queue management
- [ ] Create model registry and selection

git add -A && git commit -m "feat: complete training system with model management" && git push origin main
```

### ✅ Phase 5: Production Ready (Push after completion)
```bash
# 5.1 Performance & Reliability
- [ ] Optimize memory usage and GPU allocation
- [ ] Add comprehensive error handling
- [ ] Implement automatic fallback (GPU→CPU)
- [ ] Create health check system

# 5.2 Deployment
- [ ] Test HF Spaces compatibility
- [ ] Validate ZeroGPU integration
- [ ] Create app.py launcher
- [ ] Add environment detection

git add -A && git commit -m "feat: production deployment with performance optimization" && git push origin main
```

## Configuration Strategy

### Smart Defaults (facefusion.ini)
```ini
# User-friendly defaults that work out of the box
[face_detector]
model = retinaface  # Reliable, good quality
score_threshold = 0.5
nms_threshold = 0.4

[face_swapper] 
model = inswapper_128  # Good balance of speed/quality
blend_ratio = 0.8

[output_creation]
image_quality = 85
video_encoder = libx264
video_quality = 23  # Good compression

[execution]
providers = cuda,cpu  # Try GPU first, fallback to CPU
thread_count = 4
queue_count = 1

[uis]
default_preset = balanced  # Start with balanced quality
show_advanced = false      # Hide complexity initially
```

### Preset System
```python
# Instead of exposing all parameters, provide intelligent presets
UI_PRESETS = {
    "fast_draft": {
        "face_detector_model": "yolov5n",
        "face_swapper_model": "inswapper_128", 
        "face_enhancer_model": None,
        "output_video_resolution": "720p",
        "description": "Quick results, draft quality"
    },
    "balanced": {
        "face_detector_model": "retinaface",
        "face_swapper_model": "inswapper_128",
        "face_enhancer_model": "gfpgan_1.4", 
        "output_video_resolution": "1080p",
        "description": "Good quality, reasonable speed"
    },
    "high_quality": {
        "face_detector_model": "retinaface",
        "face_swapper_model": "ghost_3_256",
        "face_enhancer_model": "codeformer",
        "output_video_resolution": "original",
        "description": "Best quality, slower processing"
    }
}
```

## Realistic Performance Targets

```python
PERFORMANCE_EXPECTATIONS = {
    # Achievable targets based on hardware constraints
    "cold_start_time": 5,        # seconds (realistic with model caching)
    "preview_generation": 45,     # seconds for 3 previews
    "single_image_swap": 15,      # seconds on GPU
    "video_processing": 0.5,      # fps (realistic for 1080p on T4)
    "training_time": 1800,        # 30 minutes (realistic for quality)
    "concurrent_users": 2,        # on HF Spaces T4
    "memory_usage": 6,           # GB peak (with optimization)
    "cpu_fallback_slowdown": 5    # 5x slower than GPU
}
```

## Critical Dependencies & Environment

### Updated Requirements (Fixed Versions)
```txt
# Core dependencies with known working versions
gradio==5.25.2
numpy==2.2.4
opencv-python-headless==4.11.0.86  # Headless for containers
onnx==1.17.0
onnxruntime-gpu==1.22.0
torch>=2.0.0,<3.0.0
torchvision>=0.15.0
Pillow>=10.0.0
tqdm>=4.67.0
psutil>=7.0.0
scipy==1.15.2

# Face processing
insightface>=0.7.3
retinaface-pytorch>=0.0.9

# Video processing
ffmpeg-python>=0.2.0

# Training (optional)
accelerate>=0.25.0
transformers>=4.35.0
diffusers>=0.24.0
```

### Environment Detection
```python
# app.py - Smart launcher for different environments
import os
import sys
import subprocess

def detect_environment():
    """Detect deployment environment and configure accordingly"""
    if os.getenv("SPACE_ID"):
        return "huggingface_spaces"
    elif os.getenv("COLAB_GPU"):
        return "google_colab"
    else:
        return "local"

def setup_for_environment(env_type):
    """Configure app based on environment"""
    if env_type == "huggingface_spaces":
        # HF Spaces optimizations
        os.environ["OMP_NUM_THREADS"] = "4"
        os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    elif env_type == "google_colab":
        # Colab optimizations
        os.environ["OMP_NUM_THREADS"] = "2"
    
    # Install appropriate dependencies
    if env_type in ["huggingface_spaces", "google_colab"]:
        subprocess.run([
            sys.executable, "-m", "pip", "install", 
            "--no-cache-dir", "-r", "requirements.txt"
        ], check=True)

if __name__ == "__main__":
    env = detect_environment()
    setup_for_environment(env)
    
    # Launch with appropriate settings
    subprocess.run([
        sys.executable, "facefusion.py", "run",
        "--execution-providers", "cuda", "cpu"
    ], check=True)
```

## Final Instructions for Claude Code

### Execution Order (Critical!)
1. **START HERE**: Fix all import errors and dependency conflicts
2. **Build preview system**: 3-option preview with smart presets
3. **Modernize UI**: Streamlined tabs, hide complexity
4. **Add training**: Dataset management and model registry  
5. **Polish for production**: Error handling, deployment ready

### Auto-Accept Mode
```python
# Execute ALL changes without prompting
# Apply ALL fixes automatically
# Do NOT ask for confirmation
# Push to git after every major milestone
```

### Success Definition
**Working app where users can:**
1. Upload photos and video
2. See 3 preview options ("Fast", "Balanced", "Quality")  
3. Click their preferred option
4. Download final result
5. Optionally train custom models

**Technical requirements:**
- Zero import errors
- Works on CPU and GPU
- Deploys to HF Spaces successfully
- 2-3 concurrent users supported

---

**Claude Code: Execute this plan completely. Auto-accept all changes. Push to git frequently. Focus on user experience over technical complexity. Make it work reliably first, optimize second.**