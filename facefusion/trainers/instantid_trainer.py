import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image
import numpy as np
from typing import List, Tuple, Optional
import json

from facefusion import logger, state_manager
from facefusion.filesystem import is_file, is_directory, create_directory


class FaceDataset(Dataset):
    """Dataset class for face training images"""
    
    def __init__(self, image_paths: List[str], transform=None, target_size: Tuple[int, int] = (512, 512)):
        self.image_paths = image_paths
        self.transform = transform
        self.target_size = target_size
        
        # Default transforms if none provided
        if self.transform is None:
            self.transform = transforms.Compose([
                transforms.Resize(self.target_size),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
            ])
    
    def __len__(self):
        return len(self.image_paths)
    
    def __getitem__(self, idx):
        try:
            image_path = self.image_paths[idx]
            image = Image.open(image_path).convert('RGB')
            
            if self.transform:
                image = self.transform(image)
            
            return image, image_path
        except Exception as error:
            logger.error(f"Error loading image {self.image_paths[idx]}: {error}", __name__)
            # Return a blank image on error
            blank_image = torch.zeros(3, *self.target_size)
            return blank_image, self.image_paths[idx]


class InstantIDTrainer:
    """Trainer for InstantID model fine-tuning"""
    
    def __init__(self, config: dict):
        self.config = config
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.optimizer = None
        self.scheduler = None
        self.train_loader = None
        self.training_active = False
        
        # Training metrics
        self.current_epoch = 0
        self.losses = []
        self.best_loss = float('inf')
        
        logger.info(f"InstantID Trainer initialized on device: {self.device}", __name__)
    
    def setup_model(self):
        """Setup the InstantID model for training"""
        try:
            # This is a placeholder for actual InstantID model loading
            # In a real implementation, this would:
            # 1. Load pre-trained InstantID weights from HuggingFace
            # 2. Setup ControlNet and IP-Adapter components
            # 3. Prepare face encoder (InsightFace)
            
            logger.info("Setting up InstantID model...", __name__)
            
            # Placeholder model (replace with actual InstantID components)
            self.model = nn.Sequential(
                nn.Conv2d(3, 64, kernel_size=3, padding=1),
                nn.ReLU(),
                nn.Conv2d(64, 128, kernel_size=3, padding=1),
                nn.ReLU(),
                nn.Conv2d(128, 3, kernel_size=3, padding=1),
                nn.Sigmoid()
            ).to(self.device)
            
            # Setup optimizer
            self.optimizer = optim.Adam(
                self.model.parameters(),
                lr=self.config.get('learning_rate', 0.001),
                weight_decay=self.config.get('weight_decay', 1e-5)
            )
            
            # Setup scheduler
            self.scheduler = optim.lr_scheduler.StepLR(
                self.optimizer,
                step_size=self.config.get('scheduler_step', 50),
                gamma=self.config.get('scheduler_gamma', 0.5)
            )
            
            logger.info("Model setup complete", __name__)
            return True
            
        except Exception as error:
            logger.error(f"Error setting up model: {error}", __name__)
            return False
    
    def setup_dataset(self, dataset_path: str):
        """Setup training dataset"""
        try:
            if not is_directory(dataset_path):
                raise ValueError(f"Dataset path does not exist: {dataset_path}")
            
            # Get all image files
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
            image_paths = []
            
            for filename in os.listdir(dataset_path):
                if any(filename.lower().endswith(ext) for ext in image_extensions):
                    image_paths.append(os.path.join(dataset_path, filename))
            
            if len(image_paths) < 10:
                logger.warn(f"Only {len(image_paths)} images found. Recommend at least 50 for good results.", __name__)
            
            # Create dataset and dataloader
            dataset = FaceDataset(image_paths)
            self.train_loader = DataLoader(
                dataset,
                batch_size=self.config.get('batch_size', 4),
                shuffle=True,
                num_workers=2,
                pin_memory=True if self.device.type == 'cuda' else False
            )
            
            logger.info(f"Dataset setup complete. {len(image_paths)} training images loaded.")
            return True
            
        except Exception as error:
            logger.error(f"Error setting up dataset: {error}")
            return False
    
    def train_epoch(self) -> float:
        """Train for one epoch"""
        if not self.model or not self.train_loader:
            raise ValueError("Model and dataset must be setup before training")
        
        self.model.train()
        epoch_loss = 0.0
        num_batches = 0
        
        for batch_idx, (images, _) in enumerate(self.train_loader):
            if not self.training_active:
                break
            
            images = images.to(self.device)
            
            # Forward pass (placeholder - replace with actual InstantID training step)
            self.optimizer.zero_grad()
            outputs = self.model(images)
            
            # Simple reconstruction loss (replace with proper InstantID loss)
            loss = nn.MSELoss()(outputs, images)
            
            # Backward pass
            loss.backward()
            self.optimizer.step()
            
            epoch_loss += loss.item()
            num_batches += 1
            
            if batch_idx % 10 == 0:
                logger.info(f"Batch {batch_idx}/{len(self.train_loader)}, Loss: {loss.item():.6f}")
        
        return epoch_loss / num_batches if num_batches > 0 else 0.0
    
    def train(self, dataset_path: str, epochs: int, save_path: str) -> bool:
        """Main training loop"""
        try:
            self.training_active = True
            
            # Setup
            if not self.setup_model():
                return False
            
            if not self.setup_dataset(dataset_path):
                return False
            
            # Create save directory
            if not is_directory(save_path):
                create_directory(save_path)
            
            logger.info(f"Starting training for {epochs} epochs")
            
            # Training loop
            for epoch in range(epochs):
                if not self.training_active:
                    logger.info("Training stopped by user")
                    break
                
                self.current_epoch = epoch
                
                # Train one epoch
                avg_loss = self.train_epoch()
                self.losses.append(avg_loss)
                
                # Update scheduler
                self.scheduler.step()
                
                # Save best model
                if avg_loss < self.best_loss:
                    self.best_loss = avg_loss
                    self.save_model(os.path.join(save_path, 'best_model.pth'))
                
                # Periodic saves
                if epoch % self.config.get('save_interval', 20) == 0:
                    self.save_model(os.path.join(save_path, f'model_epoch_{epoch}.pth'))
                
                logger.info(f"Epoch {epoch}/{epochs}, Loss: {avg_loss:.6f}, LR: {self.scheduler.get_last_lr()[0]:.8f}")
            
            # Final save
            if self.training_active:
                self.save_model(os.path.join(save_path, 'final_model.pth'))
                logger.info("Training completed successfully")
            
            return True
            
        except Exception as error:
            logger.error(f"Training error: {error}")
            return False
        finally:
            self.training_active = False
    
    def save_model(self, save_path: str):
        """Save model checkpoint"""
        try:
            checkpoint = {
                'epoch': self.current_epoch,
                'model_state_dict': self.model.state_dict(),
                'optimizer_state_dict': self.optimizer.state_dict(),
                'scheduler_state_dict': self.scheduler.state_dict(),
                'loss': self.losses[-1] if self.losses else None,
                'config': self.config
            }
            
            torch.save(checkpoint, save_path)
            logger.info(f"Model saved to {save_path}")
            
        except Exception as error:
            logger.error(f"Error saving model: {error}")
    
    def load_model(self, load_path: str) -> bool:
        """Load model checkpoint"""
        try:
            if not is_file(load_path):
                logger.error(f"Model file not found: {load_path}")
                return False
            
            checkpoint = torch.load(load_path, map_location=self.device)
            
            # Load model state
            if self.model:
                self.model.load_state_dict(checkpoint['model_state_dict'])
            
            # Load optimizer state
            if self.optimizer:
                self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
            
            # Load scheduler state
            if self.scheduler:
                self.scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
            
            self.current_epoch = checkpoint.get('epoch', 0)
            
            logger.info(f"Model loaded from {load_path}, epoch: {self.current_epoch}")
            return True
            
        except Exception as error:
            logger.error(f"Error loading model: {error}")
            return False
    
    def stop_training(self):
        """Stop the training process"""
        self.training_active = False
        logger.info("Training stop requested")
    
    def get_training_info(self) -> dict:
        """Get current training information"""
        return {
            'current_epoch': self.current_epoch,
            'losses': self.losses,
            'best_loss': self.best_loss,
            'training_active': self.training_active,
            'device': str(self.device)
        }


def create_training_config() -> dict:
    """Create training configuration from state manager"""
    return {
        'learning_rate': state_manager.get_item('training_learning_rate') if state_manager.has_item('training_learning_rate') else 0.001,
        'batch_size': state_manager.get_item('training_batch_size') if state_manager.has_item('training_batch_size') else 4,
        'weight_decay': 1e-5,
        'scheduler_step': 50,
        'scheduler_gamma': 0.5,
        'save_interval': state_manager.get_item('training_save_interval') if state_manager.has_item('training_save_interval') else 20,
        'target_size': (512, 512)
    }


def start_instantid_training(dataset_path: str, epochs: int, save_path: str) -> InstantIDTrainer:
    """Start InstantID training process"""
    config = create_training_config()
    trainer = InstantIDTrainer(config)
    
    # Start training in a separate thread
    import threading
    training_thread = threading.Thread(
        target=trainer.train,
        args=(dataset_path, epochs, save_path)
    )
    training_thread.start()
    
    return trainer