"""
Data preprocessing utilities for behavior sequence modeling.
Handles data loading, encoding, sequence generation, and train/test splitting.
"""
import pandas as pd
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from typing import Tuple, List, Dict, Optional
from datetime import datetime
from sklearn.model_selection import train_test_split
from collections import Counter


class BehaviorEncoder:
    """
    Encodes user behaviors (actions and products) into numerical representations.
    """
    
    def __init__(self):
        self.action_to_idx = {
            '<PAD>': 0,
            'view': 1,
            'click': 2,
            'add_to_cart': 3,
            'purchase': 4,
            'search': 5
        }
        self.idx_to_action = {v: k for k, v in self.action_to_idx.items()}
        
        self.product_to_idx = {'<PAD>': 0, '<UNK>': 1}
        self.idx_to_product = {0: '<PAD>', 1: '<UNK>'}
        self.next_product_idx = 2
        
    def fit_products(self, product_ids: List[int]):
        """Build product vocabulary from data."""
        unique_products = sorted(set(product_ids))
        for pid in unique_products:
            if pid not in self.product_to_idx:
                self.product_to_idx[pid] = self.next_product_idx
                self.idx_to_product[self.next_product_idx] = pid
                self.next_product_idx += 1
    
    def encode_action(self, action: str) -> int:
        """Encode action string to index."""
        # Normalize action string
        action = action.lower().replace(' ', '_')
        return self.action_to_idx.get(action, self.action_to_idx['view'])
    
    def encode_product(self, product_id: int) -> int:
        """Encode product ID to index."""
        return self.product_to_idx.get(product_id, self.product_to_idx['<UNK>'])
    
    def decode_action(self, idx: int) -> str:
        """Decode action index to string."""
        return self.idx_to_action.get(idx, 'unknown')
    
    def decode_product(self, idx: int) -> int:
        """Decode product index to ID."""
        return self.idx_to_product.get(idx, -1)
    
    @property
    def vocab_size(self) -> int:
        """Total vocabulary size (actions + products)."""
        return len(self.action_to_idx) + len(self.product_to_idx)
    
    @property
    def num_actions(self) -> int:
        """Number of action types."""
        return len(self.action_to_idx)


class BehaviorSequenceDataset(Dataset):
    """
    PyTorch Dataset for behavior sequences.
    Creates sequences of user actions for training RNN/LSTM models.
    """
    
    def __init__(
        self,
        sequences: List[List[int]],
        labels: List[int],
        max_seq_len: int = 50
    ):
        """
        Initialize dataset.
        
        Args:
            sequences: List of behavior sequences (encoded)
            labels: List of target actions (next action to predict)
            max_seq_len: Maximum sequence length (for padding/truncation)
        """
        self.sequences = sequences
        self.labels = labels
        self.max_seq_len = max_seq_len
        
    def __len__(self) -> int:
        return len(self.sequences)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        sequence = self.sequences[idx]
        label = self.labels[idx]
        
        # Pad or truncate sequence
        if len(sequence) < self.max_seq_len:
            # Pad with zeros
            padded = [0] * (self.max_seq_len - len(sequence)) + sequence
        else:
            # Take last max_seq_len items
            padded = sequence[-self.max_seq_len:]
        
        return torch.tensor(padded, dtype=torch.long), torch.tensor(label, dtype=torch.long)


class BehaviorDataProcessor:
    """
    Main data processor for behavior prediction.
    Handles loading, preprocessing, and sequence generation.
    """
    
    def __init__(
        self,
        seq_length: int = 10,
        min_seq_length: int = 3,
        max_seq_len: int = 50
    ):
        """
        Initialize processor.
        
        Args:
            seq_length: Number of past actions to use for prediction
            min_seq_length: Minimum sequence length to include
            max_seq_len: Maximum sequence length for padding
        """
        self.seq_length = seq_length
        self.min_seq_length = min_seq_length
        self.max_seq_len = max_seq_len
        self.encoder = BehaviorEncoder()
        
    def load_data(self, csv_path: str) -> pd.DataFrame:
        """
        Load behavior data from CSV.
        
        Args:
            csv_path: Path to CSV file
            
        Returns:
            DataFrame with behavior data
        """
        df = pd.read_csv(csv_path)
        
        # Ensure required columns exist
        required_cols = ['user_id', 'product_id', 'action', 'timestamp']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"CSV must contain columns: {required_cols}")
        
        # Sort by user and timestamp
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values(['user_id', 'timestamp']).reset_index(drop=True)
        
        return df
    
    def create_sequences(
        self,
        df: pd.DataFrame,
        combine_action_product: bool = True
    ) -> Tuple[List[List[int]], List[int]]:
        """
        Create sequences from behavior data.
        
        Args:
            df: DataFrame with behavior data
            combine_action_product: If True, combine action and product into single token
            
        Returns:
            sequences: List of input sequences
            labels: List of target labels (next action)
        """
        # Fit encoder on all products
        self.encoder.fit_products(df['product_id'].unique().tolist())
        
        sequences = []
        labels = []
        
        # Group by user
        for user_id, user_df in df.groupby('user_id'):
            user_actions = user_df['action'].tolist()
            user_products = user_df['product_id'].tolist()
            
            # Skip if too few actions
            if len(user_actions) < self.min_seq_length:
                continue
            
            # Encode actions
            encoded_actions = [self.encoder.encode_action(a) for a in user_actions]
            
            if combine_action_product:
                # Combine action and product into single representation
                # Use action as primary feature, product as context
                encoded_sequence = encoded_actions
            else:
                # Separate encoding (can be extended for multi-input models)
                encoded_sequence = encoded_actions
            
            # Create sliding window sequences
            for i in range(len(encoded_sequence) - 1):
                # Get sequence of past actions
                start_idx = max(0, i - self.seq_length + 1)
                seq = encoded_sequence[start_idx:i + 1]
                
                # Next action is the label
                next_action = encoded_actions[i + 1]
                
                if len(seq) >= self.min_seq_length:
                    sequences.append(seq)
                    labels.append(next_action - 1)  # Subtract 1 to make 0-indexed for classification
        
        return sequences, labels
    
    def prepare_dataloaders(
        self,
        csv_path: str,
        batch_size: int = 32,
        test_size: float = 0.2,
        val_size: float = 0.1,
        random_state: int = 42
    ) -> Tuple[DataLoader, DataLoader, DataLoader]:
        """
        Prepare train, validation, and test dataloaders.
        
        Args:
            csv_path: Path to behavior CSV file
            batch_size: Batch size for dataloaders
            test_size: Proportion of data for testing
            val_size: Proportion of training data for validation
            random_state: Random seed
            
        Returns:
            train_loader, val_loader, test_loader
        """
        # Load and process data
        df = self.load_data(csv_path)
        sequences, labels = self.create_sequences(df)
        
        print(f"Total sequences created: {len(sequences)}")
        print(f"Vocabulary size: {self.encoder.vocab_size}")
        print(f"Number of action classes: {self.encoder.num_actions - 1}")  # Exclude PAD
        
        # Split data
        X_temp, X_test, y_temp, y_test = train_test_split(
            sequences, labels, test_size=test_size, random_state=random_state
        )
        
        X_train, X_val, y_train, y_val = train_test_split(
            X_temp, y_temp, test_size=val_size, random_state=random_state
        )
        
        print(f"Train size: {len(X_train)}, Val size: {len(X_val)}, Test size: {len(X_test)}")
        
        # Create datasets
        train_dataset = BehaviorSequenceDataset(X_train, y_train, self.max_seq_len)
        val_dataset = BehaviorSequenceDataset(X_val, y_val, self.max_seq_len)
        test_dataset = BehaviorSequenceDataset(X_test, y_test, self.max_seq_len)
        
        # Create dataloaders
        train_loader = DataLoader(
            train_dataset,
            batch_size=batch_size,
            shuffle=True,
            num_workers=0  # Set to 0 for Windows compatibility
        )
        
        val_loader = DataLoader(
            val_dataset,
            batch_size=batch_size,
            shuffle=False,
            num_workers=0
        )
        
        test_loader = DataLoader(
            test_dataset,
            batch_size=batch_size,
            shuffle=False,
            num_workers=0
        )
        
        return train_loader, val_loader, test_loader
    
    def get_class_weights(self, labels: List[int]) -> torch.Tensor:
        """
        Calculate class weights for imbalanced data.
        
        Args:
            labels: List of class labels
            
        Returns:
            Tensor of class weights
        """
        counter = Counter(labels)
        total = len(labels)
        num_classes = max(counter.keys()) + 1
        
        weights = torch.ones(num_classes)
        for cls, count in counter.items():
            weights[cls] = total / (num_classes * count)
        
        return weights
    
    def encode_user_sequence(
        self,
        actions: List[str],
        product_ids: Optional[List[int]] = None
    ) -> torch.Tensor:
        """
        Encode a user's behavior sequence for inference.
        
        Args:
            actions: List of action strings
            product_ids: List of product IDs (optional)
            
        Returns:
            Encoded sequence tensor
        """
        encoded = [self.encoder.encode_action(a) for a in actions]
        
        # Pad or truncate
        if len(encoded) < self.max_seq_len:
            padded = [0] * (self.max_seq_len - len(encoded)) + encoded
        else:
            padded = encoded[-self.max_seq_len:]
        
        return torch.tensor(padded, dtype=torch.long).unsqueeze(0)


def analyze_behavior_data(csv_path: str) -> Dict:
    """
    Analyze behavior data and return statistics.
    
    Args:
        csv_path: Path to behavior CSV file
        
    Returns:
        Dictionary with data statistics
    """
    df = pd.read_csv(csv_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    stats = {
        'total_events': len(df),
        'unique_users': df['user_id'].nunique(),
        'unique_products': df['product_id'].nunique(),
        'action_distribution': df['action'].value_counts().to_dict(),
        'avg_events_per_user': len(df) / df['user_id'].nunique(),
        'date_range': {
            'start': df['timestamp'].min().isoformat(),
            'end': df['timestamp'].max().isoformat()
        }
    }
    
    # Sequence length distribution
    seq_lengths = df.groupby('user_id').size()
    stats['sequence_length'] = {
        'min': int(seq_lengths.min()),
        'max': int(seq_lengths.max()),
        'mean': float(seq_lengths.mean()),
        'median': float(seq_lengths.median())
    }
    
    return stats
