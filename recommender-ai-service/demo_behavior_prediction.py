"""
Demo script for behavior prediction models.
Quick test and visualization of model predictions.
"""
import sys
from pathlib import Path
import torch

sys.path.append(str(Path(__file__).parent))

from app.behavior_models import BehaviorPredictor
from app.behavior_preprocessing import BehaviorDataProcessor, analyze_behavior_data


def print_header(text: str):
    """Print formatted header."""
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80 + "\n")


def demo_data_analysis(csv_path: str):
    """Demo: Analyze behavior data."""
    print_header("1. DATA ANALYSIS")
    
    stats = analyze_behavior_data(csv_path)
    
    print(f"📊 Total Events: {stats['total_events']:,}")
    print(f"👥 Unique Users: {stats['unique_users']:,}")
    print(f"📦 Unique Products: {stats['unique_products']:,}")
    print(f"📈 Avg Events per User: {stats['avg_events_per_user']:.2f}")
    
    print(f"\n📅 Date Range:")
    print(f"   Start: {stats['date_range']['start']}")
    print(f"   End:   {stats['date_range']['end']}")
    
    print(f"\n🎯 Action Distribution:")
    for action, count in stats['action_distribution'].items():
        percentage = (count / stats['total_events']) * 100
        bar = "█" * int(percentage / 2)
        print(f"   {action:15s}: {count:5d} ({percentage:5.2f}%) {bar}")
    
    print(f"\n📏 Sequence Length Statistics:")
    print(f"   Min:    {stats['sequence_length']['min']}")
    print(f"   Max:    {stats['sequence_length']['max']}")
    print(f"   Mean:   {stats['sequence_length']['mean']:.2f}")
    print(f"   Median: {stats['sequence_length']['median']:.2f}")


def demo_preprocessing(csv_path: str):
    """Demo: Data preprocessing and sequence creation."""
    print_header("2. DATA PREPROCESSING")
    
    processor = BehaviorDataProcessor(seq_length=10, max_seq_len=50)
    
    print("Loading and processing data...")
    df = processor.load_data(csv_path)
    sequences, labels = processor.create_sequences(df)
    
    print(f"✓ Created {len(sequences):,} training sequences")
    print(f"✓ Vocabulary size: {processor.encoder.vocab_size}")
    print(f"✓ Number of action classes: {processor.encoder.num_actions - 1}")
    
    # Show sample sequences
    print("\n📝 Sample Sequences:")
    for i in range(min(3, len(sequences))):
        seq = sequences[i]
        label = labels[i]
        
        # Decode sequence
        decoded_actions = [processor.encoder.decode_action(idx) for idx in seq[-5:]]
        decoded_label = processor.encoder.decode_action(label + 1)
        
        print(f"\n   Sequence {i+1}:")
        print(f"   Last 5 actions: {' → '.join(decoded_actions)}")
        print(f"   Next action (label): {decoded_label}")


def demo_model_prediction(model_type: str = 'bilstm'):
    """Demo: Model prediction on sample sequences."""
    print_header(f"3. MODEL PREDICTION ({model_type.upper()})")
    
    # Check if model exists
    weights_dir = Path(__file__).parent / "weights" / "behavior_models"
    model_path = weights_dir / f"{model_type.upper()}_best_acc.pth"
    
    if not model_path.exists():
        print(f"❌ Model not found: {model_path}")
        print(f"   Please train the model first using:")
        print(f"   python train_behavior_models.py --data ../behavior-data/data_user500.csv")
        return
    
    # Initialize predictor and processor
    print(f"Loading {model_type.upper()} model...")
    predictor = BehaviorPredictor(model_type=model_type, model_path=str(model_path))
    processor = BehaviorDataProcessor(seq_length=10, max_seq_len=50)
    
    # Test cases
    test_cases = [
        {
            'user_id': 311,
            'actions': ['view', 'view', 'click'],
            'description': 'User browsing products'
        },
        {
            'user_id': 318,
            'actions': ['view', 'click', 'view', 'add_to_cart'],
            'description': 'User showing purchase intent'
        },
        {
            'user_id': 129,
            'actions': ['search', 'view', 'click', 'add_to_cart', 'view'],
            'description': 'User in decision phase'
        },
        {
            'user_id': 266,
            'actions': ['view', 'view', 'view', 'view'],
            'description': 'User just browsing'
        }
    ]
    
    print(f"✓ Model loaded successfully\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"{'─'*80}")
        print(f"Test Case {i}: {test_case['description']}")
        print(f"User ID: {test_case['user_id']}")
        print(f"Action Sequence: {' → '.join(test_case['actions'])}")
        
        # Encode sequence
        sequence = processor.encode_user_sequence(test_case['actions'])
        
        # Single prediction
        predicted_action, confidence = predictor.predict(sequence)
        print(f"\n🎯 Predicted Next Action: {predicted_action.upper()}")
        print(f"   Confidence: {confidence:.2%}")
        
        # Top-3 predictions
        top_predictions = predictor.predict_top_k(sequence, k=3)
        print(f"\n📊 Top 3 Predictions:")
        for rank, (action, prob) in enumerate(top_predictions, 1):
            bar = "█" * int(prob * 50)
            print(f"   {rank}. {action:15s} {prob:.2%} {bar}")
        
        print()


def demo_compare_models():
    """Demo: Compare predictions from different models."""
    print_header("4. MODEL COMPARISON")
    
    weights_dir = Path(__file__).parent / "weights" / "behavior_models"
    processor = BehaviorDataProcessor(seq_length=10, max_seq_len=50)
    
    # Test sequence
    test_actions = ['view', 'click', 'view', 'add_to_cart', 'view']
    sequence = processor.encode_user_sequence(test_actions)
    
    print(f"Test Sequence: {' → '.join(test_actions)}")
    print(f"\nComparing predictions from different models:\n")
    
    models = ['rnn', 'lstm', 'bilstm']
    results = []
    
    for model_type in models:
        model_path = weights_dir / f"{model_type.upper()}_best_acc.pth"
        
        if not model_path.exists():
            print(f"⚠️  {model_type.upper():8s}: Model not found")
            continue
        
        try:
            predictor = BehaviorPredictor(model_type=model_type, model_path=str(model_path))
            predicted_action, confidence = predictor.predict(sequence)
            
            results.append({
                'model': model_type.upper(),
                'prediction': predicted_action,
                'confidence': confidence
            })
            
            bar = "█" * int(confidence * 50)
            print(f"   {model_type.upper():8s}: {predicted_action:15s} ({confidence:.2%}) {bar}")
            
        except Exception as e:
            print(f"❌ {model_type.upper():8s}: Error - {str(e)}")
    
    if results:
        # Find best prediction
        best = max(results, key=lambda x: x['confidence'])
        print(f"\n🏆 Highest Confidence: {best['model']} → {best['prediction']} ({best['confidence']:.2%})")


def demo_sequence_analysis():
    """Demo: Analyze behavior sequences."""
    print_header("5. SEQUENCE ANALYSIS")
    
    test_sequences = [
        {
            'user_id': 311,
            'actions': ['view', 'view', 'click', 'purchase'],
            'label': 'Quick buyer'
        },
        {
            'user_id': 318,
            'actions': ['view', 'view', 'view', 'view', 'view', 'click', 'view'],
            'label': 'Window shopper'
        },
        {
            'user_id': 129,
            'actions': ['search', 'view', 'click', 'add_to_cart', 'view', 'add_to_cart', 'purchase'],
            'label': 'Deliberate buyer'
        }
    ]
    
    for seq in test_sequences:
        print(f"\n{'─'*80}")
        print(f"User {seq['user_id']} - {seq['label']}")
        print(f"Sequence: {' → '.join(seq['actions'])}")
        
        # Calculate metrics
        action_counts = {}
        for action in seq['actions']:
            action_counts[action] = action_counts.get(action, 0) + 1
        
        # Engagement score
        weights = {'view': 1, 'click': 2, 'search': 2, 'add_to_cart': 3, 'purchase': 5}
        engagement = sum(weights.get(a, 1) for a in seq['actions'])
        
        print(f"\n📊 Analysis:")
        print(f"   Sequence Length: {len(seq['actions'])}")
        print(f"   Unique Actions: {len(set(seq['actions']))}")
        print(f"   Engagement Score: {engagement}")
        print(f"   Action Distribution: {action_counts}")
        
        # Determine intent
        if 'purchase' in seq['actions']:
            intent = "🎯 High Intent (Converted)"
        elif 'add_to_cart' in seq['actions']:
            intent = "🛒 Medium Intent (Considering)"
        elif action_counts.get('view', 0) > len(seq['actions']) * 0.7:
            intent = "👀 Low Intent (Browsing)"
        else:
            intent = "🔍 Exploring"
        
        print(f"   User Intent: {intent}")


def main():
    """Run all demos."""
    print("\n" + "="*80)
    print("  🤖 BEHAVIOR PREDICTION MODELS - DEMO")
    print("  RNN | LSTM | BiLSTM")
    print("="*80)
    
    # Path to data
    csv_path = Path(__file__).parent.parent / "behavior-data" / "data_user500.csv"
    
    if not csv_path.exists():
        print(f"\n❌ Data file not found: {csv_path}")
        print("Please ensure the behavior data CSV exists.")
        return
    
    try:
        # Run demos
        demo_data_analysis(str(csv_path))
        demo_preprocessing(str(csv_path))
        demo_sequence_analysis()
        
        # Check if models are trained
        weights_dir = Path(__file__).parent / "weights" / "behavior_models"
        if weights_dir.exists() and any(weights_dir.glob("*.pth")):
            demo_model_prediction('bilstm')
            demo_compare_models()
        else:
            print_header("MODEL PREDICTION")
            print("⚠️  No trained models found.")
            print("\nTo train models, run:")
            print("   python train_behavior_models.py --data ../behavior-data/data_user500.csv")
        
        print("\n" + "="*80)
        print("  ✓ Demo completed successfully!")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
