"""
Training script for RNN, LSTM, and BiLSTM behavior prediction models.
Trains all three models and saves the best performing one.
"""
import os
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.tensorboard import SummaryWriter
import numpy as np
from tqdm import tqdm

# Add app directory to path
sys.path.append(str(Path(__file__).parent))

from app.behavior_models import BehaviorRNN, BehaviorLSTM, BehaviorBiLSTM
from app.behavior_preprocessing import BehaviorDataProcessor, analyze_behavior_data


class BehaviorModelTrainer:
    """
    Trainer class for behavior prediction models.
    Handles training loop, validation, and model saving.
    """
    
    def __init__(
        self,
        model: nn.Module,
        model_name: str,
        device: torch.device,
        learning_rate: float = 0.001,
        weight_decay: float = 1e-5
    ):
        self.model = model.to(device)
        self.model_name = model_name
        self.device = device
        
        # Loss and optimizer
        self.criterion = nn.CrossEntropyLoss()
        self.optimizer = optim.Adam(
            self.model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay
        )
        
        # Learning rate scheduler
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer,
            mode='min',
            factor=0.5,
            patience=3,
            verbose=True
        )
        
        # Tracking
        self.train_losses = []
        self.val_losses = []
        self.val_accuracies = []
        self.best_val_loss = float('inf')
        self.best_val_acc = 0.0
        
    def train_epoch(self, train_loader, epoch: int) -> float:
        """Train for one epoch."""
        self.model.train()
        total_loss = 0
        correct = 0
        total = 0
        
        pbar = tqdm(train_loader, desc=f"Epoch {epoch} [Train]")
        for sequences, labels in pbar:
            sequences = sequences.to(self.device)
            labels = labels.to(self.device)
            
            # Forward pass
            self.optimizer.zero_grad()
            outputs, _ = self.model(sequences)
            loss = self.criterion(outputs, labels)
            
            # Backward pass
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=5.0)
            self.optimizer.step()
            
            # Statistics
            total_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
            
            # Update progress bar
            pbar.set_postfix({
                'loss': f'{loss.item():.4f}',
                'acc': f'{100 * correct / total:.2f}%'
            })
        
        avg_loss = total_loss / len(train_loader)
        accuracy = 100 * correct / total
        
        return avg_loss, accuracy
    
    def validate(self, val_loader, epoch: int) -> tuple:
        """Validate the model."""
        self.model.eval()
        total_loss = 0
        correct = 0
        total = 0
        
        with torch.no_grad():
            pbar = tqdm(val_loader, desc=f"Epoch {epoch} [Val]")
            for sequences, labels in pbar:
                sequences = sequences.to(self.device)
                labels = labels.to(self.device)
                
                outputs, _ = self.model(sequences)
                loss = self.criterion(outputs, labels)
                
                total_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                total += labels.size(0)
                correct += (predicted == labels).sum().item()
                
                pbar.set_postfix({
                    'loss': f'{loss.item():.4f}',
                    'acc': f'{100 * correct / total:.2f}%'
                })
        
        avg_loss = total_loss / len(val_loader)
        accuracy = 100 * correct / total
        
        return avg_loss, accuracy
    
    def train(
        self,
        train_loader,
        val_loader,
        num_epochs: int,
        save_dir: str,
        writer: SummaryWriter = None
    ):
        """
        Full training loop.
        
        Args:
            train_loader: Training data loader
            val_loader: Validation data loader
            num_epochs: Number of epochs to train
            save_dir: Directory to save model checkpoints
            writer: TensorBoard writer (optional)
        """
        print(f"\n{'='*60}")
        print(f"Training {self.model_name}")
        print(f"{'='*60}\n")
        
        for epoch in range(1, num_epochs + 1):
            # Train
            train_loss, train_acc = self.train_epoch(train_loader, epoch)
            self.train_losses.append(train_loss)
            
            # Validate
            val_loss, val_acc = self.validate(val_loader, epoch)
            self.val_losses.append(val_loss)
            self.val_accuracies.append(val_acc)
            
            # Learning rate scheduling
            self.scheduler.step(val_loss)
            
            # Log to tensorboard
            if writer:
                writer.add_scalar(f'{self.model_name}/train_loss', train_loss, epoch)
                writer.add_scalar(f'{self.model_name}/train_acc', train_acc, epoch)
                writer.add_scalar(f'{self.model_name}/val_loss', val_loss, epoch)
                writer.add_scalar(f'{self.model_name}/val_acc', val_acc, epoch)
                writer.add_scalar(f'{self.model_name}/lr', self.optimizer.param_groups[0]['lr'], epoch)
            
            # Print epoch summary
            print(f"\nEpoch {epoch}/{num_epochs}")
            print(f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}%")
            print(f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.2f}%")
            print(f"Learning Rate: {self.optimizer.param_groups[0]['lr']:.6f}")
            
            # Save best model
            if val_loss < self.best_val_loss:
                self.best_val_loss = val_loss
                self.save_checkpoint(save_dir, 'best_loss')
                print(f"✓ Saved best loss model (val_loss: {val_loss:.4f})")
            
            if val_acc > self.best_val_acc:
                self.best_val_acc = val_acc
                self.save_checkpoint(save_dir, 'best_acc')
                print(f"✓ Saved best accuracy model (val_acc: {val_acc:.2f}%)")
            
            # Save checkpoint every 5 epochs
            if epoch % 5 == 0:
                self.save_checkpoint(save_dir, f'epoch_{epoch}')
            
            print()
        
        # Save final model
        self.save_checkpoint(save_dir, 'final')
        
        print(f"\n{'='*60}")
        print(f"Training completed for {self.model_name}")
        print(f"Best Val Loss: {self.best_val_loss:.4f}")
        print(f"Best Val Accuracy: {self.best_val_acc:.2f}%")
        print(f"{'='*60}\n")
    
    def save_checkpoint(self, save_dir: str, checkpoint_name: str):
        """Save model checkpoint."""
        os.makedirs(save_dir, exist_ok=True)
        path = os.path.join(save_dir, f'{self.model_name}_{checkpoint_name}.pth')
        torch.save(self.model.state_dict(), path)
    
    def test(self, test_loader) -> dict:
        """Test the model and return metrics."""
        self.model.eval()
        correct = 0
        total = 0
        
        # Per-class accuracy
        class_correct = {}
        class_total = {}
        
        with torch.no_grad():
            for sequences, labels in tqdm(test_loader, desc="Testing"):
                sequences = sequences.to(self.device)
                labels = labels.to(self.device)
                
                outputs, _ = self.model(sequences)
                _, predicted = torch.max(outputs.data, 1)
                
                total += labels.size(0)
                correct += (predicted == labels).sum().item()
                
                # Per-class statistics
                for label, pred in zip(labels, predicted):
                    label_item = label.item()
                    if label_item not in class_total:
                        class_total[label_item] = 0
                        class_correct[label_item] = 0
                    
                    class_total[label_item] += 1
                    if label_item == pred.item():
                        class_correct[label_item] += 1
        
        overall_acc = 100 * correct / total
        
        # Calculate per-class accuracy
        per_class_acc = {}
        for cls in class_total:
            per_class_acc[cls] = 100 * class_correct[cls] / class_total[cls]
        
        return {
            'overall_accuracy': overall_acc,
            'per_class_accuracy': per_class_acc,
            'total_samples': total
        }


def main():
    parser = argparse.ArgumentParser(description='Train behavior prediction models')
    parser.add_argument('--data', type=str, required=True, help='Path to behavior CSV file')
    parser.add_argument('--models', nargs='+', default=['rnn', 'lstm', 'bilstm'],
                        choices=['rnn', 'lstm', 'bilstm'], help='Models to train')
    parser.add_argument('--epochs', type=int, default=20, help='Number of epochs')
    parser.add_argument('--batch-size', type=int, default=64, help='Batch size')
    parser.add_argument('--lr', type=float, default=0.001, help='Learning rate')
    parser.add_argument('--hidden-dim', type=int, default=128, help='Hidden dimension')
    parser.add_argument('--embedding-dim', type=int, default=64, help='Embedding dimension')
    parser.add_argument('--num-layers', type=int, default=2, help='Number of RNN layers')
    parser.add_argument('--dropout', type=float, default=0.3, help='Dropout rate')
    parser.add_argument('--seq-length', type=int, default=10, help='Sequence length')
    parser.add_argument('--save-dir', type=str, default='weights/behavior_models',
                        help='Directory to save models')
    parser.add_argument('--no-cuda', action='store_true', help='Disable CUDA')
    
    args = parser.parse_args()
    
    # Setup device
    device = torch.device('cuda' if torch.cuda.is_available() and not args.no_cuda else 'cpu')
    print(f"Using device: {device}")
    
    # Analyze data
    print("\n" + "="*60)
    print("Analyzing behavior data...")
    print("="*60)
    stats = analyze_behavior_data(args.data)
    print(json.dumps(stats, indent=2))
    
    # Prepare data
    print("\n" + "="*60)
    print("Preparing data...")
    print("="*60)
    processor = BehaviorDataProcessor(
        seq_length=args.seq_length,
        min_seq_length=3,
        max_seq_len=50
    )
    
    train_loader, val_loader, test_loader = processor.prepare_dataloaders(
        csv_path=args.data,
        batch_size=args.batch_size,
        test_size=0.2,
        val_size=0.1
    )
    
    vocab_size = processor.encoder.vocab_size
    num_classes = processor.encoder.num_actions - 1  # Exclude PAD token
    
    print(f"Vocabulary size: {vocab_size}")
    print(f"Number of classes: {num_classes}")
    
    # TensorBoard writer
    log_dir = f'runs/behavior_training_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    writer = SummaryWriter(log_dir)
    
    # Model configurations
    model_configs = {
        'rnn': {
            'class': BehaviorRNN,
            'name': 'RNN'
        },
        'lstm': {
            'class': BehaviorLSTM,
            'name': 'LSTM'
        },
        'bilstm': {
            'class': BehaviorBiLSTM,
            'name': 'BiLSTM'
        }
    }
    
    # Train each model
    results = {}
    
    for model_type in args.models:
        config = model_configs[model_type]
        
        # Create model
        model = config['class'](
            vocab_size=vocab_size,
            embedding_dim=args.embedding_dim,
            hidden_dim=args.hidden_dim,
            num_layers=args.num_layers,
            dropout=args.dropout,
            num_classes=num_classes
        )
        
        # Create trainer
        trainer = BehaviorModelTrainer(
            model=model,
            model_name=config['name'],
            device=device,
            learning_rate=args.lr
        )
        
        # Train
        trainer.train(
            train_loader=train_loader,
            val_loader=val_loader,
            num_epochs=args.epochs,
            save_dir=args.save_dir,
            writer=writer
        )
        
        # Test
        print(f"\nTesting {config['name']}...")
        test_results = trainer.test(test_loader)
        results[model_type] = test_results
        
        print(f"\nTest Results for {config['name']}:")
        print(f"Overall Accuracy: {test_results['overall_accuracy']:.2f}%")
        print(f"Per-class Accuracy: {test_results['per_class_accuracy']}")
    
    # Save results
    results_path = os.path.join(args.save_dir, 'training_results.json')
    os.makedirs(args.save_dir, exist_ok=True)
    with open(results_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*60}")
    print("Training Summary")
    print(f"{'='*60}")
    for model_type, result in results.items():
        print(f"{model_type.upper()}: {result['overall_accuracy']:.2f}%")
    
    # Find best model
    best_model = max(results.items(), key=lambda x: x[1]['overall_accuracy'])
    print(f"\nBest Model: {best_model[0].upper()} ({best_model[1]['overall_accuracy']:.2f}%)")
    print(f"\nResults saved to: {results_path}")
    print(f"TensorBoard logs: {log_dir}")
    print(f"Run: tensorboard --logdir={log_dir}")
    
    writer.close()


if __name__ == '__main__':
    main()
