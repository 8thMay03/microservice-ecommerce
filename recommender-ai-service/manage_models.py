"""
Utility script for managing behavior prediction models.
Provides commands for listing, testing, and cleaning models.
"""
import os
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime
import torch

sys.path.append(str(Path(__file__).parent))

from app.behavior_models import BehaviorRNN, BehaviorLSTM, BehaviorBiLSTM


def list_models(weights_dir: str):
    """List all available trained models."""
    print("\n" + "="*80)
    print("  AVAILABLE MODELS")
    print("="*80 + "\n")
    
    weights_path = Path(weights_dir)
    
    if not weights_path.exists():
        print(f"❌ Weights directory not found: {weights_dir}")
        return
    
    model_files = list(weights_path.glob("*.pth"))
    
    if not model_files:
        print("No trained models found.")
        print(f"\nTo train models, run:")
        print("  python train_behavior_models.py --data ../behavior-data/data_user500.csv")
        return
    
    # Group by model type
    models = {}
    for file in model_files:
        parts = file.stem.split('_')
        model_type = parts[0]
        checkpoint = '_'.join(parts[1:])
        
        if model_type not in models:
            models[model_type] = []
        
        models[model_type].append({
            'checkpoint': checkpoint,
            'path': file,
            'size_mb': file.stat().st_size / (1024 * 1024),
            'modified': datetime.fromtimestamp(file.stat().st_mtime)
        })
    
    # Display models
    for model_type, checkpoints in sorted(models.items()):
        print(f"📦 {model_type}")
        print(f"   Found {len(checkpoints)} checkpoint(s):")
        
        for ckpt in sorted(checkpoints, key=lambda x: x['modified'], reverse=True):
            print(f"   • {ckpt['checkpoint']:20s} "
                  f"({ckpt['size_mb']:.2f} MB) "
                  f"- {ckpt['modified'].strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    print(f"Total: {len(model_files)} model file(s)")
    print(f"Location: {weights_path.absolute()}")


def model_info(model_path: str):
    """Display detailed information about a model."""
    print("\n" + "="*80)
    print("  MODEL INFORMATION")
    print("="*80 + "\n")
    
    path = Path(model_path)
    
    if not path.exists():
        print(f"❌ Model not found: {model_path}")
        return
    
    # Load model state dict
    try:
        state_dict = torch.load(model_path, map_location='cpu')
        
        print(f"📄 File: {path.name}")
        print(f"📍 Path: {path.absolute()}")
        print(f"📦 Size: {path.stat().st_size / (1024 * 1024):.2f} MB")
        print(f"📅 Modified: {datetime.fromtimestamp(path.stat().st_mtime)}")
        
        print(f"\n🔧 Model Architecture:")
        print(f"   Total parameters: {len(state_dict)}")
        
        # Analyze layers
        layer_types = {}
        total_params = 0
        
        for key, tensor in state_dict.items():
            layer_type = key.split('.')[0]
            layer_types[layer_type] = layer_types.get(layer_type, 0) + 1
            total_params += tensor.numel()
        
        print(f"   Total trainable parameters: {total_params:,}")
        print(f"\n   Layer breakdown:")
        for layer, count in sorted(layer_types.items()):
            print(f"   • {layer:20s}: {count} parameter(s)")
        
        # Sample layer shapes
        print(f"\n   Sample layer shapes:")
        for i, (key, tensor) in enumerate(list(state_dict.items())[:5]):
            print(f"   • {key:40s}: {list(tensor.shape)}")
        
        if len(state_dict) > 5:
            print(f"   ... and {len(state_dict) - 5} more layers")
        
    except Exception as e:
        print(f"❌ Error loading model: {str(e)}")


def test_model(model_path: str, model_type: str):
    """Quick test of a model."""
    print("\n" + "="*80)
    print(f"  TESTING MODEL: {model_type.upper()}")
    print("="*80 + "\n")
    
    path = Path(model_path)
    
    if not path.exists():
        print(f"❌ Model not found: {model_path}")
        return
    
    try:
        # Create model
        model_classes = {
            'rnn': BehaviorRNN,
            'lstm': BehaviorLSTM,
            'bilstm': BehaviorBiLSTM
        }
        
        if model_type.lower() not in model_classes:
            print(f"❌ Unknown model type: {model_type}")
            return
        
        print("Loading model...")
        model = model_classes[model_type.lower()](
            vocab_size=1000,
            embedding_dim=64,
            hidden_dim=128,
            num_layers=2,
            dropout=0.3,
            num_classes=5
        )
        
        model.load_state_dict(torch.load(model_path, map_location='cpu'))
        model.eval()
        
        print("✓ Model loaded successfully")
        
        # Test forward pass
        print("\nTesting forward pass...")
        batch_size = 4
        seq_len = 10
        
        dummy_input = torch.randint(0, 100, (batch_size, seq_len))
        
        with torch.no_grad():
            output, hidden = model(dummy_input)
        
        print(f"✓ Forward pass successful")
        print(f"   Input shape:  {list(dummy_input.shape)}")
        print(f"   Output shape: {list(output.shape)}")
        
        # Test predictions
        print("\nSample predictions:")
        probs = torch.softmax(output, dim=1)
        
        actions = ['view', 'click', 'add_to_cart', 'purchase', 'search']
        
        for i in range(min(3, batch_size)):
            top_prob, top_idx = torch.max(probs[i], dim=0)
            print(f"   Sample {i+1}: {actions[top_idx]} (confidence: {top_prob:.2%})")
        
        print("\n✓ Model test completed successfully")
        
    except Exception as e:
        print(f"❌ Error testing model: {str(e)}")
        import traceback
        traceback.print_exc()


def clean_models(weights_dir: str, keep_best: bool = True, dry_run: bool = True):
    """Clean up old model checkpoints."""
    print("\n" + "="*80)
    print("  CLEAN MODELS")
    print("="*80 + "\n")
    
    weights_path = Path(weights_dir)
    
    if not weights_path.exists():
        print(f"❌ Weights directory not found: {weights_dir}")
        return
    
    model_files = list(weights_path.glob("*.pth"))
    
    if not model_files:
        print("No models to clean.")
        return
    
    # Identify files to keep/remove
    to_keep = []
    to_remove = []
    
    if keep_best:
        # Keep best_acc and best_loss checkpoints
        for file in model_files:
            if 'best_acc' in file.name or 'best_loss' in file.name or 'final' in file.name:
                to_keep.append(file)
            else:
                to_remove.append(file)
    else:
        to_remove = model_files
    
    print(f"Files to keep: {len(to_keep)}")
    for file in to_keep:
        print(f"  ✓ {file.name}")
    
    print(f"\nFiles to remove: {len(to_remove)}")
    total_size = 0
    for file in to_remove:
        size_mb = file.stat().st_size / (1024 * 1024)
        total_size += size_mb
        print(f"  ✗ {file.name} ({size_mb:.2f} MB)")
    
    print(f"\nTotal space to free: {total_size:.2f} MB")
    
    if dry_run:
        print("\n⚠️  DRY RUN - No files were deleted")
        print("   Run with --no-dry-run to actually delete files")
    else:
        confirm = input("\n⚠️  Are you sure you want to delete these files? (yes/no): ")
        if confirm.lower() == 'yes':
            for file in to_remove:
                file.unlink()
                print(f"  ✓ Deleted {file.name}")
            print(f"\n✓ Cleaned up {len(to_remove)} file(s), freed {total_size:.2f} MB")
        else:
            print("Cancelled.")


def compare_models(weights_dir: str):
    """Compare model sizes and architectures."""
    print("\n" + "="*80)
    print("  MODEL COMPARISON")
    print("="*80 + "\n")
    
    weights_path = Path(weights_dir)
    
    if not weights_path.exists():
        print(f"❌ Weights directory not found: {weights_dir}")
        return
    
    # Find best models
    model_types = ['RNN', 'LSTM', 'BiLSTM']
    models_info = []
    
    for model_type in model_types:
        model_file = weights_path / f"{model_type}_best_acc.pth"
        
        if model_file.exists():
            state_dict = torch.load(model_file, map_location='cpu')
            total_params = sum(t.numel() for t in state_dict.values())
            size_mb = model_file.stat().st_size / (1024 * 1024)
            
            models_info.append({
                'type': model_type,
                'params': total_params,
                'size_mb': size_mb,
                'file': model_file.name
            })
    
    if not models_info:
        print("No models found for comparison.")
        return
    
    # Display comparison
    print(f"{'Model':<10} {'Parameters':>15} {'Size (MB)':>12} {'File':<30}")
    print("-" * 80)
    
    for info in models_info:
        print(f"{info['type']:<10} {info['params']:>15,} {info['size_mb']:>12.2f} {info['file']:<30}")
    
    print("\n💡 Tips:")
    print("   • More parameters = More capacity but slower inference")
    print("   • BiLSTM typically has 2x parameters of LSTM due to bidirectional processing")
    print("   • Choose model based on accuracy/speed tradeoff for your use case")


def main():
    parser = argparse.ArgumentParser(description='Manage behavior prediction models')
    parser.add_argument('command', choices=['list', 'info', 'test', 'clean', 'compare'],
                        help='Command to execute')
    parser.add_argument('--weights-dir', type=str, default='weights/behavior_models',
                        help='Directory with model weights')
    parser.add_argument('--model-path', type=str, help='Path to specific model file')
    parser.add_argument('--model-type', type=str, choices=['rnn', 'lstm', 'bilstm'],
                        help='Type of model')
    parser.add_argument('--keep-best', action='store_true', default=True,
                        help='Keep best checkpoints when cleaning')
    parser.add_argument('--no-dry-run', action='store_true',
                        help='Actually delete files (for clean command)')
    
    args = parser.parse_args()
    
    if args.command == 'list':
        list_models(args.weights_dir)
    
    elif args.command == 'info':
        if not args.model_path:
            print("❌ --model-path required for info command")
            return
        model_info(args.model_path)
    
    elif args.command == 'test':
        if not args.model_path or not args.model_type:
            print("❌ --model-path and --model-type required for test command")
            return
        test_model(args.model_path, args.model_type)
    
    elif args.command == 'clean':
        clean_models(args.weights_dir, args.keep_best, not args.no_dry_run)
    
    elif args.command == 'compare':
        compare_models(args.weights_dir)


if __name__ == '__main__':
    main()
