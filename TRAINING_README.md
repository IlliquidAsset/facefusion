# FaceFusion Dataset Training

This document explains how to use the new dataset training functionality added to FaceFusion.

## Overview

FaceFusion now includes a comprehensive training tab that allows you to:

- Create custom face models from your own datasets
- Train InstantID models for consistent face generation
- Manage training datasets with validation
- Monitor training progress with real-time metrics
- Export trained models for use in FaceFusion

## Quick Start

### 1. Launch with Training Tab

```bash
python facefusion.py run --ui-layouts training
```

Or use both default and training tabs:

```bash
python facefusion.py run --ui-layouts default training
```

### 2. Install Training Dependencies

The training functionality requires additional dependencies. Install them with:

```bash
pip install -r requirements-training.txt
```

**Required packages:**
- PyTorch 2.0+
- Transformers 4.30+
- Diffusers 0.20+
- HuggingFace Hub
- And more (see requirements-training.txt)

### 3. Prepare Your Dataset

1. **Dataset Folder**: Create or specify a folder containing your training images
2. **Image Requirements**:
   - Format: JPG, PNG, BMP, WEBP, TIFF
   - Resolution: 512x512 recommended (will be auto-resized)
   - Quantity: 50-100+ images for good results
   - Quality: Clear, well-lit faces from various angles

3. **Upload Images**: Use the upload interface or manually copy files to your dataset folder

## Training Models

### InstantID Training

**Best for:** High-quality, consistent face generation with identity preservation

**Features:**
- Zero-shot identity-preserving generation
- ControlNet + IP-Adapter architecture
- Support for various downstream tasks
- Based on state-of-the-art research from 2024

**Training Parameters:**
- **Epochs**: 50-200 (start with 100)
- **Batch Size**: 2-8 (adjust based on GPU memory)
- **Learning Rate**: 0.0001-0.001 (0.001 default)
- **Save Interval**: 10-50 epochs

### SimSwap Training

**Status:** Coming Soon
**Features:** High-fidelity face swapping with temporal consistency

### Custom Models

**Status:** Framework ready for additional model integrations

## Training Interface

### Dataset Manager

- **Dataset Path**: Specify folder containing training images
- **Upload Images**: Drag and drop or select multiple images
- **Dataset Validation**: Check image count and quality
- **Preview Gallery**: View your training images

### Training Options

- **Model Selection**: Choose InstantID, SimSwap, or Custom
- **Hyperparameters**: Adjust epochs, batch size, learning rate
- **Save Settings**: Configure checkpoint intervals

### Training Progress

- **Real-time Metrics**: Loss, learning rate, epoch progress
- **Training Plots**: Visual loss curves and trends (requires matplotlib)
- **Sample Gallery**: Generated samples during training
- **Status Monitoring**: Current training state and statistics

### Model Management

- **Output Path**: Specify where to save trained models
- **Base Models**: Download required pre-trained weights
- **Export Options**: Save models in compatible formats

## Training Pipeline

### 1. Dataset Preparation

```
Dataset Folder Structure:
├── my_training_dataset/
│   ├── image_001.jpg
│   ├── image_002.jpg
│   ├── ...
│   └── image_n.jpg
```

### 2. Model Setup

The training process automatically:
- Downloads base models from HuggingFace
- Initializes training architecture
- Sets up data loaders with augmentation
- Configures optimizers and schedulers

### 3. Training Loop

- **Forward Pass**: Process batch through model
- **Loss Calculation**: Compute reconstruction/identity loss
- **Backward Pass**: Update model weights
- **Logging**: Track metrics and save checkpoints

### 4. Model Export

Trained models are saved as:
- **Checkpoints**: `.pth` files with full training state
- **Model Weights**: Optimized for inference
- **Configuration**: Training parameters and metadata

## Best Practices

### Dataset Quality

1. **Diversity**: Include various angles, expressions, lighting
2. **Consistency**: Same person across all images
3. **Quality**: High resolution, clear features
4. **Quantity**: 100+ images recommended

### Training Configuration

1. **Start Small**: Begin with fewer epochs to test
2. **Monitor Loss**: Watch for convergence patterns
3. **Save Frequently**: Use shorter save intervals initially
4. **GPU Memory**: Adjust batch size based on available VRAM

### Troubleshooting

**Common Issues:**

1. **Out of Memory**: Reduce batch size or image resolution
2. **Slow Training**: Enable mixed precision, use faster GPU
3. **Poor Quality**: Increase dataset size, adjust learning rate
4. **No Convergence**: Check dataset quality, reduce learning rate

## Model Integration

### Using Trained Models

Once training is complete, your custom models can be used with:

1. **Face Swapper**: Load as custom face model
2. **Deep Swapper**: Integration with existing workflow  
3. **Export**: Convert to standard formats

### Model Files

Training produces several files:

```
models/trained/
├── best_model.pth          # Best performing checkpoint
├── final_model.pth         # Final training state
├── model_epoch_20.pth      # Periodic checkpoints
└── training_config.json    # Training parameters
```

## Advanced Features

### Custom Training Loops

The training framework is extensible:

- **Custom Datasets**: Implement your own dataset classes
- **Custom Architectures**: Add new model types
- **Custom Losses**: Implement specialized loss functions
- **Custom Metrics**: Add training monitoring

### Research Integration

Built on latest research:

- **InstantID**: Zero-shot identity preservation (2024)
- **IP-Adapter**: Image prompt adapter for text-to-image
- **ControlNet**: Controllable image generation
- **Diffusion Models**: State-of-the-art generative AI

## Technical Details

### Model Architecture

**InstantID Components:**
- Face Encoder: InsightFace ArcFace embeddings
- IP-Adapter: Cross-attention injection
- ControlNet: Structural conditioning
- Diffusion Backbone: Stable Diffusion base

### Training Optimizations

- **Mixed Precision**: FP16 training for speed
- **Gradient Accumulation**: Effective larger batch sizes
- **Learning Rate Scheduling**: Adaptive rate adjustment
- **Data Augmentation**: Improved generalization

### Hardware Requirements

**Minimum:**
- GPU: 8GB VRAM (RTX 3070, RTX 4060 Ti)
- RAM: 16GB system memory
- Storage: 50GB free space

**Recommended:**
- GPU: 16GB+ VRAM (RTX 4080, RTX 4090)
- RAM: 32GB+ system memory
- Storage: 100GB+ NVMe SSD

## Support and Resources

### Documentation
- [InstantID Paper](https://github.com/instantX-research/InstantID)
- [HuggingFace Diffusers](https://huggingface.co/docs/diffusers)
- [IP-Adapter Documentation](https://github.com/tencent-ailab/IP-Adapter)

### Model Repositories
- [InstantX/InstantID](https://huggingface.co/InstantX/InstantID)
- [netrunner-exe/SimSwap-models](https://huggingface.co/netrunner-exe/SimSwap-models)

### Community
- GitHub Issues: Report bugs and request features
- Discussions: Share training results and tips
- Examples: Community-contributed training scripts

---

**Note**: This is a powerful tool for research and creative applications. Please use responsibly and in accordance with applicable laws and ethical guidelines.