"""
Evaluation script for trained behavior prediction models.
Compares RNN, LSTM, and BiLSTM performance on test data.
"""
import os
import sys
import argparse
import json
from pathlib import Path
from typing import Dict, List

import torch
import torch.nn.functional as F
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score
)
from tqdm import tqdm

sys.path.append(str(Path(__file__).parent))

from app.behavior_models import BehaviorRNN, BehaviorLSTM, BehaviorBiLSTM
from app.behavior_preprocessing import BehaviorDataProcessor


class ModelEvaluator:
    """Evaluator for behavior prediction models."""
    
    def __init__(self, model, model_name: str, device: torch.device):
        self.model = model.to(device)
        self.model_name = model_name
        self.device = device
        self.model.eval()
        
    def evaluate(self, test_loader) -> Dict:
        """
        Comprehensive evaluation of the model.
        
        Returns:
            Dictionary with evaluation metrics
        """
        all_predictions = []
        all_labels = []
        all_probabilities = []
        
        with torch.no_grad():
            for sequences, labels in tqdm(test_loader, desc=f"Evaluating {self.model_name}"):
                sequences = sequences.to(self.device)
                labels = labels.to(self.device)
                
                outputs, _ = self.model(sequences)
                probabilities = F.softmax(outputs, dim=1)
                _, predicted = torch.max(outputs, 1)
                
                all_predictions.extend(predicted.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())
                all_probabilities.extend(probabilities.cpu().numpy())
        
        # Convert to numpy arrays
        y_true = np.array(all_labels)
        y_pred = np.array(all_predictions)
        y_prob = np.array(all_probabilities)
        
        # Calculate metrics
        accuracy = (y_true == y_pred).mean()
        precision, recall, f1, support = precision_recall_fscore_support(
            y_true, y_pred, average='weighted', zero_division=0
        )
        
        # Per-class metrics
        class_report = classification_report(
            y_true, y_pred, output_dict=True, zero_division=0
        )
        
        # Confusion matrix
        conf_matrix = confusion_matrix(y_true, y_pred)
        
        # Try to calculate AUC (if applicable)
        try:
            auc_score = roc_auc_score(y_true, y_prob, multi_class='ovr', average='weighted')
        except:
            auc_score = None
        
        return {
            'accuracy': float(accuracy),
            'precision': float(precision),
            'recall': float(recall),
            'f1_score': float(f1),
            'auc_score': float(auc_score) if auc_score else None,
            'confusion_matrix': conf_matrix.tolist(),
            'classification_report': class_report,
            'num_samples': len(y_true)
        }
    
    def plot_confusion_matrix(self, conf_matrix: np.ndarray, save_path: str):
        """Plot and save confusion matrix."""
        plt.figure(figsize=(10, 8))
        
        action_labels = ['view', 'click', 'add_to_cart', 'purchase', 'search']
        
        sns.heatmap(
            conf_matrix,
            annot=True,
            fmt='d',
            cmap='Blues',
            xticklabels=action_labels[:conf_matrix.shape[0]],
            yticklabels=action_labels[:conf_matrix.shape[1]]
        )
        
        plt.title(f'Confusion Matrix - {self.model_name}')
        plt.ylabel('True Label')
        plt.xlabel('Predicted Label')
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"Confusion matrix saved to: {save_path}")


def compare_models(results: Dict[str, Dict], save_dir: str):
    """
    Compare multiple models and create visualization.
    
    Args:
        results: Dictionary mapping model names to their results
        save_dir: Directory to save comparison plots
    """
    os.makedirs(save_dir, exist_ok=True)
    
    # Extract metrics for comparison
    models = list(results.keys())
    metrics = ['accuracy', 'precision', 'recall', 'f1_score']
    
    # Create comparison bar plot
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    axes = axes.flatten()
    
    for idx, metric in enumerate(metrics):
        values = [results[model][metric] for model in models]
        
        axes[idx].bar(models, values, color=['#3498db', '#e74c3c', '#2ecc71'][:len(models)])
        axes[idx].set_title(f'{metric.replace("_", " ").title()} Comparison', fontsize=14, fontweight='bold')
        axes[idx].set_ylabel(metric.replace('_', ' ').title())
        axes[idx].set_ylim([0, 1])
        axes[idx].grid(axis='y', alpha=0.3)
        
        # Add value labels on bars
        for i, v in enumerate(values):
            axes[idx].text(i, v + 0.02, f'{v:.4f}', ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    comparison_path = os.path.join(save_dir, 'model_comparison.png')
    plt.savefig(comparison_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Model comparison saved to: {comparison_path}")
    
    # Create detailed comparison table
    print("\n" + "="*80)
    print("MODEL COMPARISON SUMMARY")
    print("="*80)
    print(f"{'Model':<15} {'Accuracy':<12} {'Precision':<12} {'Recall':<12} {'F1-Score':<12}")
    print("-"*80)
    
    for model in models:
        print(f"{model:<15} "
              f"{results[model]['accuracy']:<12.4f} "
              f"{results[model]['precision']:<12.4f} "
              f"{results[model]['recall']:<12.4f} "
              f"{results[model]['f1_score']:<12.4f}")
    
    print("="*80)
    
    # Find best model
    best_model = max(results.items(), key=lambda x: x[1]['f1_score'])
    print(f"\n🏆 Best Model: {best_model[0].upper()} (F1-Score: {best_model[1]['f1_score']:.4f})")


def main():
    parser = argparse.ArgumentParser(description='Evaluate behavior prediction models')
    parser.add_argument('--data', type=str, required=True, help='Path to behavior CSV file')
    parser.add_argument('--models', nargs='+', default=['rnn', 'lstm', 'bilstm'],
                        choices=['rnn', 'lstm', 'bilstm'], help='Models to evaluate')
    parser.add_argument('--weights-dir', type=str, default='weights/behavior_models',
                        help='Directory with trained model weights')
    parser.add_argument('--output-dir', type=str, default='evaluation_results',
                        help='Directory to save evaluation results')
    parser.add_argument('--batch-size', type=int, default=64, help='Batch size')
    parser.add_argument('--no-cuda', action='store_true', help='Disable CUDA')
    
    args = parser.parse_args()
    
    # Setup
    device = torch.device('cuda' if torch.cuda.is_available() and not args.no_cuda else 'cpu')
    print(f"Using device: {device}\n")
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Prepare data
    print("Preparing test data...")
    processor = BehaviorDataProcessor(seq_length=10, max_seq_len=50)
    _, _, test_loader = processor.prepare_dataloaders(
        csv_path=args.data,
        batch_size=args.batch_size,
        test_size=0.2,
        val_size=0.1
    )
    
    vocab_size = processor.encoder.vocab_size
    num_classes = processor.encoder.num_actions - 1
    
    # Model configurations
    model_configs = {
        'rnn': BehaviorRNN,
        'lstm': BehaviorLSTM,
        'bilstm': BehaviorBiLSTM
    }
    
    # Evaluate each model
    all_results = {}
    
    for model_type in args.models:
        print(f"\n{'='*80}")
        print(f"Evaluating {model_type.upper()}")
        print(f"{'='*80}")
        
        # Load model
        model_path = os.path.join(args.weights_dir, f"{model_type.upper()}_best_acc.pth")
        
        if not os.path.exists(model_path):
            print(f"⚠️  Model weights not found: {model_path}")
            print(f"Skipping {model_type.upper()}...")
            continue
        
        # Create model
        model = model_configs[model_type](
            vocab_size=vocab_size,
            embedding_dim=64,
            hidden_dim=128,
            num_layers=2,
            dropout=0.3,
            num_classes=num_classes
        )
        
        # Load weights
        model.load_state_dict(torch.load(model_path, map_location=device))
        
        # Create evaluator
        evaluator = ModelEvaluator(model, model_type.upper(), device)
        
        # Evaluate
        results = evaluator.evaluate(test_loader)
        all_results[model_type.upper()] = results
        
        # Print results
        print(f"\nResults for {model_type.upper()}:")
        print(f"  Accuracy:  {results['accuracy']:.4f}")
        print(f"  Precision: {results['precision']:.4f}")
        print(f"  Recall:    {results['recall']:.4f}")
        print(f"  F1-Score:  {results['f1_score']:.4f}")
        if results['auc_score']:
            print(f"  AUC Score: {results['auc_score']:.4f}")
        
        # Plot confusion matrix
        conf_matrix = np.array(results['confusion_matrix'])
        cm_path = os.path.join(args.output_dir, f'{model_type}_confusion_matrix.png')
        evaluator.plot_confusion_matrix(conf_matrix, cm_path)
    
    # Compare models
    if len(all_results) > 1:
        print(f"\n{'='*80}")
        compare_models(all_results, args.output_dir)
    
    # Save results to JSON
    results_path = os.path.join(args.output_dir, 'evaluation_results.json')
    with open(results_path, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n✓ Evaluation results saved to: {results_path}")
    print(f"✓ Visualizations saved to: {args.output_dir}")


if __name__ == '__main__':
    main()
