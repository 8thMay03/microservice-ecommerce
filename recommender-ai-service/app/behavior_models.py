"""
Deep Learning models for customer behavior prediction.
Includes RNN, LSTM, and BiLSTM architectures.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple, Optional


class BehaviorRNN(nn.Module):
    """
    Simple RNN model for behavior sequence prediction.
    Predicts next action based on sequence of past behaviors.
    """
    
    def __init__(
        self,
        vocab_size: int,
        embedding_dim: int = 64,
        hidden_dim: int = 128,
        num_layers: int = 2,
        dropout: float = 0.3,
        num_classes: int = 5  # view, click, add_to_cart, purchase, search
    ):
        super(BehaviorRNN, self).__init__()
        
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        
        # Embedding layer for action and product IDs
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=0)
        
        # RNN layers
        self.rnn = nn.RNN(
            embedding_dim,
            hidden_dim,
            num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        
        # Dropout for regularization
        self.dropout = nn.Dropout(dropout)
        
        # Output layers
        self.fc1 = nn.Linear(hidden_dim, hidden_dim // 2)
        self.fc2 = nn.Linear(hidden_dim // 2, num_classes)
        
    def forward(
        self,
        x: torch.Tensor,
        hidden: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass.
        
        Args:
            x: Input tensor of shape (batch_size, seq_len)
            hidden: Hidden state (optional)
            
        Returns:
            output: Predictions of shape (batch_size, num_classes)
            hidden: Final hidden state
        """
        # Embedding
        embedded = self.embedding(x)  # (batch, seq_len, embedding_dim)
        
        # RNN
        rnn_out, hidden = self.rnn(embedded, hidden)  # (batch, seq_len, hidden_dim)
        
        # Take the last output
        last_output = rnn_out[:, -1, :]  # (batch, hidden_dim)
        
        # Fully connected layers
        out = self.dropout(last_output)
        out = F.relu(self.fc1(out))
        out = self.dropout(out)
        out = self.fc2(out)
        
        return out, hidden
    
    def init_hidden(self, batch_size: int, device: torch.device) -> torch.Tensor:
        """Initialize hidden state."""
        return torch.zeros(self.num_layers, batch_size, self.hidden_dim).to(device)


class BehaviorLSTM(nn.Module):
    """
    LSTM model for behavior sequence prediction.
    Better at capturing long-term dependencies than RNN.
    """
    
    def __init__(
        self,
        vocab_size: int,
        embedding_dim: int = 64,
        hidden_dim: int = 128,
        num_layers: int = 2,
        dropout: float = 0.3,
        num_classes: int = 5
    ):
        super(BehaviorLSTM, self).__init__()
        
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        
        # Embedding layer
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=0)
        
        # LSTM layers
        self.lstm = nn.LSTM(
            embedding_dim,
            hidden_dim,
            num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        
        # Dropout
        self.dropout = nn.Dropout(dropout)
        
        # Attention mechanism (optional enhancement)
        self.attention = nn.Linear(hidden_dim, 1)
        
        # Output layers
        self.fc1 = nn.Linear(hidden_dim, hidden_dim // 2)
        self.fc2 = nn.Linear(hidden_dim // 2, num_classes)
        
    def forward(
        self,
        x: torch.Tensor,
        hidden: Optional[Tuple[torch.Tensor, torch.Tensor]] = None
    ) -> Tuple[torch.Tensor, Tuple[torch.Tensor, torch.Tensor]]:
        """
        Forward pass with attention mechanism.
        
        Args:
            x: Input tensor of shape (batch_size, seq_len)
            hidden: Tuple of (h_0, c_0) hidden states (optional)
            
        Returns:
            output: Predictions of shape (batch_size, num_classes)
            hidden: Final hidden state tuple (h_n, c_n)
        """
        # Embedding
        embedded = self.embedding(x)  # (batch, seq_len, embedding_dim)
        
        # LSTM
        lstm_out, hidden = self.lstm(embedded, hidden)  # (batch, seq_len, hidden_dim)
        
        # Apply attention
        attention_weights = F.softmax(self.attention(lstm_out), dim=1)  # (batch, seq_len, 1)
        context = torch.sum(attention_weights * lstm_out, dim=1)  # (batch, hidden_dim)
        
        # Fully connected layers
        out = self.dropout(context)
        out = F.relu(self.fc1(out))
        out = self.dropout(out)
        out = self.fc2(out)
        
        return out, hidden
    
    def init_hidden(self, batch_size: int, device: torch.device) -> Tuple[torch.Tensor, torch.Tensor]:
        """Initialize hidden state and cell state."""
        h_0 = torch.zeros(self.num_layers, batch_size, self.hidden_dim).to(device)
        c_0 = torch.zeros(self.num_layers, batch_size, self.hidden_dim).to(device)
        return (h_0, c_0)


class BehaviorBiLSTM(nn.Module):
    """
    Bidirectional LSTM model for behavior sequence prediction.
    Processes sequences in both forward and backward directions.
    """
    
    def __init__(
        self,
        vocab_size: int,
        embedding_dim: int = 64,
        hidden_dim: int = 128,
        num_layers: int = 2,
        dropout: float = 0.3,
        num_classes: int = 5
    ):
        super(BehaviorBiLSTM, self).__init__()
        
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        
        # Embedding layer
        self.embedding = nn.Embedding(vocab_size, embedding_dim, padding_idx=0)
        
        # Bidirectional LSTM layers
        self.bilstm = nn.LSTM(
            embedding_dim,
            hidden_dim,
            num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=True
        )
        
        # Dropout
        self.dropout = nn.Dropout(dropout)
        
        # Attention for bidirectional output
        self.attention = nn.Linear(hidden_dim * 2, 1)
        
        # Output layers (note: hidden_dim * 2 because of bidirectional)
        self.fc1 = nn.Linear(hidden_dim * 2, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim // 2)
        self.fc3 = nn.Linear(hidden_dim // 2, num_classes)
        
        # Batch normalization
        self.bn1 = nn.BatchNorm1d(hidden_dim)
        self.bn2 = nn.BatchNorm1d(hidden_dim // 2)
        
    def forward(
        self,
        x: torch.Tensor,
        hidden: Optional[Tuple[torch.Tensor, torch.Tensor]] = None
    ) -> Tuple[torch.Tensor, Tuple[torch.Tensor, torch.Tensor]]:
        """
        Forward pass with bidirectional processing and attention.
        
        Args:
            x: Input tensor of shape (batch_size, seq_len)
            hidden: Tuple of (h_0, c_0) hidden states (optional)
            
        Returns:
            output: Predictions of shape (batch_size, num_classes)
            hidden: Final hidden state tuple (h_n, c_n)
        """
        # Embedding
        embedded = self.embedding(x)  # (batch, seq_len, embedding_dim)
        
        # Bidirectional LSTM
        bilstm_out, hidden = self.bilstm(embedded, hidden)  # (batch, seq_len, hidden_dim*2)
        
        # Apply attention mechanism
        attention_weights = F.softmax(self.attention(bilstm_out), dim=1)  # (batch, seq_len, 1)
        context = torch.sum(attention_weights * bilstm_out, dim=1)  # (batch, hidden_dim*2)
        
        # Fully connected layers with batch normalization
        out = self.dropout(context)
        out = F.relu(self.bn1(self.fc1(out)))
        out = self.dropout(out)
        out = F.relu(self.bn2(self.fc2(out)))
        out = self.dropout(out)
        out = self.fc3(out)
        
        return out, hidden
    
    def init_hidden(self, batch_size: int, device: torch.device) -> Tuple[torch.Tensor, torch.Tensor]:
        """Initialize hidden state and cell state for bidirectional LSTM."""
        # Note: num_directions = 2 for bidirectional
        h_0 = torch.zeros(self.num_layers * 2, batch_size, self.hidden_dim).to(device)
        c_0 = torch.zeros(self.num_layers * 2, batch_size, self.hidden_dim).to(device)
        return (h_0, c_0)


class BehaviorPredictor:
    """
    Wrapper class for behavior prediction models.
    Handles model loading, inference, and prediction interpretation.
    """
    
    def __init__(
        self,
        model_type: str = "bilstm",
        model_path: Optional[str] = None,
        device: Optional[torch.device] = None
    ):
        """
        Initialize predictor.
        
        Args:
            model_type: Type of model ('rnn', 'lstm', 'bilstm')
            model_path: Path to saved model weights
            device: Torch device (cuda/cpu)
        """
        self.model_type = model_type.lower()
        self.device = device or torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.action_to_idx = {
            'view': 1,
            'click': 2,
            'add_to_cart': 3,
            'purchase': 4,
            'search': 5
        }
        self.idx_to_action = {v: k for k, v in self.action_to_idx.items()}
        
        if model_path:
            self.load_model(model_path)
    
    def load_model(self, model_path: str, vocab_size: int = 1000):
        """Load trained model from file."""
        if self.model_type == 'rnn':
            self.model = BehaviorRNN(vocab_size=vocab_size)
        elif self.model_type == 'lstm':
            self.model = BehaviorLSTM(vocab_size=vocab_size)
        elif self.model_type == 'bilstm':
            self.model = BehaviorBiLSTM(vocab_size=vocab_size)
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")
        
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.to(self.device)
        self.model.eval()
    
    def predict(self, sequence: torch.Tensor) -> Tuple[str, float]:
        """
        Predict next action from behavior sequence.
        
        Args:
            sequence: Tensor of shape (1, seq_len) or (seq_len,)
            
        Returns:
            predicted_action: String action name
            confidence: Prediction confidence score
        """
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        with torch.no_grad():
            if sequence.dim() == 1:
                sequence = sequence.unsqueeze(0)
            
            sequence = sequence.to(self.device)
            output, _ = self.model(sequence)
            probabilities = F.softmax(output, dim=1)
            confidence, predicted_idx = torch.max(probabilities, dim=1)
            
            predicted_action = self.idx_to_action.get(predicted_idx.item() + 1, 'unknown')
            
            return predicted_action, confidence.item()
    
    def predict_top_k(self, sequence: torch.Tensor, k: int = 3) -> list:
        """
        Predict top-k most likely next actions.
        
        Args:
            sequence: Tensor of shape (1, seq_len) or (seq_len,)
            k: Number of top predictions to return
            
        Returns:
            List of tuples (action, probability)
        """
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        with torch.no_grad():
            if sequence.dim() == 1:
                sequence = sequence.unsqueeze(0)
            
            sequence = sequence.to(self.device)
            output, _ = self.model(sequence)
            probabilities = F.softmax(output, dim=1)
            
            top_probs, top_indices = torch.topk(probabilities, k, dim=1)
            
            results = []
            for prob, idx in zip(top_probs[0], top_indices[0]):
                action = self.idx_to_action.get(idx.item() + 1, 'unknown')
                results.append((action, prob.item()))
            
            return results
